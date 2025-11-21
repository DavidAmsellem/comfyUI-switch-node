from flask import Blueprint, request, jsonify, send_file
from services.file_service import save_uploaded_image, create_output_directory, extract_generated_images_individual, save_images_to_our_output, save_single_image_incremental
from services.workflow_service import load_workflow, update_workflow
from services.comfy_service import submit_workflow_to_comfyui, verify_image_accessibility
from services.comfy_service_simple import wait_for_completion_simple as wait_for_completion
from utils.helpers import allowed_file
from utils.logger import log_info, log_error
from job_persistence import individual_session_manager
import os
import threading
import io
from datetime import datetime
from PIL import Image
from config import WORKFLOW_CONFIG, OUR_OUTPUT_DIR, COMFYUI_OUTPUT_DIR

job_bp = Blueprint('job_routes', __name__)

def process_job_background(job_id, prompt_id, workflow_name, frame_color, style_id, include_upscale, file_info, output_dir, updated_workflow):
    log_info(f"🟢 [BACKGROUND {job_id[:8]}] *** THREAD INICIADO *** - PID: {os.getpid()}")
    
    try:
        log_info(f"🔥 [BACKGROUND {job_id[:8]}] Iniciando procesamiento background")
        log_info(f"🔥 [BACKGROUND {job_id[:8]}] PromptID: {prompt_id}")
        
        # 🔥 ACTUALIZAR ESTADO INMEDIATAMENTE A PROCESSING
        log_info(f"📝 [BACKGROUND {job_id[:8]}] Actualizando estado a 'processing'...")
        individual_session_manager.update_job(job_id, 
            status='processing',
            current_operation='Esperando respuesta de ComfyUI...',
            prompt_id=prompt_id
        )
        log_info(f"✅ [BACKGROUND {job_id[:8]}] Estado actualizado a 'processing'")
        
        # 1. Esperar a ComfyUI (Sin callbacks, solo esperar)
        log_info(f"⏳ [BACKGROUND {job_id[:8]}] Esperando a ComfyUI...")
        outputs = wait_for_completion(prompt_id, timeout=600)
        
        if not outputs: 
            log_error(f"❌ [BACKGROUND {job_id[:8]}] Sin respuesta de ComfyUI")
            raise Exception("Sin respuesta de ComfyUI")

        log_info(f"✅ [BACKGROUND {job_id[:8]}] ComfyUI completado, procesando imágenes...")
        
        # 2. Procesar imágenes INCREMENTALMENTE
        generated_images = extract_generated_images_individual(outputs, file_info['filename'], include_upscale)
        log_info(f"📷 [BACKGROUND {job_id[:8]}] Imágenes extraídas: {len(generated_images)}")
        
        # 2a. Primero guardar imagen original
        input_path = file_info['input_path']  # Usar la ruta del archivo físico
        log_info(f"🔍 [BACKGROUND {job_id[:8]}] Guardando imagen original desde: {input_path}")
        log_info(f"🔍 [BACKGROUND {job_id[:8]}] Output dir: {output_dir}")
        
        orig_path = os.path.join(output_dir, "original.jpg")
        try:
            log_info(f"🔍 [BACKGROUND {job_id[:8]}] Abriendo imagen...")
            img = Image.open(input_path).convert('RGB')
            
            log_info(f"🔍 [BACKGROUND {job_id[:8]}] Creando buffer...")
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=90, optimize=True)
            
            log_info(f"🔍 [BACKGROUND {job_id[:8]}] Guardando en disco: {orig_path}")
            with open(orig_path, 'wb') as f: 
                f.write(buffer.getvalue())
            
            log_info(f"🔍 [BACKGROUND {job_id[:8]}] Guardando en sesión...")
            buffer.seek(0)
            session_url = individual_session_manager.save_job_image(job_id, buffer.read(), "original.jpg")
            base_name = os.path.basename(output_dir)
            direct_url = f"/get-image/{base_name}/original.jpg"
            
            log_info(f"🔍 [BACKGROUND {job_id[:8]}] URLs creadas - Direct: {direct_url}, Session: {session_url}")
            
            original_result = {
                'filename': "original.jpg", 
                'url': direct_url,
                'session_url': session_url, 
                'image_type': 'original',
                'status': 'saved'
            }
            
            log_info(f"🔍 [BACKGROUND {job_id[:8]}] Actualizando job con imagen original...")
            # Actualizar job con imagen original
            update_success = individual_session_manager.update_job(job_id, 
                status='processing',
                current_operation='Imagen original guardada...',
                results=[original_result]
            )
            log_info(f"✅ [BACKGROUND {job_id[:8]}] Imagen original guardada y job actualizado: {update_success}")
            
        except Exception as e:
            log_error(f"❌ [BACKGROUND {job_id[:8]}] Error guardando original: {e}")
            import traceback
            log_error(f"❌ [BACKGROUND {job_id[:8]}] Traceback: {traceback.format_exc()}")
        
        # 2b. Procesar y guardar cada imagen generada incrementalmente
        all_results = [original_result] if 'original_result' in locals() else []
        
        for i, img_info in enumerate(generated_images):
            log_info(f"💾 [BACKGROUND {job_id[:8]}] Guardando imagen {i+1}/{len(generated_images)}: {img_info['filename']}")
            
            saved_img = save_single_image_incremental(
                output_dir, img_info, file_info['filename'], 
                job_id, workflow_name, style_id
            )
            
            if saved_img:
                all_results.append(saved_img)
                
                # Actualizar job inmediatamente con la nueva imagen
                individual_session_manager.update_job(job_id, 
                    status='processing',
                    current_operation=f'Guardando imagen {i+1}/{len(generated_images)}...',
                    results=all_results
                )
                log_info(f"✅ [BACKGROUND {job_id[:8]}] Imagen {i+1} guardada y job actualizado - Total: {len(all_results)}")
            else:
                log_error(f"❌ [BACKGROUND {job_id[:8]}] Error guardando imagen {i+1}")
        
        # 3. Filtrar para frontend (solo composición)
        frontend_images = [img for img in all_results if img.get('image_type') == 'composition'] or all_results[:1]
        log_info(f"🖼️ [BACKGROUND {job_id[:8]}] Imágenes para frontend: {len(frontend_images)}")
        
        # 4. Actualización FINAL
        individual_session_manager.update_job(job_id, 
            status='completed', 
            current_operation='Completado', 
            results=all_results  # Todas las imágenes incluyendo original
        )
        
        log_info(f"🎉 [BACKGROUND {job_id[:8]}] Procesamiento completado exitosamente!")

    except Exception as e:
        import traceback
        log_error(f"💥 [BACKGROUND {job_id[:8]}] Error background: {e}")
        log_error(f"💥 [BACKGROUND {job_id[:8]}] Error type: {type(e).__name__}")
        log_error(f"💥 [BACKGROUND {job_id[:8]}] Traceback completo:")
        log_error(traceback.format_exc())
        
        # Actualizar job con error
        individual_session_manager.update_job(job_id, 
            status='error', 
            error=str(e),
            current_operation=f'Error: {str(e)}'
        )

