import os
import uuid
import io
import shutil
from PIL import Image
from werkzeug.utils import secure_filename
from config import COMFYUI_INPUT_DIR, COMFYUI_OUTPUT_DIR, WORKFLOW_CONFIG, OUR_OUTPUT_DIR
from utils.logger import log_info, log_error
from job_persistence import individual_session_manager
from datetime import datetime

def save_single_image_incremental(output_dir, image_info, original_filename, job_id, workflow_name=None, style_id=None):
    """
    Guarda una sola imagen de forma incremental (similar a batch)
    Retorna la información de la imagen para actualizar el job inmediatamente
    """
    from utils.logger import log_info, log_error
    
    log_info(f"🔍 [INCREMENTAL {job_id[:8]}] Iniciando guardado incremental")
    log_info(f"🔍 [INCREMENTAL {job_id[:8]}] image_info: {image_info}")
    log_info(f"🔍 [INCREMENTAL {job_id[:8]}] output_dir: {output_dir}")
    
    src = find_image_file(image_info['filename'], image_info['subfolder'])
    if not src:
        log_error(f"❌ [INCREMENTAL {job_id[:8]}] No se encontró archivo fuente: {image_info['filename']}")
        return None
    
    log_info(f"🔍 [INCREMENTAL {job_id[:8]}] Archivo fuente encontrado: {src}")
    
    # Construir nombre de archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    itype = image_info.get('image_type', 'gen')
    wflow = workflow_name.replace('/', '_') if workflow_name else 'workflow'
    base = secure_filename(original_filename.rsplit('.', 1)[0])
    
    if itype == 'composition': 
        dest_name = f"{wflow}_{style_id or 'ns'}_{base}_{timestamp}.jpg"
    else: 
        dest_name = f"upscale_{base}_{timestamp}.jpg"
    
    dest_path = os.path.join(output_dir, dest_name)
    log_info(f"🔍 [INCREMENTAL {job_id[:8]}] Destino: {dest_path}")
    
    try:
        # Guardar físicamente
        log_info(f"🔍 [INCREMENTAL {job_id[:8]}] Abriendo imagen...")
        img_gen = Image.open(src).convert('RGB')
        log_info(f"🔍 [INCREMENTAL {job_id[:8]}] Guardando en disco...")
        img_gen.save(dest_path, 'JPEG', quality=90)
        
        # Guardar en sesión
        log_info(f"🔍 [INCREMENTAL {job_id[:8]}] Guardando en sesión...")
        with open(dest_path, 'rb') as f:
            session_url = individual_session_manager.save_job_image(job_id, f.read(), dest_name)
        
        # Construir URLs
        base_name = os.path.basename(output_dir)
        direct_url = f"/get-image/{base_name}/{dest_name}"
        log_info(f"🔍 [INCREMENTAL {job_id[:8]}] URLs: direct={direct_url}, session={session_url}")
        
        result = {
            'filename': dest_name, 
            'url': direct_url,
            'session_url': session_url, 
            'image_type': itype, 
            'status': 'saved'
        }
        
        log_info(f"✅ [INCREMENTAL {job_id[:8]}] Guardado exitoso: {dest_name}")
        return result
        
    except Exception as e:
        log_error(f"❌ [INCREMENTAL {job_id[:8]}] Error guardando {dest_name}: {e}")
        import traceback
        log_error(f"❌ [INCREMENTAL {job_id[:8]}] Traceback: {traceback.format_exc()}")
        return None

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
    for root, _, files in os.walk(COMFYUI_OUTPUT_DIR):
        if filename in files: return os.path.join(root, filename)
    return None

def extract_generated_images(outputs, original_filename=None, include_upscale=True):
    final_images = []
    save_node_ids = ['704', WORKFLOW_CONFIG.get('save_image_node_id', '704'), '696']
    for node_id in outputs:
        if node_id in save_node_ids or 'images' in outputs[node_id]:
            if 'images' in outputs[node_id]:
                for img in outputs[node_id]['images']:
                    fname = img.get('filename', '')
                    if node_id == '704' or 'comfyui' in fname.lower(): itype = 'composition'
                    elif node_id == '696' or 'upscale' in fname.lower(): itype = 'upscale'
                    else: itype = 'output'
                    if itype == 'upscale' and not include_upscale: continue
                    final_images.append({'filename': fname, 'subfolder': img.get('subfolder', ''), 'type': img.get('type', 'output'), 'node_id': node_id, 'image_type': itype})
    return final_images

