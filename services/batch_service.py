import threading
import time
import uuid
import io
import os
from PIL import Image
from datetime import datetime
from werkzeug.utils import secure_filename

from config import COMFYUI_INPUT_DIR, OUR_OUTPUT_DIR
from utils.logger import log_info, log_error, log_warning
from services.comfy_service import submit_workflow_to_comfyui, wait_for_completion_simple, interrupt_current_processing, delete_queue_items
from services.workflow_service import load_workflow, update_workflow
from services.file_service import create_output_directory, extract_generated_images, find_image_file
from job_persistence import session_manager

ACTIVE_BATCHES = {}
BATCH_LOCK = threading.Lock()
BATCH_THROTTLE_LOCK = threading.Lock()
LAST_BATCH_SUBMIT_TIME = 0
CURRENT_BATCH_PROMPTS = 0

# Control de concurrencia de batches
BATCH_PROCESSING_LOCK = threading.Lock()
CURRENT_PROCESSING_BATCH = None

def is_batch_processing():
    """Verifica si hay algún batch en fase de envío de prompts actualmente"""
    global CURRENT_PROCESSING_BATCH
    with BATCH_PROCESSING_LOCK:
        return CURRENT_PROCESSING_BATCH is not None

def get_current_processing_batch():
    """Obtiene el ID del batch que está en fase de envío de prompts actualmente"""
    global CURRENT_PROCESSING_BATCH
    with BATCH_PROCESSING_LOCK:
        return CURRENT_PROCESSING_BATCH

def enforce_batch_throttle(num_prompts):
    global LAST_BATCH_SUBMIT_TIME, CURRENT_BATCH_PROMPTS
    with BATCH_THROTTLE_LOCK:
        now = time.time()
        wait = max(0, (LAST_BATCH_SUBMIT_TIME + CURRENT_BATCH_PROMPTS) - now)
        if wait > 0: time.sleep(wait)
        LAST_BATCH_SUBMIT_TIME = time.time()
        CURRENT_BATCH_PROMPTS = num_prompts
        return wait

def cancel_batch_job(batch_id):
    global CURRENT_PROCESSING_BATCH
    deleted_count = 0
    
    with BATCH_LOCK:
        if batch_id not in ACTIVE_BATCHES:
            return False, "Lote no encontrado (quizás ya terminó)"
        
        batch = ACTIVE_BATCHES[batch_id]
        
        # 1. Detener hilos y marcar estado
        batch['is_cancelled'] = True
        batch['status'] = 'cancelled'
        pids_to_kill = batch.get('comfy_pids', [])
        results_so_far = batch.get('results', [])
        orig_filename = batch.get('original_filename', 'unknown')

    # 2. Si es el batch actual en fase de envío, liberamos el lock de procesamiento
    with BATCH_PROCESSING_LOCK:
        if CURRENT_PROCESSING_BATCH == batch_id:
            CURRENT_PROCESSING_BATCH = None
            log_info(f"🔓 [BATCH] Liberado lock de procesamiento por cancelación de {batch_id} (estaba en fase de envío)")
        # Si no está en CURRENT_PROCESSING_BATCH, significa que ya terminó la fase de envío

    # 3. Acciones a ComfyUI (Fuera del lock)
    if pids_to_kill:
        interrupt_current_processing()
        delete_queue_items(pids_to_kill)
    
    # 4. LIMPIEZA DE ARCHIVOS FÍSICOS
    # Calculamos la carpeta donde están las fotos
    base_name = secure_filename(orig_filename.rsplit('.', 1)[0])
    output_folder = os.path.join(OUR_OUTPUT_DIR, base_name)
    
    print(f"🧹 [CLEANUP] Iniciando limpieza de archivos para Lote {batch_id} en {output_folder}")

    for res in results_so_far:
        images = res.get('generated_images', [])
        for img in images:
            filename = img.get('filename')
            if filename:
                file_path = os.path.join(output_folder, filename)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"   🗑️ Borrado: {filename}")
                except Exception as e:
                    print(f"   ⚠️ Error borrando {filename}: {e}")

    # 5. Limpiar referencias en memoria para que no salgan más en el frontend
    with BATCH_LOCK:
        ACTIVE_BATCHES[batch_id]['results'] = [] # Vaciamos la lista
        ACTIVE_BATCHES[batch_id]['completed_workflows'] = 0 

    # 6. Actualizar persistencia (JSON)
    # Marcamos como cancelado y borramos resultados del JSON también
    session_manager.update_job(batch['session_job_id'], status='cancelled', results=[])
    
    return True, f"Cancelado y {deleted_count} imágenes eliminadas."

