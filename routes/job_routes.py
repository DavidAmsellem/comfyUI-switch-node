from flask import Blueprint, request, jsonify, send_file
from services.file_service import save_uploaded_image, create_output_directory, extract_generated_images, save_images_to_our_output
from services.workflow_service import load_workflow, update_workflow
from services.comfy_service import submit_workflow_to_comfyui, wait_for_completion, verify_image_accessibility
from utils.helpers import allowed_file
from utils.logger import log_info
from job_persistence import session_manager
import os
from config import WORKFLOW_CONFIG, OUR_OUTPUT_DIR, COMFYUI_OUTPUT_DIR

job_bp = Blueprint('job_routes', __name__)

@job_bp.route('/process-image', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files: return jsonify({"error": "Falta imagen"}), 400
        file = request.files['image']
        if not allowed_file(file.filename): return jsonify({"error": "Tipo de archivo no permitido"}), 400

        workflow_name = request.form.get('workflow', 'default')
        frame_color = request.form.get('frame_color', 'black')
        style_id = request.form.get('style', 'default')
        include_upscale = request.form.get('include_upscale', 'true').lower() == 'true'

        job_id = session_manager.create_job(
            job_type='individual', workflow=workflow_name, frame_color=frame_color,
            style=style_id, original_filename=file.filename
        )
        session_manager.update_job(job_id, status='processing', current_operation='Iniciando...')

        base_name = file.filename.rsplit('.', 1)[0]
        output_dir = create_output_directory(base_name)
        
        input_path, workflow_filename = save_uploaded_image(file, base_name)
        
        # Verificamos accesibilidad usando la función importada de comfy_service
        if not verify_image_accessibility(workflow_filename):
            log_info(f"Advertencia: ComfyUI podría no tener acceso a {workflow_filename}")

        workflow = load_workflow(workflow_name)
        updated_workflow = update_workflow(workflow, workflow_filename, frame_color, style_id, None, base_name)
        
        prompt_id = submit_workflow_to_comfyui(updated_workflow)
        session_manager.update_job(job_id, prompt_id=prompt_id, current_operation='Esperando ComfyUI...')
        
        outputs = wait_for_completion(prompt_id)
        generated_images = extract_generated_images(outputs, file.filename, include_upscale)
        
        orig_info, saved_imgs = save_images_to_our_output(
            output_dir, file, generated_images, file.filename, include_upscale, job_id, workflow_name, style_id
        )

        frontend_images = [img for img in saved_imgs if img.get('image_type') == 'composition'] or saved_imgs[:1]
        
        response = {
            "success": True, "job_id": job_id, "prompt_id": prompt_id,
            "final_image": frontend_images[0] if frontend_images else None,
            "generated_images": frontend_images
        }
        
        session_manager.update_job(job_id, status='completed', results=frontend_images, response_data=response)
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@job_bp.route('/get-image/<base_name>/<filename>', methods=['GET'])
def get_image(base_name, filename):
    path1 = os.path.join(OUR_OUTPUT_DIR, base_name, filename)
    if os.path.exists(path1): return send_file(path1)
    path2 = os.path.join(COMFYUI_OUTPUT_DIR, base_name, filename)
    if os.path.exists(path2): return send_file(path2)
    return jsonify({"error": "No encontrado"}), 404