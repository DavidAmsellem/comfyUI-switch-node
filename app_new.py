#!/usr/bin/env python3
"""
API REST NUEVA - Implementación simplificada desde cero
"""
import os
import json
import uuid
import random
import copy
import time
import shutil
import threading
import concurrent.futures
import stat
from datetime import datetime
from io import BytesIO

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import requests
from werkzeug.utils import secure_filename

# Importar configuración de estilos
from style_presets import get_available_styles, apply_style_to_workflow, get_workflow_nodes_for_style

# Configuración básica
app = Flask(__name__)
CORS(app)

# URLs y directorios
COMFYUI_HOST = os.getenv('COMFYUI_HOST', 'localhost')
COMFYUI_PORT = os.getenv('COMFYUI_PORT', '8188')
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

# Sistema de tracking de batches en progreso
ACTIVE_BATCHES = {}  # batch_id -> batch_info
BATCH_LOCK = threading.Lock()

# Directorios principales (simplificados)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMFYUI_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
COMFYUI_INPUT_DIR = os.path.join(COMFYUI_ROOT, 'input')
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_ROOT, 'output')
WORKFLOWS_DIR = os.path.join(BASE_DIR, 'workflows')
TEMP_UPLOADS_DIR = os.path.join(BASE_DIR, 'temp_uploads')

# Crear directorios necesarios
for directory in [COMFYUI_INPUT_DIR, COMFYUI_OUTPUT_DIR, TEMP_UPLOADS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configuración del workflow (actualizar según tu nuevo workflow)
WORKFLOW_CONFIG = {
    'load_image_node_id': '699',  # ID del nodo LoadImage para el cuadro
    'save_image_node_id': '704',  # ID del nodo SaveImage principal
    'frame_node_id': '692',       # ID del nodo DynamicFrameNode
    'allowed_extensions': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
    'frame_colors': ['black', 'white', 'brown', 'gold', 'red', 'blue']
}

# ==================== FUNCIONES UTILITARIAS ====================

def log_info(message):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ℹ️  {message}")

def log_success(message):
    """Log de éxito"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ✅ {message}")

def log_error(message):
    """Log de error"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ❌ {message}")

