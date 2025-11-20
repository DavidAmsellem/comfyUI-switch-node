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
    try:
        # 1. Esperar a ComfyUI (Sin callbacks, solo esperar)
        outputs = wait_for_completion(prompt_id, timeout=600)
        
        if not outputs: raise Exception("Sin respuesta de ComfyUI")

        # 2. Procesar imágenes
        generated_images = extract_generated_images(outputs, file_info['filename'], include_upscale)
        
        # Usamos la ruta física del archivo input (clave para que no falle la carga)
        input_path = file_info['input_path']
        
        orig_info, saved_imgs = save_images_to_our_output(
            output_dir, input_path, generated_images, file_info['filename'], 
            include_upscale, job_id, workflow_name, style_id
        )
        
        frontend_images = [img for img in saved_imgs if img.get('image_type') == 'composition'] or saved_imgs[:1]
        
        # 3. Guardar resultado FINAL (Única escritura de cierre)
        session_manager.update_job(job_id, 
            status='completed', 
            current_operation='Completado', 
            results=frontend_images
        )

    except Exception as e:
        log_error(f"Error background: {e}")
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

        # Guardar archivo físico
        base_name = file.filename.rsplit('.', 1)[0]
        output_dir = create_output_directory(base_name)
        input_path, workflow_filename = save_uploaded_image(file, base_name)
        file_info = {'filename': file.filename, 'input_path': input_path}

        # Workflow
        workflow = load_workflow(workflow_name)
        updated_workflow = update_workflow(workflow, workflow_filename, frame_color, style_id, style_node_id, base_name)
        prompt_id = submit_workflow_to_comfyui(updated_workflow)
        
        # Actualizar con prompt_id
        session_manager.update_job(job_id, prompt_id=prompt_id)

        # Lanza hilo
        thread = threading.Thread(target=process_job_background, args=(job_id, prompt_id, workflow_name, frame_color, style_id, include_upscale, file_info, output_dir, updated_workflow))
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "job_id": job_id})

    except Exception as e:
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