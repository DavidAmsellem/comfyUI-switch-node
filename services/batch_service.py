import threading
import time
import uuid
import io
import os
import concurrent.futures
from PIL import Image
from datetime import datetime
from werkzeug.utils import secure_filename

from config import COMFYUI_INPUT_DIR, OUR_OUTPUT_DIR  # Importamos OUR_OUTPUT_DIR para debug
from utils.logger import log_info, log_error, log_warning
from services.comfy_service import submit_workflow_to_comfyui, wait_for_completion
from services.workflow_service import load_workflow, update_workflow
from services.file_service import create_output_directory, extract_generated_images, find_image_file
from job_persistence import session_manager

ACTIVE_BATCHES = {}
BATCH_LOCK = threading.Lock()
BATCH_THROTTLE_LOCK = threading.Lock()
LAST_BATCH_SUBMIT_TIME = 0
CURRENT_BATCH_PROMPTS = 0

def enforce_batch_throttle(num_prompts):
    global LAST_BATCH_SUBMIT_TIME, CURRENT_BATCH_PROMPTS
    with BATCH_THROTTLE_LOCK:
        now = time.time()
        wait = max(0, (LAST_BATCH_SUBMIT_TIME + CURRENT_BATCH_PROMPTS) - now)
        if wait > 0: time.sleep(wait)
        LAST_BATCH_SUBMIT_TIME = time.time()
        CURRENT_BATCH_PROMPTS = num_prompts
        return wait

def process_all_workflows_simultaneously_with_tracking(image_data, workflows, common_params, batch_id, session_job_id=None):
    results = []
    submitted = {}
    
    # Debug inicial
    print(f"🔍 [BATCH START] ID: {batch_id}")
    print(f"📂 [CONFIG] Intentando guardar en raíz: {OUR_OUTPUT_DIR}")

    with BATCH_LOCK:
        if batch_id in ACTIVE_BATCHES:
            ACTIVE_BATCHES[batch_id]["status"] = "submitting"

    # Cargar imagen maestra
    image_data.seek(0)
    master = Image.open(image_data).convert('RGB')
    if master.width > 2048: master.thumbnail((2048, 2048))
    
    # 1. Enviar prompts
    for i, wf in enumerate(workflows):
        try:
            uniq_name = f"batch_{batch_id}_{i:03d}.png"
            path = os.path.join(COMFYUI_INPUT_DIR, uniq_name)
            master.save(path)
            
            w_data = load_workflow(wf["id"])
            base_name = secure_filename(common_params.get('original_filename', 'img').rsplit('.',1)[0])
            
            w_upd = update_workflow(w_data, uniq_name, common_params['frame_color'], common_params['style'], None, base_name)
            pid = submit_workflow_to_comfyui(w_upd)
            submitted[pid] = {'wf': wf, 'idx': i, 'base_name': base_name} # Guardamos base_name
            
        except Exception as e:
            log_error(f"Error enviando {wf['id']}: {e}")
            with BATCH_LOCK: ACTIVE_BATCHES[batch_id]['failed'] += 1

    # 2. Recoger resultados
    with BATCH_LOCK: ACTIVE_BATCHES[batch_id]["status"] = "processing"
    
    def _wait(pid, data):
        try:
            # Timeout largo para dar tiempo a la GPU
            outs = wait_for_completion(pid, timeout=60000)
            
            # Verificar si ComfyUI devolvió algo
            if not outs:
                print(f"⚠️ [BATCH] PID {pid} finalizó pero sin outputs (outs vacío).")
                raise Exception("ComfyUI no devolvió datos de salida")

            orig_name = common_params.get('original_filename', 'img')
            # Extraer imágenes
            imgs = extract_generated_images(outs, orig_name)
            print(f"🔎 [BATCH] PID {pid} encontró {len(imgs)} imágenes generadas.")

            # Crear directorio destino
            # Usamos el base_name limpio que guardamos al enviar
            safe_folder_name = secure_filename(data['base_name'])
            if not safe_folder_name: safe_folder_name = "batch_output"
            
            out_dir = create_output_directory(safe_folder_name)
            print(f"📂 [BATCH] Carpeta de destino: {out_dir}")
            
            saved = []
            
            for im in imgs:
                src = find_image_file(im['filename'], im['subfolder'])
                if src:
                    print(f"   🔄 Procesando: {src}")
                    new_name = f"{data['wf']['id'].replace('/','_')}_{uuid.uuid4().hex[:6]}.jpg"
                    dest = os.path.join(out_dir, new_name)
                    
                    try:
                        # Escritura FÍSICA
                        Image.open(src).convert('RGB').save(dest, 'JPEG')
                        print(f"   ✅ Guardado OK: {dest}")
                        
                        # Registro en PERSISTENCIA (Solo URL)
                        # Leemos lo que acabamos de guardar para simular el objeto archivo si save_job_image lo requiere,
                        # o simplemente pasamos la ruta relativa si tu job_persistence está actualizado.
                        with open(dest, 'rb') as f:
                            # session_job_id puede ser None si no se pasó bien, aseguramos
                            jid_safe = session_job_id if session_job_id else batch_id
                            url = session_manager.save_job_image(jid_safe, f.read(), new_name)
                        
                        saved.append({'filename': new_name, 'session_url': url, 'url': url}) # Añadimos 'url' por compatibilidad
                    except Exception as e_save:
                        print(f"   ❌ ERROR ESCRITURA DISCO: {e_save}")
                else:
                    print(f"   ⚠️ No se encontró el archivo origen: {im['filename']}")

            with BATCH_LOCK:
                if len(saved) > 0:
                    ACTIVE_BATCHES[batch_id]['successful'] += 1
                    # Añadir resultados a la memoria activa para el polling
                    ACTIVE_BATCHES[batch_id]['results'].extend([
                        {'workflow': data['wf']['id'], 'generated_images': saved}
                    ])
                else:
                    ACTIVE_BATCHES[batch_id]['failed'] += 1
                    
                ACTIVE_BATCHES[batch_id]['completed_workflows'] += 1

            # Actualizar persistencia en disco del JSON del trabajo
            session_manager.update_job(session_job_id, 
                results=ACTIVE_BATCHES[batch_id]['results'],
                status='processing'
            )
                
            return {'success': True, 'generated_images': saved, 'workflow': data['wf']['id']}
            
        except Exception as e:
            print(f"❌ [BATCH FATAL] Error en hilo _wait: {e}")
            with BATCH_LOCK:
                ACTIVE_BATCHES[batch_id]['completed_workflows'] += 1
                ACTIVE_BATCHES[batch_id]['failed'] += 1
            return {'success': False, 'error': str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: # Reducido workers por seguridad
        futs = {ex.submit(_wait, pid, data): pid for pid, data in submitted.items()}
        for f in concurrent.futures.as_completed(futs):
            try:
                results.append(f.result())
            except Exception as e:
                print(f"Error en future: {e}")

    # Cierre final del lote
    with BATCH_LOCK:
        ACTIVE_BATCHES[batch_id]["status"] = "completed"
    
    session_manager.update_job(session_job_id, status='completed', results=ACTIVE_BATCHES[batch_id]['results'])

    return results