def log_warning(message):
    """Log de advertencia"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ⚠️  {message}")

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in WORKFLOW_CONFIG['allowed_extensions']

def generate_unique_filename(original_filename):
    """Genera un nombre de archivo único manteniendo la extensión"""
    if '.' in original_filename:
        name, ext = original_filename.rsplit('.', 1)
        return f"{uuid.uuid4().hex}.{ext.lower()}"
    return f"{uuid.uuid4().hex}.png"

# ==================== GESTIÓN DE ARCHIVOS ====================

def save_uploaded_image(file, base_name=None):
    """
    Guarda la imagen subida en el directorio de input de ComfyUI
    Retorna: (input_path, filename_for_workflow)
    """
    if not base_name:
        base_name = secure_filename(file.filename.rsplit('.', 1)[0] if '.' in file.filename else 'image')
    
    # Generar nombre único para evitar conflictos
    unique_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.png"
    input_path = os.path.join(COMFYUI_INPUT_DIR, unique_filename)
    
    try:
        # Abrir y procesar la imagen
        image = Image.open(file.stream)
        
        # Convertir a RGB si es necesario (eliminar canal alpha)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Crear fondo blanco
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Redimensionar si es muy grande (para evitar problemas de memoria)
        max_size = 2048
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            log_info(f"Imagen redimensionada a: {image.width}x{image.height}")
        
        # Guardar como PNG con calidad alta
        image.save(input_path, format='PNG', optimize=False)
        file.stream.seek(0)  # Reset stream para uso posterior
        
        # Establecer permisos de lectura para todos
        try:
            import stat
            os.chmod(input_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        except:
            pass  # No crítico si falla
        
        # Verificar que el archivo se guardó correctamente
        if os.path.exists(input_path) and os.path.getsize(input_path) > 0:
            file_size = os.path.getsize(input_path)
            log_success(f"Imagen guardada correctamente: {unique_filename} ({file_size} bytes)")
            log_info(f"Ruta completa: {input_path}")
            return input_path, unique_filename
        else:
            raise Exception("El archivo no se guardó correctamente")
        
    except Exception as e:
        log_error(f"Error al guardar imagen: {str(e)}")
        # Limpiar archivo parcial si existe
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except:
                pass
        raise

def create_output_directory(base_name):
    """
    Crea directorio de salida para las imágenes procesadas
    Retorna: ruta del directorio creado
    """
    output_dir = os.path.join(COMFYUI_OUTPUT_DIR, base_name)
    os.makedirs(output_dir, exist_ok=True)
    log_info(f"Directorio de salida creado: {output_dir}")
    return output_dir

# ==================== GESTIÓN DE WORKFLOWS ====================

def load_workflow(workflow_name):
    """
    Carga un workflow desde archivo JSON
    Soporta tanto nombres simples como rutas completas (e.g., "bathroom/H80x60/cuadro-bathroom-open-H60x802")
    Retorna: diccionario del workflow
    """
    # Limpiar el nombre del workflow
    workflow_name = workflow_name.strip()
    
    # Construir posibles rutas
    possible_paths = []
    
    # Si contiene barras, es una ruta relativa completa
    if '/' in workflow_name:
        # Ejemplo: "bathroom/H80x60/cuadro-bathroom-open-H60x802"
        full_path = os.path.join(WORKFLOWS_DIR, workflow_name + '.json')
        possible_paths.append(full_path)
        
        # También probar la ruta directa
        direct_path = os.path.join(WORKFLOWS_DIR, workflow_name)
        possible_paths.append(direct_path)
    
    # Rutas tradicionales (nombre simple)
    possible_paths.extend([
        os.path.join(WORKFLOWS_DIR, f"{workflow_name}.json"),
        os.path.join(WORKFLOWS_DIR, workflow_name),
    ])
    
    # Búsqueda recursiva como respaldo
    for root, dirs, files in os.walk(WORKFLOWS_DIR):
        for file in files:
            if file.endswith('.json'):
                # Coincidencia exacta del nombre del archivo
                if file == f"{workflow_name}.json" or file == workflow_name:
                    possible_paths.append(os.path.join(root, file))
                
                # Coincidencia del nombre sin extensión
                file_base = file.replace('.json', '')
                if file_base == workflow_name:
                    possible_paths.append(os.path.join(root, file))
    
    # Buscar el primer archivo que exista
    workflow_path = None
    for path in possible_paths:
        if os.path.exists(path):
            workflow_path = path
            break
    
    if not workflow_path:
        log_error(f"Workflow '{workflow_name}' no encontrado. Rutas intentadas: {possible_paths[:5]}")
        raise FileNotFoundError(f"Workflow '{workflow_name}' no encontrado")
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        log_success(f"Workflow cargado: {workflow_path}")
        return workflow
        
    except Exception as e:
        log_error(f"Error al cargar workflow: {str(e)}")
        raise

def update_workflow(workflow, image_filename, frame_color='black', style_id='default', style_node_id=None, output_subfolder=None):
    """
    Actualiza el workflow con la nueva imagen, configuraciones y estilo
    
    LÓGICA IMPLEMENTADA:
    - Por defecto: img2img (más fiel a la imagen original)
    - Con estilo aplicado: text2img + ControlNet depth/canny con strength 0.85
    
    Retorna: workflow actualizado
    """
    workflow_copy = copy.deepcopy(workflow)
    
    # Determinar si se aplica estilo (para decidir img2img vs text2img)
    has_style = style_id and style_id != 'default'
    
    # Verificar si el estilo fuerza text2img
    forces_text2img = False
    if has_style:
        from style_presets import style_forces_text2img
        forces_text2img = style_forces_text2img(style_id)
    
    log_info(f"🎯 Modo de procesamiento: {'TEXT2IMG + ControlNet 0.85 (estilo fuerza)' if forces_text2img else 'IMG2IMG (preservar original)'} (estilo: {style_id})")
    
    # Actualizar nodo LoadImage
    load_node_id = WORKFLOW_CONFIG['load_image_node_id']
    if load_node_id in workflow_copy:
        workflow_copy[load_node_id]['inputs']['image'] = image_filename
        log_success(f"Nodo LoadImage ({load_node_id}) actualizado con: {image_filename}")
    else:
        log_warning(f"Nodo LoadImage ({load_node_id}) no encontrado en el workflow")
    
    # Actualizar nodo DynamicFrameNode (color del marco)
    frame_node_id = WORKFLOW_CONFIG['frame_node_id']
    if frame_node_id in workflow_copy and frame_color in WORKFLOW_CONFIG['frame_colors']:
        workflow_copy[frame_node_id]['inputs']['preset'] = frame_color
        log_success(f"Color del marco actualizado a: {frame_color}")
    else:
        log_warning(f"No se pudo actualizar el color del marco")
    
    # CONFIGURAR MODO DE WORKFLOW Y CONTROLNET SEGÚN ESTILO
    if forces_text2img:
        # CON ESTILO QUE FUERZA TEXT2IMG: Cambiar a text2img y activar ControlNet con strength alta
        log_info("🎨 Estilo aplicado: Configurando TEXT2IMG + ControlNet 0.85...")
        
        # Cambiar a text2img
        for node_id, node_data in workflow_copy.items():
            if isinstance(node_data, dict) and node_data.get('class_type') == 'SeargeOperatingMode':
                if 'inputs' in node_data and 'workflow_mode' in node_data['inputs']:
                    node_data['inputs']['workflow_mode'] = 'text-to-image'
                    log_success(f"Modo cambiado a TEXT2IMG en nodo {node_id}")
        
        # Configurar ControlNet Depth con strength 0.85
        for node_id, node_data in workflow_copy.items():
            if (isinstance(node_data, dict) and 
                node_data.get('class_type') == 'SeargeControlnetAdapterV2' and
                'inputs' in node_data and 
                node_data['inputs'].get('controlnet_mode') == 'depth'):
                
                node_data['inputs']['strength'] = 0.85
                log_success(f"ControlNet Depth strength actualizado a 0.85 en nodo {node_id}")
        
        # Configurar ControlNet Canny con strength 0.85
        for node_id, node_data in workflow_copy.items():
            if (isinstance(node_data, dict) and 
                node_data.get('class_type') == 'SeargeControlnetAdapterV2' and
                'inputs' in node_data and 
                node_data['inputs'].get('controlnet_mode') == 'canny'):
                
                node_data['inputs']['strength'] = 0.85
                log_success(f"ControlNet Canny strength actualizado a 0.85 en nodo {node_id}")
        
        # Aplicar el estilo
        from style_presets import get_style_prompt, get_style_negative_prompt, style_forces_text2img
        style_prompt = get_style_prompt(style_id)
        negative_prompt = get_style_negative_prompt(style_id)
        log_info(f"📝 Prompt del estilo: '{style_prompt[:100]}...'")
        if negative_prompt:
            log_info(f"❌ Prompt negativo del estilo: '{negative_prompt[:100]}...'")
        
        workflow_copy = apply_style_to_workflow(workflow_copy, style_id, style_node_id)
        
        # Verificar que se aplicó correctamente
        if style_node_id:
            if style_node_id in workflow_copy:
                applied_value = ""
                node = workflow_copy[style_node_id]
                if "inputs" in node:
                    applied_value = node["inputs"].get("prompt", node["inputs"].get("text", ""))
                log_success(f"Estilo aplicado: {style_id} al nodo {style_node_id}")
                log_info(f"Valor aplicado en nodo {style_node_id}: '{applied_value}'")
            else:
                log_error(f"Nodo especificado {style_node_id} no existe en el workflow")
        else:
            # Verificar en el nodo de estilo por defecto para Searge
            style_node_6 = workflow_copy.get("6", {})
            if "inputs" in style_node_6:
                applied_value = style_node_6["inputs"].get("prompt", "")
                log_success(f"Estilo aplicado: {style_id} (auto-detectado al nodo 6)")
                log_info(f"Valor aplicado en nodo 6: '{applied_value}'")
            else:
                log_warning("No se pudo verificar la aplicación del estilo")
    
    else:
        # SIN ESTILO O ESTILO QUE NO FUERZA TEXT2IMG: Asegurar img2img y ControlNet con strength baja
        log_info("📷 Sin estilo o estilo compatible: Manteniendo IMG2IMG...")
        
        # Asegurar img2img
        for node_id, node_data in workflow_copy.items():
            if isinstance(node_data, dict) and node_data.get('class_type') == 'SeargeOperatingMode':
                if 'inputs' in node_data and 'workflow_mode' in node_data['inputs']:
                    node_data['inputs']['workflow_mode'] = 'image-to-image'
                    log_success(f"Modo mantenido en IMG2IMG en nodo {node_id}")
        
        # Configurar ControlNet con strength más baja para preservar imagen original
        for node_id, node_data in workflow_copy.items():
            if (isinstance(node_data, dict) and 
                node_data.get('class_type') == 'SeargeControlnetAdapterV2' and
                'inputs' in node_data and 
                node_data['inputs'].get('controlnet_mode') == 'depth'):
                
                node_data['inputs']['strength'] = 0.2  # Strength baja para img2img
                log_success(f"ControlNet Depth strength mantenido en 0.2 para IMG2IMG en nodo {node_id}")
        
        for node_id, node_data in workflow_copy.items():
            if (isinstance(node_data, dict) and 
                node_data.get('class_type') == 'SeargeControlnetAdapterV2' and
                'inputs' in node_data and 
                node_data['inputs'].get('controlnet_mode') == 'canny'):
                
                node_data['inputs']['strength'] = 0.71  # Strength actual para img2img
                log_success(f"ControlNet Canny strength mantenido en 0.71 para IMG2IMG en nodo {node_id}")
    
    # Actualizar nodos SaveImage (subfolder si se especifica)
    if output_subfolder:
        for node_id, node_data in workflow_copy.items():
            if isinstance(node_data, dict) and node_data.get('class_type') == 'SaveImage':
                if 'inputs' in node_data and 'filename_prefix' in node_data['inputs']:
                    old_prefix = node_data['inputs']['filename_prefix']
                    new_prefix = f"{output_subfolder}/{old_prefix}"
                    node_data['inputs']['filename_prefix'] = new_prefix
                    log_info(f"SaveImage {node_id}: {old_prefix} → {new_prefix}")
    
    # Randomizar seeds
    for node_id, node_data in workflow_copy.items():
        if isinstance(node_data, dict) and 'inputs' in node_data and 'seed' in node_data['inputs']:
            new_seed = random.randint(1, 2**32-1)
            node_data['inputs']['seed'] = new_seed
    
    log_success(f"✅ Workflow actualizado correctamente en modo: {'TEXT2IMG + ControlNet 0.85' if forces_text2img else 'IMG2IMG (fiel al original)'}")
    return workflow_copy

# ==================== COMUNICACIÓN CON COMFYUI ====================

def verify_image_accessibility(filename):
    """
    Verifica que ComfyUI pueda acceder al archivo de imagen
    Retorna: True si es accesible, False en caso contrario
    """
    try:
        # Verificar que el archivo existe físicamente
        input_path = os.path.join(COMFYUI_INPUT_DIR, filename)
        if not os.path.exists(input_path):
            log_error(f"Archivo no existe en disco: {input_path}")
            return False
        
        file_size = os.path.getsize(input_path)
        if file_size == 0:
            log_error(f"Archivo vacío: {input_path}")
            return False
        
        log_info(f"Archivo verificado en disco: {filename} ({file_size} bytes)")
        
        # Hacer una petición a ComfyUI para verificar la imagen
        response = requests.get(f"{COMFYUI_URL}/view", params={'filename': filename}, timeout=10)
        if response.status_code == 200:
            log_success(f"Imagen accesible para ComfyUI: {filename}")
            return True
        else:
            log_warning(f"ComfyUI no puede acceder a la imagen: {filename} (status: {response.status_code})")
            
            # Intentar con diferentes parámetros
            response2 = requests.get(f"{COMFYUI_URL}/view", params={'filename': filename, 'type': 'input'}, timeout=10)
            if response2.status_code == 200:
                log_success(f"Imagen accesible para ComfyUI (con type=input): {filename}")
                return True
            
            return False
    except Exception as e:
        log_warning(f"Error verificando acceso a imagen: {str(e)}")
        return False

def submit_workflow_to_comfyui(workflow):
    """
    Envía el workflow a ComfyUI para procesamiento
    Retorna: prompt_id
    """
    client_id = str(uuid.uuid4())
    prompt_data = {
        "prompt": workflow,
        "client_id": client_id
    }
    
    try:
        response = requests.post(f"{COMFYUI_URL}/prompt", json=prompt_data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        prompt_id = result.get('prompt_id')
        
        if not prompt_id:
            raise ValueError("ComfyUI no devolvió prompt_id")
        
        log_success(f"Workflow enviado a ComfyUI. Prompt ID: {prompt_id}")
        return prompt_id
        
    except Exception as e:
        log_error(f"Error enviando workflow a ComfyUI: {str(e)}")
        raise

def wait_for_completion(prompt_id, timeout=300):
    """
    Espera a que ComfyUI complete el procesamiento
    Retorna: outputs del workflow
    """
    log_info(f"Esperando completion del prompt: {prompt_id}")
    
    for i in range(timeout):
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30)
            
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    
                    # Verificar si hay outputs
                    if 'outputs' in prompt_history:
                        log_success("Procesamiento completado")
                        return prompt_history['outputs']
                    
                    # Verificar errores
                    if 'status' in prompt_history and 'error' in prompt_history['status']:
                        error_msg = prompt_history['status']['error']
                        raise Exception(f"Error en ComfyUI: {error_msg}")
            
            if i % 10 == 0 and i > 0:
                log_info(f"Esperando... {i}/{timeout}s")
            
            time.sleep(1)
            
        except requests.exceptions.RequestException:
            time.sleep(1)
            continue
    
    raise TimeoutError(f"Timeout esperando completion después de {timeout} segundos")

# ==================== PROCESAMIENTO DE RESULTADOS ====================

def extract_generated_images(outputs):
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
                log_info(f"Imagen encontrada: {image_info['filename']}")
    
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
                        log_info(f"Imagen encontrada en nodo {node_id}: {image_info['filename']}")
    
    log_success(f"Total de imágenes encontradas: {len(images)}")
    return images

def find_image_file(filename, subfolder=''):
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

# ==================== RUTAS DEL API ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Verificación de estado del servicio"""
    try:
        # Verificar conexión con ComfyUI
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        comfyui_status = "ok" if response.status_code == 200 else "error"
    except:
        comfyui_status = "error"
    
    return jsonify({
        "status": "ok",
        "comfyui_connection": comfyui_status,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/styles', methods=['GET'])
def list_styles():
    """Lista estilos predefinidos disponibles"""
    try:
        styles = get_available_styles()
        return jsonify({
            "styles": styles,
            "total": len(styles),
            "message": "Estilos cargados correctamente"
        })
    except Exception as e:
        log_error(f"Error cargando estilos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/workflows', methods=['GET'])
def list_workflows():
    """Lista workflows disponibles organizados por tipo y orientación"""
    workflows_structure = {}
    workflows_list = []
    
    if os.path.exists(WORKFLOWS_DIR):
        for root, dirs, files in os.walk(WORKFLOWS_DIR):
            for filename in files:
                if filename.endswith('.json'):
                    # Obtener la ruta relativa desde workflows/
                    rel_path = os.path.relpath(os.path.join(root, filename), WORKFLOWS_DIR)
                    path_parts = rel_path.replace('\\', '/').split('/')
                    
                    # Ejemplo: bathroom/H80x60/cuadro-bathroom-open-H60x802.json
                    if len(path_parts) >= 3:
                        room_type = path_parts[0]  # bathroom
                        orientation = path_parts[1]  # H80x60
                        workflow_name = path_parts[2].replace('.json', '')  # cuadro-bathroom-open-H60x802
                        
                        # ID único para el workflow
                        workflow_id = f"{room_type}/{orientation}/{workflow_name}"
                        
                        # Crear estructura jerárquica
                        if room_type not in workflows_structure:
                            workflows_structure[room_type] = {}
                        if orientation not in workflows_structure[room_type]:
                            workflows_structure[room_type][orientation] = []
                        
                        workflow_info = {
                            "id": workflow_id,
                            "name": workflow_name,
                            "filename": filename,
                            "room_type": room_type,
                            "orientation": orientation,
                            "path": rel_path.replace('\\', '/'),
                            "status": "available"
                        }
                        
                        workflows_structure[room_type][orientation].append(workflow_info)
                        workflows_list.append(workflow_info)
    
    return jsonify({
        "workflows": workflows_list,
        "structure": workflows_structure,
        "total": len(workflows_list),
        "config": WORKFLOW_CONFIG,
        "available_colors": WORKFLOW_CONFIG.get("frame_colors", ["black", "white", "brown", "gold", "silver"]),
        "available_styles": get_available_styles()
    })

@app.route('/process-image', methods=['POST'])
def process_image():
    """Procesa una imagen usando un workflow especificado"""
    try:
        log_info("=== INICIANDO PROCESAMIENTO DE IMAGEN ===")
        
        # Validar entrada
        if 'image' not in request.files:
            return jsonify({"error": "No se proporcionó imagen"}), 400
        
        file = request.files['image']
        if not file or file.filename == '':
            return jsonify({"error": "Archivo de imagen vacío"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Tipo de archivo no permitido"}), 400
        
        # Parámetros
        workflow_name = request.form.get('workflow', 'default')
        frame_color = request.form.get('frame_color', 'black')
        style_id = request.form.get('style', 'default')
        style_node_id = request.form.get('style_node', None)  # Nodo personalizado para aplicar estilo
        original_filename = request.form.get('original_filename', file.filename)
        
        log_info(f"Parámetros: workflow={workflow_name}, frame_color={frame_color}, style={style_id}, style_node={style_node_id}, file={original_filename}")
        
        # Validar color del marco
        if frame_color not in WORKFLOW_CONFIG['frame_colors']:
            frame_color = 'black'
            log_warning(f"Color de marco no válido, usando: {frame_color}")
        
        # Validar estilo
        available_styles = [style['id'] for style in get_available_styles()]
        if style_id not in available_styles:
            style_id = 'default'
            log_warning(f"Estilo no válido, usando: {style_id}")
        
        # Preparar nombres y directorios
        base_name = secure_filename(original_filename.rsplit('.', 1)[0] if '.' in original_filename else 'image')
        output_dir = create_output_directory(base_name)
        
        # Guardar imagen original
        log_info("Guardando imagen original...")
        original_path = os.path.join(output_dir, 'original.png')
        image = Image.open(file.stream)
        image.save(original_path, format='PNG')
        file.stream.seek(0)
        
        # Guardar en input de ComfyUI
        input_path, workflow_filename = save_uploaded_image(file, base_name)
        
        # Verificar que ComfyUI puede acceder al archivo (sin fallar si no puede)
        log_info("Verificando acceso a la imagen desde ComfyUI...")
        accessibility_check = verify_image_accessibility(workflow_filename)
        if not accessibility_check:
            log_warning("ComfyUI no puede verificar la imagen, pero continuando...")
            # Esperar un poco más para que el archivo se asiente
            time.sleep(1)
        
        # Cargar y actualizar workflow
        log_info(f"Cargando workflow: {workflow_name}")
        workflow = load_workflow(workflow_name)
        updated_workflow = update_workflow(workflow, workflow_filename, frame_color, style_id, style_node_id, base_name)
        
        # Enviar a ComfyUI
        log_info("Enviando a ComfyUI...")
        prompt_id = submit_workflow_to_comfyui(updated_workflow)
        
        # Esperar resultados
        log_info("Esperando resultados...")
        outputs = wait_for_completion(prompt_id)
        
        # Extraer imágenes generadas
        log_info("Extrayendo imágenes...")
        generated_images = extract_generated_images(outputs)
        
        # Copiar imágenes generadas al directorio de salida
        saved_images = []
        for img_info in generated_images:
            source_path = find_image_file(img_info['filename'], img_info['subfolder'])
            if source_path:
                dest_path = os.path.join(output_dir, f"result_{img_info['filename']}")
                shutil.copy2(source_path, dest_path)
                saved_images.append({
                    'filename': f"result_{img_info['filename']}",
                    'url': f"/get-image/{base_name}/result_{img_info['filename']}",
                    'original_filename': img_info['filename']
                })
                log_success(f"Imagen copiada: {dest_path}")
        
        # Crear respuesta
        processing_mode = "text2img + controlnet_0.85" if (style_id and style_id != 'default') else "img2img_preserving_original"
        
        response = {
            "success": True,
            "prompt_id": prompt_id,
            "workflow_used": workflow_name,
            "processing_mode": processing_mode,
            "frame_color": frame_color,
            "style_used": style_id,
            "style_node_used": style_node_id if style_node_id else "auto-detectado",
            "base_name": base_name,
            "output_dir": output_dir,
            "original_image": {
                "filename": "original.png",
                "url": f"/get-image/{base_name}/original.png"
            },
            "generated_images": saved_images,
            "total_images": len(saved_images),
            "message": f"Procesamiento completado en modo {processing_mode}. {len(saved_images)} imágenes generadas."
        }
        
        log_success("=== PROCESAMIENTO COMPLETADO ===")
        return jsonify(response)
        
    except FileNotFoundError as e:
        log_error(f"Workflow no encontrado: {str(e)}")
        return jsonify({"error": f"Workflow no encontrado: {str(e)}"}), 404
    except TimeoutError as e:
        log_error(f"Timeout en procesamiento: {str(e)}")
        return jsonify({"error": f"Timeout en procesamiento: {str(e)}"}), 408
    except Exception as e:
        log_error(f"Error en procesamiento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-image/<base_name>/<filename>', methods=['GET'])
def get_image(base_name, filename):
    """Descarga una imagen del directorio de salida"""
    try:
        # Sanitizar parámetros
        base_name = secure_filename(base_name)
        filename = secure_filename(filename)
        
        # Buscar archivo
        file_path = os.path.join(COMFYUI_OUTPUT_DIR, base_name, filename)
        
        if not os.path.exists(file_path):
            log_error(f"Archivo no encontrado: {file_path}")
            return jsonify({"error": "Archivo no encontrado"}), 404
        
        log_success(f"Enviando archivo: {file_path}")
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        log_error(f"Error al obtener imagen: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/workflow-nodes/<workflow_name>', methods=['GET'])
def get_workflow_nodes(workflow_name):
    """Obtiene los nodos candidatos para aplicar estilos en un workflow específico"""
    try:
        # Cargar el workflow
        workflow = load_workflow(workflow_name)
        
        # Obtener nodos candidatos
        candidate_nodes = get_workflow_nodes_for_style(workflow)
        
        return jsonify({
            "workflow_name": workflow_name,
            "candidate_nodes": candidate_nodes,
            "total": len(candidate_nodes),
            "message": f"Se encontraron {len(candidate_nodes)} nodos candidatos para aplicar estilos"
        })
    except FileNotFoundError:
        return jsonify({"error": f"Workflow no encontrado: {workflow_name}"}), 404
    except Exception as e:
        log_error(f"Error obteniendo nodos del workflow {workflow_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/batch-status/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """
    Obtiene el status actual de un batch en progreso
    """
    with BATCH_LOCK:
        if batch_id not in ACTIVE_BATCHES:
            return jsonify({"error": "Batch no encontrado"}), 404
        
        batch_info = ACTIVE_BATCHES[batch_id].copy()
    
    return jsonify(batch_info)

@app.route('/batch-status/<batch_id>', methods=['DELETE'])
def clear_batch_status(batch_id):
    """
    Limpia un batch completado del tracking
    """
    with BATCH_LOCK:
        if batch_id in ACTIVE_BATCHES:
            del ACTIVE_BATCHES[batch_id]
            return jsonify({"success": True, "message": f"Batch {batch_id} eliminado del tracking"})
        else:
            return jsonify({"error": "Batch no encontrado"}), 404

@app.route('/active-batches', methods=['GET'])
def get_active_batches():
    """
    Obtiene la lista de todos los batches activos
    """
    with BATCH_LOCK:
        batches = {bid: {"status": info["status"], "total_workflows": info["total_workflows"], 
                        "completed_workflows": info["completed_workflows"]} 
                  for bid, info in ACTIVE_BATCHES.items()}
    
    return jsonify({"active_batches": batches, "count": len(batches)})

@app.route('/')
def serve_client():
    """Sirve el cliente web principal"""
    client_path = os.path.join(BASE_DIR, 'web_client_fixed.html')
    if os.path.exists(client_path):
        return send_file(client_path)
    else:
        # Fallback al cliente original
        fallback_path = os.path.join(BASE_DIR, 'web_client.html')
        if os.path.exists(fallback_path):
            return send_file(fallback_path)
        else:
            return jsonify({
                "message": "ComfyUI API REST - Nueva implementación",
                "version": "2.0.0",
                "endpoints": ["/health", "/workflows", "/styles", "/workflow-nodes/<workflow_name>", "/process-image", "/process-batch", "/get-image"],
                "web_clients": ["/web_client_fixed.html", "/web_client.html"]
            })

@app.route('/web_client_fixed.html')
def serve_fixed_client():
    """Sirve el cliente web corregido"""
    client_path = os.path.join(BASE_DIR, 'web_client_fixed.html')
    if os.path.exists(client_path):
        return send_file(client_path)
    else:
        return jsonify({"error": "Cliente web corregido no encontrado"}), 404

@app.route('/web_client.html')
def serve_original_client():
    """Servir el cliente web original (fallback)"""
    try:
        return send_file('web_client.html')
    except FileNotFoundError:
        return jsonify({
            "error": "Cliente web original no encontrado",
            "message": "Use /web_client_fixed.html en su lugar"
        }), 404

# ==================== FUNCIONES AUXILIARES ADICIONALES ====================

def is_allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida (alias de allowed_file)"""
    return allowed_file(filename)

def get_available_workflows():
    """Obtiene la lista de workflows disponibles"""
    workflows = []
    
    if os.path.exists(WORKFLOWS_DIR):
        for root, dirs, files in os.walk(WORKFLOWS_DIR):
            for filename in files:
                if filename.endswith('.json'):
                    # Obtener la ruta relativa desde workflows/
                    rel_path = os.path.relpath(os.path.join(root, filename), WORKFLOWS_DIR)
                    path_parts = rel_path.replace('\\', '/').split('/')
                    
                    # Ejemplo: bathroom/H80x60/cuadro-bathroom-open-H60x802.json
                    if len(path_parts) >= 3:
                        room_type = path_parts[0]  # bathroom
                        orientation = path_parts[1]  # H80x60
                        workflow_name = path_parts[2].replace('.json', '')  # cuadro-bathroom-open-H60x802
                        
                        # ID único para el workflow
                        workflow_id = f"{room_type}/{orientation}/{workflow_name}"
                        
                        workflow_info = {
                            "id": workflow_id,
                            "name": workflow_name,
                            "filename": filename,
                            "room_type": room_type,
                            "orientation": orientation,
                            "path": rel_path.replace('\\', '/'),
                            "status": "available"
                        }
                        
                        workflows.append(workflow_info)
    
    return workflows

# ==================== PROCESAMIENTO EN LOTE ====================

@app.route('/process-batch', methods=['POST'])
def process_batch():
    """
    Procesa una imagen con múltiples workflows simultáneamente
    """
    try:
        log_info("📦 Iniciando procesamiento en lote...")
        
        # Validar datos de entrada
        if 'image' not in request.files or not request.files['image']:
            return jsonify({"error": "No se encontró archivo de imagen"}), 400
            
        image_file = request.files['image']
        
        if not is_allowed_file(image_file.filename):
            return jsonify({"error": f"Formato de archivo no permitido. Usar: {', '.join(WORKFLOW_CONFIG['allowed_extensions'])}"}), 400
        
        # Obtener parámetros del batch
        batch_config = {}
        
        # Verificar si se envió como JSON en batch_config
        if 'batch_config' in request.form:
            try:
                batch_config = json.loads(request.form['batch_config'])
                log_info(f"📋 Configuración del batch desde JSON: {batch_config}")
            except json.JSONDecodeError:
                log_warning("⚠️ Error decodificando batch_config JSON, usando parámetros individuales")
        
        # Filtros opcionales (fallback a parámetros individuales)
        if not batch_config.get('room_types') and 'room_types' in request.form:
            room_types_str = request.form['room_types']
            batch_config['room_types'] = [t.strip() for t in room_types_str.split(',') if t.strip()]
            
        if not batch_config.get('orientations') and 'orientations' in request.form:
            orientations_str = request.form['orientations']
            batch_config['orientations'] = [o.strip() for o in orientations_str.split(',') if o.strip()]
            
        if not batch_config.get('specific_workflows') and 'specific_workflows' in request.form:
            specific_str = request.form['specific_workflows']
            batch_config['specific_workflows'] = [w.strip() for w in specific_str.split(',') if w.strip()]
        
        # Parámetros comunes (pueden venir del JSON o del form)
        frame_color = batch_config.get('frame_color') or request.form.get('frame_color', 'black')
        style = batch_config.get('style') or request.form.get('style', 'default')
        
        log_info(f"📋 Configuración del batch: {batch_config}")
        log_info(f"🎨 Parámetros: frame_color={frame_color}, style={style}")
        
        # Validar estilo
        available_styles = get_available_styles()
        available_style_ids = [style['id'] for style in available_styles]
        if style not in available_style_ids:
            return jsonify({"error": f"Estilo no encontrado: {style}. Estilos disponibles: {available_style_ids}"}), 400
        
        # Obtener workflows disponibles
        available_workflows = get_available_workflows()
        
        # Filtrar workflows según criterios del batch
        filtered_workflows = filter_workflows_for_batch(batch_config, available_workflows)
        
        if not filtered_workflows:
            return jsonify({
                "error": "No se encontraron workflows que coincidan con los criterios especificados",
                "available_workflows": len(available_workflows),
                "criteria": batch_config
            }), 400
        
        log_info(f"🎯 Workflows seleccionados: {len(filtered_workflows)}/{len(available_workflows)}")
        
        # Preparar parámetros comunes
        common_params = {
            "frame_color": frame_color,
            "style": style
        }
        
        # Obtener nodos de estilo si es necesario
        if filtered_workflows:
            sample_workflow = load_workflow(filtered_workflows[0]["id"])
            style_nodes = get_workflow_nodes_for_style(sample_workflow)
            if style_nodes:
                common_params["style_node"] = style_nodes[0]["id"]
        
        # Generar ID único para este batch
        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
        
        # Inicializar tracking del batch
        with BATCH_LOCK:
            ACTIVE_BATCHES[batch_id] = {
                "batch_id": batch_id,
                "status": "starting",
                "total_workflows": len(filtered_workflows),
                "completed_workflows": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "start_time": time.time(),
                "estimated_completion": None,
                "current_operation": "Iniciando procesamiento...",
                "workflow_list": [w["id"] for w in filtered_workflows]
            }
        
        log_info(f"🚀 Iniciando procesamiento simultáneo de {len(filtered_workflows)} workflows...")
        log_info(f"📊 Batch ID para tracking: {batch_id}")
        
        # Guardar el contenido de la imagen en memoria antes de iniciar el thread
        image_file.seek(0)
        image_data = BytesIO(image_file.read())
        image_data.seek(0)
        
        # Iniciar procesamiento en thread separado
        def process_batch_async():
            try:
                results = process_all_workflows_simultáneamente_with_tracking(
                    image_data, filtered_workflows, common_params, batch_id
                )
                
                # Finalizar batch
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        batch_info = ACTIVE_BATCHES[batch_id]
                        batch_info["status"] = "completed"
                        batch_info["total_processing_time"] = round(time.time() - batch_info["start_time"], 2)
                        batch_info["final_results"] = results
                        
            except Exception as e:
                log_error(f"❌ Error en procesamiento async de batch {batch_id}: {str(e)}")
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        ACTIVE_BATCHES[batch_id]["status"] = "error"
                        ACTIVE_BATCHES[batch_id]["error"] = str(e)
        
        # Iniciar thread
        thread = threading.Thread(target=process_batch_async)
        thread.daemon = True
        thread.start()
        
        # Retornar inmediatamente el ID del batch para tracking
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "processing_mode": "asynchronous_with_tracking",
            "status": "processing",
            "total_workflows": len(filtered_workflows),
            "message": "Batch iniciado. Use GET /batch-status/{batch_id} para consultar progreso",
            "status_endpoint": f"/batch-status/{batch_id}",
            "workflow_list": [w["id"] for w in filtered_workflows],
            "batch_config": batch_config,
            "common_params": common_params
        })
        
    except Exception as e:
        log_error(f"❌ Error en procesamiento batch: {str(e)}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "processing_mode": "simultaneous"
        }), 500

def filter_workflows_for_batch(batch_config, available_workflows):
    """
    Filtra workflows según los criterios del batch
    """
    filtered = []
    
    room_types = batch_config.get("room_types", [])
    orientations = batch_config.get("orientations", [])
    specific_workflows = batch_config.get("specific_workflows", [])
    
    for workflow in available_workflows:
        # Si hay workflows específicos, usar solo esos
        if specific_workflows and workflow["id"] not in specific_workflows:
            continue
            
        # Filtrar por tipo de habitación
        if room_types and workflow["room_type"] not in room_types:
            continue
            
        # Filtrar por orientación  
        if orientations and workflow["orientation"] not in orientations:
            continue
            
        filtered.append(workflow)
    
    return filtered

def process_single_workflow_for_batch(image_file, workflow_info, common_params):
    """
    Procesa la imagen con un workflow específico para el batch
    """
    try:
        # Reutilizar la lógica existente de process_image pero adaptada
        start_time = time.time()
        
        # Guardar imagen temporal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_{timestamp}_{workflow_info['id'].replace('/', '_')}.{image_file.filename.split('.')[-1]}"
        
        input_path = os.path.join(COMFYUI_INPUT_DIR, filename)
        image_file.seek(0)  # Reset file pointer
        image_file.save(input_path)
        
        # Cargar y actualizar workflow
        workflow = load_workflow(workflow_info["id"])
        workflow = update_workflow(
            workflow, 
            filename, 
            common_params["frame_color"], 
            common_params["style"], 
            common_params.get("style_node"),
            workflow_info["id"]  # output_subfolder
        )
        
        # Enviar a ComfyUI
        prompt_id = submit_workflow_to_comfyui(workflow)
        if not prompt_id:
            raise Exception("Error enviando workflow a ComfyUI")
        
        # Esperar resultados
        outputs = wait_for_completion(prompt_id)
        if not outputs:
            raise Exception("Error esperando resultados de ComfyUI")
        
        # Extraer imágenes generadas
        generated_images = extract_generated_images(outputs)
        
        # Crear directorio de salida para este workflow
        workflow_output_dir = create_output_directory(f"batch_{workflow_info['id'].replace('/', '_')}")
        
        # Copiar imágenes generadas
        saved_images = []
        for img_info in generated_images:
            source_path = find_image_file(img_info['filename'], img_info['subfolder'])
            if source_path:
                dest_path = os.path.join(workflow_output_dir, f"result_{img_info['filename']}")
                shutil.copy2(source_path, dest_path)
                saved_images.append({
                    'filename': f"result_{img_info['filename']}",
                    'url': f"/get-image/batch_{workflow_info['id'].replace('/', '_')}/result_{img_info['filename']}",
                    'original_filename': img_info['filename']
                })
        
        # Guardar imagen original en el directorio del workflow
        original_dest = os.path.join(workflow_output_dir, 'original.png')
        image_file.seek(0)
        image = Image.open(image_file.stream)
        image.save(original_dest, format='PNG')
        
        processing_time = time.time() - start_time
        
        return {
            "workflow_id": workflow_info["id"],
            "workflow_info": workflow_info,
            "success": True,
            "generated_images": saved_images,
            "original_image": {
                "filename": "original.png",
                "url": f"/get-image/batch_{workflow_info['id'].replace('/', '_')}/original.png"
            },
            "processing_time": round(processing_time, 2)
        }
        
    except Exception as e:
        log_error(f"Error procesando workflow {workflow_info['id']}: {str(e)}")
        return {
            "workflow_id": workflow_info["id"],
            "workflow_info": workflow_info,
            "success": False,
            "error": str(e),
            "processing_time": 0
        }

def process_all_workflows_simultáneamente_with_tracking(image_data, workflows, common_params, batch_id):
    """
    Procesa todos los workflows simultáneamente con tracking en tiempo real
    image_data: BytesIO object con el contenido de la imagen
    """
    import concurrent.futures
    
    results = []
    submitted_prompts = {}  # prompt_id -> workflow_info
    
    # Actualizar status: enviando workflows
    with BATCH_LOCK:
        if batch_id in ACTIVE_BATCHES:
            ACTIVE_BATCHES[batch_id]["status"] = "submitting"
            ACTIVE_BATCHES[batch_id]["current_operation"] = "Enviando workflows a ComfyUI..."
    
    log_info(f"🚀 Enviando {len(workflows)} workflows simultáneamente a ComfyUI...")
    
    # Pre-cargar la imagen una vez para todos los workflows
    log_info("📷 Pre-cargando imagen para todos los workflows...")
    try:
        image_data.seek(0)
        master_image = Image.open(image_data)
        
        # Convertir a RGB si es necesario
        if master_image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', master_image.size, (255, 255, 255))
            if master_image.mode == 'P':
                master_image = master_image.convert('RGBA')
            background.paste(master_image, mask=master_image.split()[-1] if master_image.mode in ('RGBA', 'LA') else None)
            master_image = background
        elif master_image.mode != 'RGB':
            master_image = master_image.convert('RGB')
            
        # Redimensionar si es muy grande
        max_size = 2048
        if master_image.width > max_size or master_image.height > max_size:
            master_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            log_info(f"📏 Imagen redimensionada a: {master_image.width}x{master_image.height}")
            
        log_success("✅ Imagen pre-cargada correctamente")
    except Exception as e:
        log_error(f"❌ Error pre-cargando imagen: {str(e)}")
        with BATCH_LOCK:
            if batch_id in ACTIVE_BATCHES:
                ACTIVE_BATCHES[batch_id]["status"] = "error"
                ACTIVE_BATCHES[batch_id]["error"] = f"Error pre-cargando imagen: {str(e)}"
        return []

    # Fase 1: Preparar y enviar todos los workflows a ComfyUI
    for i, workflow_info in enumerate(workflows):
        try:
            # Actualizar progreso
            with BATCH_LOCK:
                if batch_id in ACTIVE_BATCHES:
                    ACTIVE_BATCHES[batch_id]["current_operation"] = f"Enviando {i+1}/{len(workflows)}: {workflow_info['id']}"
            
            log_info(f"📤 Preparando {i+1}/{len(workflows)}: {workflow_info['id']}")
            
            # Guardar imagen temporal única para cada workflow
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"batch_{batch_id}_{i:03d}_{workflow_info['id'].replace('/', '_')}.png"
            
            input_path = os.path.join(COMFYUI_INPUT_DIR, unique_filename)
            
            # Guardar copia de la imagen pre-cargada
            master_image.save(input_path, format='PNG', optimize=False)
            
            # Cargar y actualizar workflow
            workflow = load_workflow(workflow_info["id"])
            workflow = update_workflow(
                workflow, 
                unique_filename, 
                common_params["frame_color"], 
                common_params["style"], 
                common_params.get("style_node"),
                f"batch_{workflow_info['id'].replace('/', '_')}"  # output_subfolder
            )
            
            # Enviar a ComfyUI (sin esperar)
            prompt_id = submit_workflow_to_comfyui(workflow)
            if prompt_id:
                submitted_prompts[prompt_id] = {
                    "workflow_info": workflow_info,
                    "unique_filename": unique_filename,
                    "submit_time": time.time(),
                    "index": i
                }
                log_success(f"✅ Enviado {i+1}/{len(workflows)}: {workflow_info['id']} (prompt_id: {prompt_id})")
            else:
                log_error(f"❌ Error enviando {i+1}/{len(workflows)}: {workflow_info['id']}")
                result = {
                    "workflow_id": workflow_info["id"],
                    "workflow_info": workflow_info,
                    "success": False,
                    "error": "Error enviando workflow a ComfyUI",
                    "processing_time": 0
                }
                results.append(result)
                
                # Actualizar tracking inmediatamente
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        batch_info = ACTIVE_BATCHES[batch_id]
                        batch_info["completed_workflows"] += 1
                        batch_info["failed"] += 1
                        batch_info["results"].append(result)
                
        except Exception as e:
            log_error(f"❌ Error preparando workflow {workflow_info['id']}: {str(e)}")
            result = {
                "workflow_id": workflow_info["id"],
                "workflow_info": workflow_info,
                "success": False,
                "error": f"Error preparando workflow: {str(e)}",
                "processing_time": 0
            }
            results.append(result)
            
            # Actualizar tracking inmediatamente
            with BATCH_LOCK:
                if batch_id in ACTIVE_BATCHES:
                    batch_info = ACTIVE_BATCHES[batch_id]
                    batch_info["completed_workflows"] += 1
                    batch_info["failed"] += 1
                    batch_info["results"].append(result)
    
    if not submitted_prompts:
        log_error("❌ No se pudo enviar ningún workflow a ComfyUI")
        with BATCH_LOCK:
            if batch_id in ACTIVE_BATCHES:
                ACTIVE_BATCHES[batch_id]["status"] = "error"
                ACTIVE_BATCHES[batch_id]["error"] = "No se pudo enviar ningún workflow"
        return results
    
    # Actualizar status: procesando
    with BATCH_LOCK:
        if batch_id in ACTIVE_BATCHES:
            ACTIVE_BATCHES[batch_id]["status"] = "processing"
            ACTIVE_BATCHES[batch_id]["current_operation"] = f"Procesando {len(submitted_prompts)} workflows..."
    
    log_info(f"🏁 {len(submitted_prompts)} workflows enviados a ComfyUI. Esperando resultados...")
    
    # Fase 2: Esperar y recoger resultados simultáneamente CON TRACKING
    def wait_for_single_workflow_with_tracking(prompt_id, workflow_data, master_image):
        """Espera el resultado de un workflow específico CON TRACKING"""
        try:
            start_time = workflow_data["submit_time"]
            workflow_info = workflow_data["workflow_info"]
            index = workflow_data["index"]
            
            log_info(f"⏳ Esperando resultado {index+1}: {workflow_info['id']} (prompt_id: {prompt_id})")
            
            # Actualizar status individual
            with BATCH_LOCK:
                if batch_id in ACTIVE_BATCHES:
                    ACTIVE_BATCHES[batch_id]["current_operation"] = f"Procesando: {workflow_info['id']}"
            
            # Esperar completion de este workflow específico
            outputs = wait_for_completion(prompt_id, timeout=600)  # 10 minutos timeout
            
            # Extraer imágenes generadas
            generated_images = extract_generated_images(outputs)
            
            # Crear directorio de salida para este workflow
            workflow_output_dir = create_output_directory(f"batch_{workflow_info['id'].replace('/', '_')}")
            
            # Copiar imágenes generadas
            saved_images = []
            for img_info in generated_images:
                source_path = find_image_file(img_info['filename'], img_info['subfolder'])
                if source_path:
                    dest_path = os.path.join(workflow_output_dir, f"result_{img_info['filename']}")
                    shutil.copy2(source_path, dest_path)
                    saved_images.append({
                        'filename': f"result_{img_info['filename']}",
                        'url': f"/get-image/batch_{workflow_info['id'].replace('/', '_')}/result_{img_info['filename']}",
                        'original_filename': img_info['filename']
                    })
            
            # Guardar imagen original en el directorio del workflow
            original_dest = os.path.join(workflow_output_dir, 'original.png')
            master_image.save(original_dest, format='PNG')
            
            processing_time = time.time() - start_time
            
            result = {
                "workflow_id": workflow_info["id"],
                "workflow_info": workflow_info,
                "success": True,
                "generated_images": saved_images,
                "original_image": {
                    "filename": "original.png",
                    "url": f"/get-image/batch_{workflow_info['id'].replace('/', '_')}/original.png"
                },
                "processing_time": round(processing_time, 2),
                "prompt_id": prompt_id,
                "completion_time": datetime.now().isoformat()
            }
            
            log_success(f"✅ Completado {index+1}: {workflow_info['id']} en {processing_time:.1f}s ({len(saved_images)} imágenes)")
            
            # *** ACTUALIZAR TRACKING INMEDIATAMENTE CUANDO TERMINA ***
            with BATCH_LOCK:
                if batch_id in ACTIVE_BATCHES:
                    batch_info = ACTIVE_BATCHES[batch_id]
                    batch_info["completed_workflows"] += 1
                    batch_info["successful"] += 1
                    batch_info["results"].append(result)
                    
                    # Calcular estimación de tiempo restante
                    if batch_info["completed_workflows"] > 0:
                        elapsed_time = time.time() - batch_info["start_time"]
                        avg_time_per_workflow = elapsed_time / batch_info["completed_workflows"]
                        remaining_workflows = batch_info["total_workflows"] - batch_info["completed_workflows"]
                        estimated_remaining = avg_time_per_workflow * remaining_workflows
                        batch_info["estimated_completion"] = time.time() + estimated_remaining
                    
                    batch_info["current_operation"] = f"Completado: {workflow_info['id']} ({batch_info['completed_workflows']}/{batch_info['total_workflows']})"
            
            return result
            
        except Exception as e:
            processing_time = time.time() - workflow_data["submit_time"]
            log_error(f"❌ Error procesando {workflow_info['id']}: {str(e)}")
            
            result = {
                "workflow_id": workflow_info["id"],
                "workflow_info": workflow_info,
                "success": False,
                "error": str(e),
                "processing_time": round(processing_time, 2),
                "prompt_id": prompt_id,
                "completion_time": datetime.now().isoformat()
            }
            
            # *** ACTUALIZAR TRACKING INMEDIATAMENTE EN CASO DE ERROR ***
            with BATCH_LOCK:
                if batch_id in ACTIVE_BATCHES:
                    batch_info = ACTIVE_BATCHES[batch_id]
                    batch_info["completed_workflows"] += 1
                    batch_info["failed"] += 1
                    batch_info["results"].append(result)
                    batch_info["current_operation"] = f"Error en: {workflow_info['id']} ({batch_info['completed_workflows']}/{batch_info['total_workflows']})"
            
            return result
    
    # Usar ThreadPoolExecutor para esperar todos los workflows en paralelo
    max_workers = min(len(submitted_prompts), 10)  # Máximo 10 hilos concurrentes
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Enviar todas las tareas de espera (crear copia de imagen para cada hilo)
        future_to_prompt = {
            executor.submit(wait_for_single_workflow_with_tracking, prompt_id, workflow_data, master_image.copy()): prompt_id 
            for prompt_id, workflow_data in submitted_prompts.items()
        }
        
        # Recoger resultados conforme van completándose
        for future in concurrent.futures.as_completed(future_to_prompt):
            prompt_id = future_to_prompt[future]
            try:
                result = future.result()
                results.append(result)
                completed = len(results)
                total = len(submitted_prompts)
                log_info(f"📈 Progreso: {completed}/{total} workflows completados")
            except Exception as e:
                workflow_data = submitted_prompts[prompt_id]
                workflow_info = workflow_data["workflow_info"]
                log_error(f"❌ Error obteniendo resultado de {workflow_info['id']}: {str(e)}")
                error_result = {
                    "workflow_id": workflow_info["id"],
                    "workflow_info": workflow_info,
                    "success": False,
                    "error": f"Error obteniendo resultado: {str(e)}",
                    "processing_time": 0,
                    "prompt_id": prompt_id
                }
                results.append(error_result)
                
                # Actualizar tracking
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        batch_info = ACTIVE_BATCHES[batch_id]
                        batch_info["completed_workflows"] += 1
                        batch_info["failed"] += 1
                        batch_info["results"].append(error_result)
    
    # Ordenar resultados por el índice original para mantener orden
    results.sort(key=lambda x: next(
        (data["index"] for prompt_id, data in submitted_prompts.items() 
         if x.get("prompt_id") == prompt_id), 999
    ))
    
    return results

# ==================== INICIO DEL SERVIDOR ====================

if __name__ == '__main__':
    log_info("🚀 Iniciando ComfyUI API REST v2.0.0...")
    log_info(f"📁 Directorio de workflows: {WORKFLOWS_DIR}")
    log_info(f"📁 Directorio de input: {COMFYUI_INPUT_DIR}")
    log_info(f"📁 Directorio de output: {COMFYUI_OUTPUT_DIR}")
    log_info(f"🌐 ComfyUI URL: {COMFYUI_URL}")
    
    # Verificar conexión con ComfyUI
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        if response.status_code == 200:
            log_success("✅ Conexión con ComfyUI establecida")
        else:
            log_warning("⚠️ ComfyUI no responde correctamente")
    except Exception as e:
        log_warning(f"⚠️ No se pudo conectar con ComfyUI: {str(e)}")
    
    # Contar workflows disponibles
    try:
        workflows = get_available_workflows()
        log_info(f"📊 {len(workflows)} workflows encontrados")
    except Exception as e:
        log_warning(f"⚠️ Error contando workflows: {str(e)}")
    
    # Iniciar servidor
    log_info("🌟 Servidor iniciado en http://localhost:5000")
    log_info("📱 Cliente web disponible en: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