def extract_generated_images_individual(outputs, original_filename=None, include_upscale=True):
    """
    Versión específica para individual jobs con filtrado de archivos temporales
    """
    final_images = []
    save_node_ids = ['704', WORKFLOW_CONFIG.get('save_image_node_id', '704'), '696']
    for node_id in outputs:
        if node_id in save_node_ids or 'images' in outputs[node_id]:
            if 'images' in outputs[node_id]:
                for img in outputs[node_id]['images']:
                    fname = img.get('filename', '')
                    
                    # 🔥 FILTRO DE ARCHIVOS TEMPORALES (solo para individual)
                    fname_lower = fname.lower()
                    temporal_patterns = ['tmp_', 'temp_', '_temp']
                    is_temporal = any(pattern in fname_lower for pattern in temporal_patterns)
                    
                    if is_temporal:
                        from utils.logger import log_info
                        log_info(f"🗑️ [INDIVIDUAL-FILTER] Descartando archivo temporal: {fname}")
                        continue  # Saltar archivos temporales
                    
                    # 🔥 FILTRO DE TIPO 'temp' (solo para individual)
                    if img.get('type', 'output') == 'temp':
                        from utils.logger import log_info
                        log_info(f"🗑️ [INDIVIDUAL-FILTER] Descartando archivo tipo temp: {fname}")
                        continue  # Saltar archivos tipo temp
                    
                    if node_id == '704' or 'comfyui' in fname.lower(): itype = 'composition'
                    elif node_id == '696' or 'upscale' in fname.lower(): itype = 'upscale'
                    else: itype = 'output'
                    if itype == 'upscale' and not include_upscale: continue
                    final_images.append({'filename': fname, 'subfolder': img.get('subfolder', ''), 'type': img.get('type', 'output'), 'node_id': node_id, 'image_type': itype})
    return final_images

def save_images_to_our_output(output_dir, original_file_source, generated_images, original_filename, include_upscale, job_id, workflow_name=None, style_id=None):
    saved_images = []
    orig_path = os.path.join(output_dir, "original.jpg")
    try:
        # Soporte para String (Path) y Stream (Flask)
        img = None
        if isinstance(original_file_source, str): 
             img = Image.open(original_file_source).convert('RGB')
        elif hasattr(original_file_source, 'stream'):
            original_file_source.stream.seek(0)
            img = Image.open(original_file_source.stream).convert('RGB')
        elif hasattr(original_file_source, 'read'):
             if hasattr(original_file_source, 'seek'): original_file_source.seek(0)
             img = Image.open(original_file_source).convert('RGB')

        if img:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=90, optimize=True)
            with open(orig_path, 'wb') as f: 
                f.write(buffer.getvalue())
            
            # Guardar en sesión y construir URLs
            buffer.seek(0)
            session_url = individual_session_manager.save_job_image(job_id, buffer.read(), "original.jpg")
            
            # URL directa para el endpoint
            base_name = os.path.basename(output_dir)
            direct_url = f"/get-image/{base_name}/original.jpg"
            
            log_info(f"✅ Imagen original guardada: {orig_path}")
            log_info(f"   🔗 Direct URL: {direct_url}")
            log_info(f"   💾 Session URL: {session_url}")
            
            original_info = {
                'filename': "original.jpg", 
                'url': direct_url,
                'session_url': session_url, 
                'image_type': 'original',
                'status': 'saved'
            }
        else:
            raise Exception("Fuente de imagen inválida")
    except Exception as e:
        original_info = {'error': str(e)}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, img_info in enumerate(generated_images):
        src = find_image_file(img_info['filename'], img_info['subfolder'])
        if not src: continue
        itype = img_info.get('image_type', 'gen')
        wflow = workflow_name.replace('/', '_') if workflow_name else 'workflow'
        base = secure_filename(original_filename.rsplit('.', 1)[0])
        if itype == 'composition': dest_name = f"{wflow}_{style_id or 'ns'}_{base}_{timestamp}.jpg"
        else: dest_name = f"upscale_{base}_{timestamp}.jpg"
        dest_path = os.path.join(output_dir, dest_name)
        try:
            img_gen = Image.open(src).convert('RGB')
            img_gen.save(dest_path, 'JPEG', quality=90)
            
            # Guardar en sesión y obtener URL de sesión
            with open(dest_path, 'rb') as f:
                session_url = individual_session_manager.save_job_image(job_id, f.read(), dest_name)
            
            # Construir URL directa para el endpoint /get-image
            base_name = os.path.basename(output_dir)  # Nombre de la carpeta (ej: bedroom_123456)
            direct_url = f"/get-image/{base_name}/{dest_name}"
            
            log_info(f"✅ Imagen guardada: {dest_path}")
            log_info(f"   📁 Base dir: {base_name}")
            log_info(f"   🔗 Direct URL: {direct_url}")
            log_info(f"   💾 Session URL: {session_url}")
            
            saved_images.append({
                'filename': dest_name, 
                'url': direct_url,          # URL principal para el frontend
                'session_url': session_url, # URL de sesión como backup
                'image_type': itype, 
                'status': 'saved'
            })
            
        except Exception as e:
            log_error(f"Error guardando {dest_name}: {e}")
    return original_info, saved_images