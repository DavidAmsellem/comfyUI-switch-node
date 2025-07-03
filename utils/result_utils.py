import os
from .logging import log_success, log_error

def extract_generated_images(outputs, WORKFLOW_CONFIG):
    """
    Extrae las imágenes generadas de los outputs de ComfyUI
    Retorna: lista de información de imágenes
    """
    images = []
    save_node_id = WORKFLOW_CONFIG['save_image_node_id']
    
    # Buscar en el nodo SaveImage principal
    if save_node_id in outputs and 'images' in outputs[save_node_id]:
        for image_info in outputs[save_node_id]['images']:
            if 'filename' in image_info:
                images.append({
                    'filename': image_info['filename'],
                    'subfolder': image_info.get('subfolder', ''),
                    'type': image_info.get('type', 'output'),
                    'node_id': save_node_id
                })
                log_success(f"Imagen encontrada: {image_info['filename']}")
    
    # Buscar en otros nodos SaveImage si no se encontró nada
    if not images:
        for node_id, node_data in outputs.items():
            if isinstance(node_data, dict) and 'images' in node_data:
                for image_info in node_data['images']:
                    if 'filename' in image_info:
                        images.append({
                            'filename': image_info['filename'],
                            'subfolder': image_info.get('subfolder', ''),
                            'type': image_info.get('type', 'output'),
                            'node_id': node_id
                        })
    
    log_success(f"Total de imágenes encontradas: {len(images)}")
    return images

def find_image_file(filename, subfolder, COMFYUI_OUTPUT_DIR):
    """
    Busca un archivo de imagen en el directorio de output de ComfyUI
    Retorna: ruta completa del archivo o None
    """
    possible_paths = [
        os.path.join(COMFYUI_OUTPUT_DIR, subfolder, filename) if subfolder else os.path.join(COMFYUI_OUTPUT_DIR, filename),
        os.path.join(COMFYUI_OUTPUT_DIR, filename)
    ]
    
    # Búsqueda recursiva como fallback
    for root, dirs, files in os.walk(COMFYUI_OUTPUT_DIR):
        if filename in files:
            possible_paths.append(os.path.join(root, filename))
    
    for path in possible_paths:
        if os.path.exists(path):
            log_success(f"Imagen encontrada en: {path}")
            return path
    
    log_error(f"Imagen no encontrada: {filename}")
    return None
