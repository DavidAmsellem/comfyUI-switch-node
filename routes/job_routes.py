from flask import Blueprint, request, jsonify, send_file
from services.file_service import save_uploaded_image, create_output_directory, extract_generated_images, save_images_to_our_output
from services.workflow_service import load_workflow, update_workflow
from services.comfy_service import submit_workflow_to_comfyui, wait_for_completion, verify_image_accessibility
from utils.helpers import allowed_file
from utils.logger import log_info, log_error
from job_persistence import session_manager
import os
import threading
from config import WORKFLOW_CONFIG, OUR_OUTPUT_DIR, COMFYUI_OUTPUT_DIR

job_bp = Blueprint('job_routes', __name__)

def process_job_background(job_id, prompt_id, workflow_name, frame_color, style_id, include_upscale, file_info, output_dir, updated_workflow):
    log_info(f"🟢 [BACKGROUND {job_id[:8]}] *** THREAD INICIADO *** - PID: {os.getpid()}")
    
    try:
        log_info(f"🔥 [BACKGROUND {job_id[:8]}] Iniciando procesamiento background")
        log_info(f"🔥 [BACKGROUND {job_id[:8]}] PromptID: {prompt_id}")
        
        # 1. Esperar a ComfyUI (Sin callbacks, solo esperar)
        log_info(f"⏳ [BACKGROUND {job_id[:8]}] Esperando a ComfyUI...")
        outputs = wait_for_completion(prompt_id, timeout=600)
        
        if not outputs: 
            log_error(f"❌ [BACKGROUND {job_id[:8]}] Sin respuesta de ComfyUI")
            raise Exception("Sin respuesta de ComfyUI")

        log_info(f"✅ [BACKGROUND {job_id[:8]}] ComfyUI completado, procesando imágenes...")
        
        # 2. Procesar imágenes
        generated_images = extract_generated_images(outputs, file_info['filename'], include_upscale)
        log_info(f"📷 [BACKGROUND {job_id[:8]}] Imágenes extraídas: {len(generated_images)}")
        
        # Usamos la ruta física del archivo input (clave para que no falle la carga)
        input_path = file_info['input_path']
        
        orig_info, saved_imgs = save_images_to_our_output(
            output_dir, input_path, generated_images, file_info['filename'], 
            include_upscale, job_id, workflow_name, style_id
        )
        
        frontend_images = [img for img in saved_imgs if img.get('image_type') == 'composition'] or saved_imgs[:1]
        log_info(f"🖼️ [BACKGROUND {job_id[:8]}] Imágenes para frontend: {len(frontend_images)}")
        
        # Log de cada imagen que se va a enviar al frontend
        for i, img in enumerate(frontend_images):
            log_info(f"   🖼️ Imagen {i+1}: {img.get('filename')} - URL: {img.get('url')} - Type: {img.get('image_type')}")
        
        # 3. Guardar resultado FINAL (Única escritura de cierre)
        log_info(f"💾 [BACKGROUND {job_id[:8]}] Actualizando job como completado...")
        session_manager.update_job(job_id, 
            status='completed', 
            current_operation='Completado', 
            results=frontend_images
        )
        
        log_info(f"🎉 [BACKGROUND {job_id[:8]}] Procesamiento completado exitosamente!")

    except Exception as e:
        log_error(f"💥 [BACKGROUND {job_id[:8]}] Error background: {e}")
        log_error(f"💥 [BACKGROUND {job_id[:8]}] Error type: {type(e)}")
        log_error(f"💥 [BACKGROUND {job_id[:8]}] Error args: {e.args}")
        session_manager.update_job(job_id, status='error', error=str(e))

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
        job_id = session_manager.create_job(
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
        session_manager.update_job(job_id, prompt_id=prompt_id)

        log_info(f"🧵 [JOB {job_id[:8]}] Creando thread de procesamiento background...")
        
        # Lanza hilo
        try:
            thread = threading.Thread(target=process_job_background, args=(job_id, prompt_id, workflow_name, frame_color, style_id, include_upscale, file_info, output_dir, updated_workflow))
            thread.daemon = True
            
            log_info(f"▶️ [JOB {job_id[:8]}] Iniciando thread...")
            thread.start()
            
            log_info(f"✅ [JOB {job_id[:8]}] Thread iniciado exitosamente - Thread alive: {thread.is_alive()}")
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