def process_all_workflows_simultaneously_with_tracking(image_data, workflows, common_params, batch_id, session_job_id=None):
    global CURRENT_PROCESSING_BATCH
    
    # 1. Verificar si ya hay un batch procesándose
    with BATCH_PROCESSING_LOCK:
        if CURRENT_PROCESSING_BATCH is not None:
            log_error(f"❌ [BATCH] Ya hay un batch procesándose: {CURRENT_PROCESSING_BATCH}. No se puede iniciar {batch_id}")
            with BATCH_LOCK:
                if batch_id in ACTIVE_BATCHES:
                    ACTIVE_BATCHES[batch_id]["status"] = "rejected"
                    ACTIVE_BATCHES[batch_id]["error"] = f"Otro batch está procesándose: {CURRENT_PROCESSING_BATCH}"
            return [{'success': False, 'error': f'Otro batch está procesándose: {CURRENT_PROCESSING_BATCH}'}]
        
        # Marcar este batch como el que está procesándose
        CURRENT_PROCESSING_BATCH = batch_id
        log_info(f"🔒 [BATCH] Lock adquirido para batch {batch_id}")

    try:
        results = []
        submitted = {}
        comfy_pids = [] 
        
        orig_name_log = common_params.get('original_filename', 'desconocido')
        print(f"\n🚀 [BATCH START] Iniciando Lote {batch_id} para imagen: {orig_name_log}")

        with BATCH_LOCK:
            if batch_id in ACTIVE_BATCHES:
                ACTIVE_BATCHES[batch_id]["status"] = "submitting"
                ACTIVE_BATCHES[batch_id]["is_cancelled"] = False
                # GUARDAMOS EL NOMBRE ORIGINAL PARA PODER BORRAR DESPUÉS
                ACTIVE_BATCHES[batch_id]["original_filename"] = orig_name_log

        image_data.seek(0)
        master = Image.open(image_data).convert('RGB')
        if master.width > 2048: master.thumbnail((2048, 2048))
        
        # 1. Enviar prompts
        for i, wf in enumerate(workflows):
            # Chequeo temprano de cancelación
            with BATCH_LOCK:
                if ACTIVE_BATCHES.get(batch_id, {}).get('is_cancelled', False): break

            try:
                uniq_name = f"batch_{batch_id}_{i:03d}.png"
                path = os.path.join(COMFYUI_INPUT_DIR, uniq_name)
                master.save(path)
                
                w_data = load_workflow(wf["id"])
                base_name_clean = secure_filename(orig_name_log.rsplit('.', 1)[0])
                
                w_upd = update_workflow(w_data, uniq_name, common_params['frame_color'], common_params['style'], None, base_name_clean)
                
                pid = submit_workflow_to_comfyui(w_upd)
                
                comfy_pids.append(pid)
                submitted[pid] = {'wf': wf, 'idx': i}
                
            except Exception as e:
                print(f"❌ [BATCH ERROR] Fallo al enviar: {e}")
                with BATCH_LOCK: ACTIVE_BATCHES[batch_id]['failed'] += 1

        with BATCH_LOCK:
            if batch_id in ACTIVE_BATCHES:
                ACTIVE_BATCHES[batch_id]['comfy_pids'] = comfy_pids
                ACTIVE_BATCHES[batch_id]["status"] = "processing"

        # LIBERAR LOCK DE PROCESAMIENTO DESPUÉS DE ENVIAR TODOS LOS PROMPTS
        # Ahora otros batches pueden empezar a enviar sus prompts también
        with BATCH_PROCESSING_LOCK:
            if CURRENT_PROCESSING_BATCH == batch_id:
                CURRENT_PROCESSING_BATCH = None
                log_info(f"🔓 [BATCH] Lock de procesamiento liberado tras enviar prompts del batch {batch_id}")
            else:
                log_warning(f"⚠️ [BATCH] Inconsistencia al liberar lock: se esperaba {batch_id} pero el actual es {CURRENT_PROCESSING_BATCH}")
        
        # 2. Esperar resultados usando approach simple como app_new.py
        log_info(f"🔄 [BATCH {batch_id}] Esperando {len(submitted)} workflows con approach simple...")
        
        # Función simple de espera por cada job (como en app_new.py)
        def _wait_for_job(pid, data):
            """Esperar un job individual - approach simple"""
            try:
                # Chequeo de cancelación
                with BATCH_LOCK:
                    if ACTIVE_BATCHES.get(batch_id, {}).get('is_cancelled', False):
                        return {'success': False, 'error': 'Cancelled by user'}
                        
                # Esperar completion simple
                outputs = wait_for_completion_simple(pid, timeout=60000)
                
                if not outputs:
                    with BATCH_LOCK:
                        if ACTIVE_BATCHES.get(batch_id, {}).get('is_cancelled', False):
                            return {'success': False, 'error': 'Cancelled'}
                    raise Exception("ComfyUI devolvió respuesta vacía")

                # Procesar imágenes (igual que antes)
                orig_name = common_params.get('original_filename', 'batch_output')
                base_name = secure_filename(orig_name.rsplit('.', 1)[0]) 
                out_dir = create_output_directory(base_name) 
                
                imgs = extract_generated_images(outputs, orig_name)
                saved = []
                
                for im in imgs:
                    src = find_image_file(im['filename'], im['subfolder'])
                    if src:
                        # Lógica Singleton para Upscale
                        is_upscale = im.get('image_type') == 'upscale'
                        if is_upscale:
                            new_name = f"{base_name}_upscaled.jpg"
                            dest = os.path.join(out_dir, new_name)
                            if os.path.exists(dest): continue # Ya existe, saltamos
                        else:
                            new_name = f"{data['wf']['id'].replace('/','_')}_{uuid.uuid4().hex[:6]}.jpg"
                            dest = os.path.join(out_dir, new_name)

                        try:
                            Image.open(src).convert('RGB').save(dest, 'JPEG')
                            final_url = f"/get-image/{base_name}/{new_name}"
                            
                            with open(dest, 'rb') as f:
                                 _ = session_manager.save_job_image(session_job_id or batch_id, f.read(), new_name)
                            
                            saved.append({'filename': new_name, 'session_url': final_url, 'url': final_url})
                            
                        except Exception as e_save:
                            log_error(f"❌ [BATCH] Error guardando imagen: {e_save}")

                with BATCH_LOCK:
                    # Chequeo final de cancelación antes de actualizar contadores
                    if ACTIVE_BATCHES.get(batch_id, {}).get('is_cancelled', False): 
                        return {'success': False, 'error': 'Cancelled'}

                    if len(saved) > 0:
                        ACTIVE_BATCHES[batch_id]['successful'] += 1
                        ACTIVE_BATCHES[batch_id]['results'].extend([
                            {'workflow': data['wf']['id'], 'generated_images': saved}
                        ])
                    else:
                        ACTIVE_BATCHES[batch_id]['successful'] += 1
                        
                    ACTIVE_BATCHES[batch_id]['completed_workflows'] += 1

                    # Actualizar job de sesión con progreso
                    session_manager.update_job(session_job_id, 
                        results=ACTIVE_BATCHES[batch_id]['results'],
                        status='processing'
                    )
                        
                return {'success': True, 'generated_images': saved, 'workflow': data['wf']['id']}
                
            except Exception as e:
                log_error(f"❌ [BATCH] Error procesando workflow {data['wf']['id']}: {e}")
                with BATCH_LOCK:
                    if not ACTIVE_BATCHES.get(batch_id, {}).get('is_cancelled', False):
                        ACTIVE_BATCHES[batch_id]['completed_workflows'] += 1
                        ACTIVE_BATCHES[batch_id]['failed'] += 1
                return {'success': False, 'error': str(e)}

        # Usar ThreadPoolExecutor simple (como en app_new.py original)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            futs = {ex.submit(_wait_for_job, pid, data): pid for pid, data in submitted.items()}
            for f in concurrent.futures.as_completed(futs):
                try: 
                    result = f.result()
                    results.append(result)
                    log_info(f"📈 [BATCH {batch_id}] Job completado: {len(results)}/{len(submitted)}")
                except Exception as e:
                    log_error(f"❌ [BATCH] Error obteniendo resultado: {e}")
                    results.append({'success': False, 'error': str(e)})

        # Estado final
        with BATCH_LOCK:
            # Si fue cancelado, no cambiamos el status a 'completed' para no confundir
            if not ACTIVE_BATCHES[batch_id].get('is_cancelled', False):
                 ACTIVE_BATCHES[batch_id]["status"] = "completed"
                 session_manager.update_job(session_job_id, status='completed', results=ACTIVE_BATCHES[batch_id]['results'])
                 print(f"🏁 [BATCH END] Lote {batch_id} finalizado correctamente.")
            else:
                 print(f"🛑 [BATCH END] Lote {batch_id} se detuvo por cancelación.")

        return results

    finally:
        # Solo liberar el lock si todavía lo tenemos (por si hubo error antes del envío de prompts)
        with BATCH_PROCESSING_LOCK:
            if CURRENT_PROCESSING_BATCH == batch_id:
                CURRENT_PROCESSING_BATCH = None
                log_info(f"🔓 [BATCH] Lock de procesamiento liberado en finally para batch {batch_id} (debido a error temprano)")
            # Si ya fue liberado anteriormente, no hacemos nada