@job_bp.route('/process-image', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files: return jsonify({"error": "Falta imagen"}), 400
        file = request.files['image']
        
        workflow_name = request.form.get('workflow', 'default')
        frame_color = request.form.get('frame_color', 'black')
        style_id = request.form.get('style', 'default')
        include_upscale = request.form.get('include_upscale', 'true').lower() == 'true'
        style_node_id = request.form.get('style_node', None)

        # Crear job inicial
        job_id = individual_session_manager.create_job(
            job_type='individual', workflow=workflow_name, frame_color=frame_color,
            style=style_id, original_filename=file.filename
        )
        
        log_info(f"🆕 [JOB {job_id[:8]}] Nuevo trabajo individual creado")
        log_info(f"📁 [JOB {job_id[:8]}] Archivo: {file.filename} | Workflow: {workflow_name} | Style: {style_id}")

        # Guardar archivo físico
        base_name = file.filename.rsplit('.', 1)[0]
        output_dir = create_output_directory(base_name)
        input_path, workflow_filename = save_uploaded_image(file, base_name)
        file_info = {'filename': file.filename, 'input_path': input_path}

        log_info(f"💾 [JOB {job_id[:8]}] Archivo guardado: {input_path}")
        log_info(f"📂 [JOB {job_id[:8]}] Directorio output: {output_dir}")

        # Workflow
        log_info(f"⚙️ [JOB {job_id[:8]}] Cargando workflow...")
        workflow = load_workflow(workflow_name)
        
        log_info(f"🔧 [JOB {job_id[:8]}] Actualizando workflow...")
        updated_workflow = update_workflow(workflow, workflow_filename, frame_color, style_id, style_node_id, base_name)
        
        log_info(f"📤 [JOB {job_id[:8]}] Enviando workflow a ComfyUI...")
        prompt_id = submit_workflow_to_comfyui(updated_workflow)
        
        if not prompt_id:
            log_error(f"❌ [JOB {job_id[:8]}] No se obtuvo prompt_id de ComfyUI!")
            raise Exception("Error: No se pudo enviar workflow a ComfyUI")
        
        log_info(f"🚀 [JOB {job_id[:8]}] Workflow enviado a ComfyUI - PromptID: {prompt_id}")
        
        # Actualizar con prompt_id
        log_info(f"💾 [JOB {job_id[:8]}] Actualizando job con prompt_id...")
        individual_session_manager.update_job(job_id, prompt_id=prompt_id)

        log_info(f"🧵 [JOB {job_id[:8]}] Creando thread de procesamiento background...")
        
        # Lanza hilo
        try:
            thread = threading.Thread(target=process_job_background, args=(job_id, prompt_id, workflow_name, frame_color, style_id, include_upscale, file_info, output_dir, updated_workflow))
            thread.daemon = True
            
            log_info(f"▶️ [JOB {job_id[:8]}] Iniciando thread...")
            thread.start()
            
            log_info(f"✅ [JOB {job_id[:8]}] Thread iniciado exitosamente - Thread alive: {thread.is_alive()}")
            
            # 🔥 ESPERAR UN MOMENTO Y VERIFICAR QUE EL THREAD SIGUE VIVO
            import time
            time.sleep(0.5)  # Esperar medio segundo
            
            if thread.is_alive():
                log_info(f"✅ [JOB {job_id[:8]}] Thread confirmado activo después de 0.5s")
            else:
                log_error(f"❌ [JOB {job_id[:8]}] ¡WARNING! Thread murió inmediatamente después de iniciarse!")
                
        except Exception as thread_error:
            log_error(f"💥 [JOB {job_id[:8]}] Error creando/iniciando thread: {thread_error}")
            raise Exception(f"Error iniciando procesamiento: {thread_error}")

        log_info(f"🎉 [JOB {job_id[:8]}] Job creado exitosamente y thread iniciado")
        return jsonify({"success": True, "job_id": job_id})

    except Exception as e:
        log_error(f"💥 [JOB ENDPOINT] Error en process_image: {e}")
        log_error(f"💥 [JOB ENDPOINT] Error type: {type(e)}")
        return jsonify({"error": str(e)}), 500

@job_bp.route('/get-image/<base_name>/<filename>', methods=['GET'])
def get_image(base_name, filename):
    # Log para debug
    log_info(f"🔍 Buscando imagen: {base_name}/{filename}")
    
    # Ruta 1: Nuestro directorio de salida
    path1 = os.path.join(OUR_OUTPUT_DIR, base_name, filename)
    log_info(f"   📁 Ruta 1: {path1}")
    
    if os.path.exists(path1):
        log_info(f"   ✅ Encontrada en ruta 1, sirviendo archivo")
        return send_file(path1, mimetype='image/jpeg' if filename.lower().endswith(('.jpg', '.jpeg')) else None)
    
    # Ruta 2: Directorio de ComfyUI
    path2 = os.path.join(COMFYUI_OUTPUT_DIR, base_name, filename)
    log_info(f"   📁 Ruta 2: {path2}")
    
    if os.path.exists(path2):
        log_info(f"   ✅ Encontrada en ruta 2, sirviendo archivo")
        return send_file(path2, mimetype='image/jpeg' if filename.lower().endswith(('.jpg', '.jpeg')) else None)
    
    log_error(f"   ❌ Archivo NO encontrado en ninguna ruta: {base_name}/{filename}")
    return jsonify({"error": "Imagen no encontrada"}), 404