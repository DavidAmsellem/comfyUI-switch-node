import os
import uuid
import io
from PIL import Image
from werkzeug.utils import secure_filename
from config import COMFYUI_INPUT_DIR, COMFYUI_OUTPUT_DIR, WORKFLOW_CONFIG, OUR_OUTPUT_DIR
from utils.logger import log_info, log_error
from job_persistence import session_manager
from datetime import datetime

def save_uploaded_image(file, base_name=None):
    if not base_name:
        base_name = secure_filename(file.filename.rsplit('.', 1)[0] if '.' in file.filename else 'image')
    unique_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.png"
    input_path = os.path.join(COMFYUI_INPUT_DIR, unique_filename)
    
    try:
        image = Image.open(file.stream)
        if image.mode != 'RGB': image = image.convert('RGB')
        
        if image.width > 2048 or image.height > 2048:
            image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            
        image.save(input_path, format='PNG')
        file.stream.seek(0)
        return input_path, unique_filename
    except Exception as e:
        if os.path.exists(input_path): os.remove(input_path)
        raise e

def create_output_directory(base_name):
    output_dir = os.path.join(OUR_OUTPUT_DIR, base_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def find_image_file(filename, subfolder=''):
    possible = [
        os.path.join(COMFYUI_OUTPUT_DIR, subfolder, filename) if subfolder else os.path.join(COMFYUI_OUTPUT_DIR, filename),
        os.path.join(COMFYUI_OUTPUT_DIR, filename)
    ]
    for path in possible:
        if os.path.exists(path): return path
    
    # Búsqueda recursiva
    for root, _, files in os.walk(COMFYUI_OUTPUT_DIR):
        if filename in files: return os.path.join(root, filename)
    return None

def extract_generated_images(outputs, original_filename=None, include_upscale=True):
    # Simplificado para brevedad
    final_images = []
    save_node_id = WORKFLOW_CONFIG['save_image_node_id']
    
    for node_id in ['704', save_node_id, '696']:
        if node_id in outputs and 'images' in outputs[node_id]:
            for img in outputs[node_id]['images']:
                fname = img.get('filename', '')
                itype = 'composition' if node_id == '704' else ('upscale' if node_id == '696' else 'output')
                
                # Filtrar upscales si no se piden
                if itype == 'upscale' and not include_upscale: continue
                
                final_images.append({
                    'filename': fname, 'subfolder': img.get('subfolder', ''),
                    'type': img.get('type', 'output'), 'node_id': node_id, 'image_type': itype
                })
    return final_images

def save_images_to_our_output(output_dir, original_file, generated_images, original_filename, include_upscale, job_id, workflow_name=None, style_id=None):
    saved_images = []
    
    # 1. Guardar original
    orig_path = os.path.join(output_dir, "original.jpg")
    try:
        original_file.stream.seek(0)
        img = Image.open(original_file.stream).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=90, optimize=True)
        with open(orig_path, 'wb') as f: f.write(buffer.getvalue())
        
        buffer.seek(0)
        orig_url = session_manager.save_job_image(job_id, buffer.read(), "original.jpg")
        original_info = {'filename': "original.jpg", 'session_url': orig_url, 'status': 'saved'}
    except Exception as e:
        original_info = {'error': str(e)}

    # 2. Guardar generadas
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for i, img_info in enumerate(generated_images):
        src = find_image_file(img_info['filename'], img_info['subfolder'])
        if not src: continue
        
        itype = img_info.get('image_type', 'gen')
        wflow = workflow_name.replace('/', '_') if workflow_name else 'workflow'
        base = secure_filename(original_filename.rsplit('.', 1)[0])
        
        if itype == 'composition':
            dest_name = f"{wflow}_{style_id or 'ns'}_{base}_{timestamp}.jpg"
        else:
            dest_name = f"upscale_{base}_{timestamp}.jpg"

        dest_path = os.path.join(output_dir, dest_name)
        
        try:
            img = Image.open(src).convert('RGB')
            img.save(dest_path, 'JPEG', quality=90)
            
            with open(dest_path, 'rb') as f:
                s_url = session_manager.save_job_image(job_id, f.read(), dest_name)
            
            saved_images.append({
                'filename': dest_name, 'session_url': s_url, 
                'image_type': itype, 'status': 'saved'
            })
        except Exception as e:
            log_error(f"Error guardando {dest_name}: {e}")

    return original_info, saved_images