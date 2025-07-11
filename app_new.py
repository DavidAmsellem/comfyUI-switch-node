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

# Importar sistema de persistencia de sesión
from job_persistence import session_manager

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
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_ROOT, 'output')  # ComfyUI output (solo para leer)
WORKFLOWS_DIR = os.path.join(BASE_DIR, 'workflows')
TEMP_UPLOADS_DIR = os.path.join(BASE_DIR, 'temp_uploads')

# 🎯 NUESTRO DIRECTORIO DE SALIDA PERSONALIZADO (independiente de ComfyUI)
OUR_OUTPUT_DIR = os.path.join(os.path.dirname(COMFYUI_ROOT), 'output')  # C:\Users\david_qskhc9c\Documents\ComfyUI_windows_portable\output

# Crear directorios necesarios
for directory in [COMFYUI_INPUT_DIR, COMFYUI_OUTPUT_DIR, TEMP_UPLOADS_DIR, OUR_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configuración del workflow (actualizar según tu nuevo workflow)
WORKFLOW_CONFIG = {
    'load_image_node_id': '699',  # ID del nodo LoadImage para el cuadro
    'save_image_node_id': '704',  # ID del nodo SaveImage principal
    'frame_node_id': '692',       # ID del nodo DynamicFrameNode
    'allowed_extensions': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
     'frame_colors': ['none', 'black', 'white', 'brown', 'gold'],  # Incluir 'none' para sin marco
    # Parámetros por defecto para DynamicFrameNode (para asegurar todos los inputs requeridos)
    'frame_node_defaults': {
        'frame_width': 20,         # Ancho del marco (10-200)
        'shadow_enabled': True,    # Habilitar sombra del marco
        'shadow_opacity': 0.5,     # Opacidad de la sombra (0.1-0.8) - más intensa para efecto dramático
        'wall_color': 220,         # Color de pared (180-250)
        'shadow_size': 25,         # Tamaño de la sombra (5-50) - más grande para efecto picudo
        'shadow_color': 0,         # Color de sombra (0=negro, 255=blanco) - NEGRO INTENSO
        'shadow_angle': 270,       # Ángulo de la sombra en grados (270° = DIRECTAMENTE hacia abajo, efecto picudo)
        'shadow_blur': 2,          # Difuminado de la sombra (1-10) - menos difuso para bordes más definidos
        'shadow_offset_x': 0,      # Sin desplazamiento horizontal - sombra centrada
        'shadow_offset_y': 15      # Desplazamiento vertical mayor (píxeles) - sombra más pronunciada hacia abajo
    }
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
    Crea directorio de salida para las imágenes procesadas en NUESTRO directorio personalizado
    Retorna: ruta del directorio creado
    """
    output_dir = os.path.join(OUR_OUTPUT_DIR, base_name)
    os.makedirs(output_dir, exist_ok=True)
    log_info(f"📁 Directorio de salida personalizado creado: {output_dir}")
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
    
    # Actualizar nodo DynamicFrameNode (color del marco y otros parámetros)
    frame_node_id = WORKFLOW_CONFIG['frame_node_id']
    if frame_node_id in workflow_copy:
        frame_node = workflow_copy[frame_node_id]
        
        # Asegurar que el nodo tiene la estructura inputs
        if 'inputs' not in frame_node:
            frame_node['inputs'] = {}
        
        # Configuración especial para "none" (sin marco pero CON sombra)
        if frame_color == 'none':
            frame_defaults = WORKFLOW_CONFIG['frame_node_defaults']
            frame_node['inputs']['preset'] = 'black'  # Usar preset black como base
            frame_node['inputs']['wall_color'] = frame_defaults['wall_color']
            frame_node['inputs']['frame_width'] = 0  # Sin marco (ancho 0)
            
            # MANTENER LA SOMBRA HABILITADA para el efecto sin marco
            frame_node['inputs']['shadow_enabled'] = frame_defaults['shadow_enabled']
            frame_node['inputs']['shadow_size'] = frame_defaults['shadow_size']
            frame_node['inputs']['shadow_opacity'] = frame_defaults['shadow_opacity']
            frame_node['inputs']['shadow_color'] = frame_defaults['shadow_color']  # Negro
            frame_node['inputs']['shadow_angle'] = frame_defaults['shadow_angle']  # 270° hacia abajo
            frame_node['inputs']['shadow_blur'] = frame_defaults['shadow_blur']
            frame_node['inputs']['shadow_offset_x'] = frame_defaults['shadow_offset_x']
            frame_node['inputs']['shadow_offset_y'] = frame_defaults['shadow_offset_y']
            
            log_success(f"🚫 DynamicFrameNode ({frame_node_id}) configurado SIN MARCO pero CON SOMBRA NEGRA")
        else:
            # Configuración normal con marco y sombra personalizada (negra y picuda)
            frame_defaults = WORKFLOW_CONFIG['frame_node_defaults']
            frame_node['inputs']['preset'] = frame_color if frame_color in WORKFLOW_CONFIG['frame_colors'] else 'black'
            frame_node['inputs']['wall_color'] = frame_defaults['wall_color']
            frame_node['inputs']['frame_width'] = frame_defaults['frame_width']
            
            # Configuración de sombra personalizada: negra y picuda hacia abajo
            frame_node['inputs']['shadow_enabled'] = frame_defaults['shadow_enabled']
            frame_node['inputs']['shadow_size'] = frame_defaults['shadow_size']
            frame_node['inputs']['shadow_opacity'] = frame_defaults['shadow_opacity']
            frame_node['inputs']['shadow_color'] = frame_defaults['shadow_color']  # 0 = negro
            frame_node['inputs']['shadow_angle'] = frame_defaults['shadow_angle']  # 270° = picuda directamente hacia abajo
            frame_node['inputs']['shadow_blur'] = frame_defaults['shadow_blur']    # Difuminado controlado
            frame_node['inputs']['shadow_offset_x'] = frame_defaults['shadow_offset_x']  # Desplazamiento horizontal
            frame_node['inputs']['shadow_offset_y'] = frame_defaults['shadow_offset_y']  # Desplazamiento hacia abajo
            
            log_success(f"🖼️ DynamicFrameNode ({frame_node_id}) configurado: marco={frame_color}, sombra=NEGRA PICUDA directamente hacia abajo (ángulo={frame_defaults['shadow_angle']}°)")
    else:
        log_warning(f"Nodo DynamicFrameNode ({frame_node_id}) no encontrado en el workflow")
    
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
    
    # Actualizar nodos SaveImage (subfolder si se especifica Y configurar prefijo descriptivo)
    save_node_id = WORKFLOW_CONFIG['save_image_node_id']
    
    # NO actualizar el prefijo del nodo principal (704) para mantener "ComfyUI" 
    # Esto permite identificar correctamente la imagen de composición final
    # if save_node_id in workflow_copy:
    #     save_node = workflow_copy[save_node_id]
    #     if 'inputs' in save_node:
    #         # Crear prefijo basado en la imagen y frame_color
    #         base_image_name = image_filename.split('.')[0] if '.' in image_filename else image_filename
    #         descriptive_prefix = f"{base_image_name}_{frame_color}"
    #         save_node['inputs']['filename_prefix'] = descriptive_prefix
    #         log_success(f"SaveImage {save_node_id}: prefijo actualizado a '{descriptive_prefix}'")
    
    log_info(f"💾 Manteniendo prefijo original 'ComfyUI' en nodo {save_node_id} para identificación correcta")
    
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

def extract_generated_images(outputs, original_image_filename=None, include_upscale=True):
    """
    Extrae las imágenes GENERADAS de los outputs de ComfyUI para mostrar en el frontend:
    1. Upscale (imagen escalada del nodo 696) - OPCIONAL según include_upscale
    2. Composición (imagen final combinada del nodo 704) - SIEMPRE incluida
    
    NOTA: La imagen original NO se incluye en el resultado para evitar mostrarla en el frontend.
    
    Args:
        outputs: Outputs de ComfyUI
        original_image_filename: Nombre del archivo original para mejor clasificación
        include_upscale: Si True incluye imagen upscale, si False solo composición
    
    Retorna: lista de imágenes generadas filtradas (composición + upscale opcional)
    """
    # Contenedores para los 3 tipos de imágenes
    original_image = None
    upscale_image = None
    composition_image = None
    
    save_node_id = WORKFLOW_CONFIG['save_image_node_id']
    
    def classify_image_type(filename):
        """Clasifica el tipo de imagen basado en el nombre del archivo"""
        filename_lower = filename.lower()
        
        # Excluir archivos temporales
        temporal_patterns = ['tmp_', 'temp_', '_temp']
        for pattern in temporal_patterns:
            if pattern in filename_lower:
                return None
        
        # Clasificar tipos específicos CORREGIDOS:
        # 1. COMPOSICIÓN FINAL: Imágenes que empiezan con "comfyui" (nodo 704)
        if filename_lower.startswith('comfyui') and any(char.isdigit() for char in filename_lower):
            return 'composition'  # ✅ Resultado final del workflow (nodo 704)
        # 2. UPSCALE ORIGINAL: Imágenes con "original-upscale" (nodo 696)
        elif 'original-upscale' in filename_lower:
            return 'upscale'  # ✅ Solo upscale de la imagen original (nodo 696)
        # 3. UPSCALE GENÉRICO: Otras imágenes con "upscale" pero sin "original"
        elif 'upscale' in filename_lower and 'original' not in filename_lower:
            return 'upscale'  # Solo upscale
        # 4. ORIGINAL: Imágenes con "original" pero sin "upscale"
        elif 'original' in filename_lower and 'upscale' not in filename_lower:
            return 'original'  # Solo original
        else:
            # Usar keywords de habitaciones como fallback para original
            room_keywords = ['bathroom', 'bedroom', 'office', 'salon', 'kitchen', 'living']
            if any(keyword in filename_lower for keyword in room_keywords):
                return 'original'
        
        return None
    
    def add_image_if_better(current_image, new_image_info, image_type):
        """Añade la imagen si es mejor que la actual o si no hay una actual"""
        if current_image is None:
            log_info(f"✅ Primera imagen {image_type}: {new_image_info['filename']} (nodo {new_image_info['node_id']})")
            return new_image_info
        
        # 🎯 PRIORIDAD MÁXIMA: Nodo 704 siempre gana para composición
        if image_type == 'composition':
            if new_image_info['node_id'] == '704' and current_image['node_id'] != '704':
                log_info(f"✅ Mejor imagen {image_type} (nodo 704 - composición final): {new_image_info['filename']}")
                return new_image_info
            elif current_image['node_id'] == '704' and new_image_info['node_id'] != '704':
                log_info(f"⚠️ Manteniendo imagen {image_type} (nodo 704 prioritario): {current_image['filename']}")
                return current_image
        
        # Preferir imágenes que contengan el nombre original
        if original_image_filename:
            original_base = original_image_filename.split('.')[0].lower() if '.' in original_image_filename else original_image_filename.lower()
            current_has_original = original_base in current_image['filename'].lower()
            new_has_original = original_base in new_image_info['filename'].lower()
            
            if new_has_original and not current_has_original:
                log_info(f"✅ Mejor imagen {image_type} (contiene nombre original): {new_image_info['filename']}")
                return new_image_info
            elif current_has_original and not new_has_original:
                log_info(f"⚠️ Manteniendo imagen {image_type} actual (contiene nombre original): {current_image['filename']}")
                return current_image
        
        # Si ambas son similares, preferir la más reciente (por nombre)
        if new_image_info['filename'] > current_image['filename']:
            log_info(f"✅ Mejor imagen {image_type} (más reciente): {new_image_info['filename']}")
            return new_image_info
        
        log_info(f"⚠️ Manteniendo imagen {image_type} actual: {current_image['filename']}")
        return current_image
    
    # Buscar en todos los nodos SaveImage (704 primero para prioridad de composición)
    all_save_nodes = ['704', save_node_id, '696']  # 704 primero (composición final), luego los demás
    
    for node_id in all_save_nodes:
        if node_id in outputs and isinstance(outputs[node_id], dict) and 'images' in outputs[node_id]:
            for image_info in outputs[node_id]['images']:
                if 'filename' not in image_info:
                    continue
                
                filename = image_info['filename']
                image_type = classify_image_type(filename)
                
                log_info(f"🔍 Analizando imagen: {filename} (nodo {node_id}) -> clasificada como: {image_type}")
                
                if image_type is None:
                    log_info(f"❌ Archivo excluido (no clasificado): {filename}")
                    continue
                
                # Crear info de imagen
                img_info = {
                    'filename': filename,
                    'subfolder': image_info.get('subfolder', ''),
                    'type': image_info.get('type', 'output'),
                    'node_id': node_id,
                    'image_type': image_type
                }
                
                # 🎯 CLASIFICACIÓN ADICIONAL POR NODO (más confiable que el nombre)
                if node_id == '704':
                    img_info['image_type'] = 'composition'  # Nodo 704 siempre es composición final
                    log_info(f"🎯 FORZADO: Imagen del nodo 704 clasificada como COMPOSITION: {filename}")
                elif node_id == '696':
                    img_info['image_type'] = 'upscale'  # Nodo 696 siempre es upscale original
                    log_info(f"📈 FORZADO: Imagen del nodo 696 clasificada como UPSCALE: {filename}")
                
                # Usar la clasificación forzada por nodo
                final_image_type = img_info['image_type']
                
                # Asignar a la categoría correspondiente usando clasificación forzada por nodo
                if final_image_type == 'original':
                    original_image = add_image_if_better(original_image, img_info, 'original')
                elif final_image_type == 'upscale':
                    upscale_image = add_image_if_better(upscale_image, img_info, 'upscale')
                elif final_image_type == 'composition':
                    composition_image = add_image_if_better(composition_image, img_info, 'composition')
    
    # Buscar en otros nodos si no se encontraron todas las imágenes
    if not all([original_image, upscale_image, composition_image]):
        log_info("🔍 Buscando imágenes faltantes en otros nodos...")
        
        for node_id, node_data in outputs.items():
            if node_id in all_save_nodes:
                continue  # Ya procesado
            
            if isinstance(node_data, dict) and 'images' in node_data:
                for image_info in node_data['images']:
                    if 'filename' not in image_info:
                        continue
                    
                    filename = image_info['filename']
                    image_type = classify_image_type(filename)
                    
                    if image_type is None:
                        continue
                    
                    img_info = {
                        'filename': filename,
                        'subfolder': image_info.get('subfolder', ''),
                        'type': image_info.get('type', 'output'),
                        'node_id': node_id,
                        'image_type': image_type
                    }
                    
                    # Solo asignar si no tenemos una imagen de ese tipo
                    if image_type == 'original' and original_image is None:
                        original_image = img_info
                        log_info(f"✅ Imagen original encontrada en nodo {node_id}: {filename}")
                    elif image_type == 'upscale' and upscale_image is None:
                        upscale_image = img_info
                        log_info(f"✅ Imagen upscale encontrada en nodo {node_id}: {filename}")
                    elif image_type == 'composition' and composition_image is None:
                        composition_image = img_info
                        log_info(f"✅ Imagen composición encontrada en nodo {node_id}: {filename}")
    
    # Ensamblar resultado final - SOLO IMÁGENES GENERADAS (sin la original)
    final_images = []
    
    # 🎯 COMPOSICIÓN: Siempre incluir la imagen de composición (nodo 704)
    if composition_image:
        final_images.append(composition_image)
    
    # 📈 UPSCALE: Incluir solo si el usuario lo solicita
    if include_upscale and upscale_image:
        final_images.append(upscale_image)
    
    # Calcular imágenes esperadas según configuración
    expected_generated = 1 + (1 if include_upscale else 0)  # Composición + upscale opcional
    if len(final_images) != expected_generated:
        log_warning(f"⚠️ Se esperaban {expected_generated} imágenes generadas, pero se encontraron {len(final_images)}")
        log_warning(f"   Upscale: {'✅' if upscale_image else '❌'} {'(incluido)' if include_upscale else '(excluido por usuario)'}")
        log_warning(f"   Composición: {'✅' if composition_image else '❌'}")
        if original_image:
            log_info(f"   Original encontrada pero excluida del frontend: {original_image['filename']}")
    
    log_success(f"✅ Total de imágenes generadas para frontend: {len(final_images)}/{expected_generated}")
    log_info(f"📋 RESUMEN DE IMÁGENES GENERADAS PARA FRONTEND:")
    for img in final_images:
        log_info(f"   📷 {img['image_type'].upper()}: {img['filename']} (nodo {img['node_id']})")
    
    # Log especial para indicar estado del upscale
    if upscale_image:
        if include_upscale:
            log_info(f"📈 IMAGEN UPSCALE INCLUIDA EN FRONTEND Y GUARDADO: {upscale_image['filename']} (nodo {upscale_image['node_id']})")
        else:
            log_info(f"🚫 IMAGEN UPSCALE EXCLUIDA DEL FRONTEND Y GUARDADO: {upscale_image['filename']} (nodo {upscale_image['node_id']})")
    else:
        log_warning(f"⚠️ No se encontró imagen upscale en los outputs de ComfyUI")
    
    # Log especial para indicar que la original se excluye
    if original_image:
        log_info(f"🚫 IMAGEN ORIGINAL EXCLUIDA DEL FRONTEND: {original_image['filename']} (nodo {original_image['node_id']})")
    
    # Log especial para composición final
    if composition_image:
        log_success(f"🎯 IMAGEN DE COMPOSICIÓN FINAL (nodo 704): {composition_image['filename']}")
    else:
        log_error(f"❌ NO SE ENCONTRÓ IMAGEN DE COMPOSICIÓN FINAL (nodo 704)")
    
    return final_images

def find_image_file(filename, subfolder=''):
    """
    Busca un archivo de imagen en el directorio de output DE COMFYUI (para leer las imágenes generadas)
    NOTA: ComfyUI siempre guardará todas las imágenes aquí, nosotros solo leemos de aquí
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
            log_success(f"📖 Imagen encontrada en ComfyUI output: {path}")
            return path
    
    log_error(f"❌ Imagen no encontrada en ComfyUI output: {filename}")
    return None

def save_images_to_our_output(output_dir, original_file, generated_images, original_filename, include_upscale, job_id, workflow_name=None, style_id=None):
    """
    Guarda las imágenes en nuestro directorio personalizado de manera organizada
    
    Args:
        output_dir: Directorio de salida personalizado para esta imagen
        original_file: Archivo original subido
        generated_images: Lista de imágenes generadas (ya filtradas)
        original_filename: Nombre del archivo original
        include_upscale: Si incluir upscale en el guardado
        job_id: ID del trabajo de sesión
        workflow_name: Nombre del workflow utilizado (para nombres descriptivos)
        style_id: ID del estilo aplicado (para nombres descriptivos)
    
    Returns:
        (original_info, saved_images) - Información de imagen original y lista de generadas guardadas
    """
    log_info(f"💾 Guardando en directorio personalizado: {output_dir}")
    
    saved_images = []
    
    # 1. 📷 GUARDAR IMAGEN ORIGINAL
    log_info("📷 Guardando imagen original...")
    original_filename_clean = secure_filename(original_filename.rsplit('.', 1)[0] if '.' in original_filename else 'image')
    original_ext = original_filename.rsplit('.', 1)[1] if '.' in original_filename else 'png'
    original_dest_filename = f"original.{original_ext}"
    original_dest_path = os.path.join(output_dir, original_dest_filename)
    
    try:
        # Guardar imagen original desde el archivo subido
        original_file.stream.seek(0)  # Reset stream
        image = Image.open(original_file.stream)
        
        # Convertir a RGB si es necesario
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        image.save(original_dest_path, format='PNG', optimize=False)
        
        # Guardar también en sesión
        with open(original_dest_path, 'rb') as img_file:
            session_original_url = session_manager.save_job_image(job_id, img_file.read(), original_dest_filename)
        
        original_info = {
            'filename': original_dest_filename,
            'url': f"/get-image/{os.path.basename(output_dir)}/{original_dest_filename}",
            'session_url': session_original_url,
            'image_type': 'original',
            'status': 'saved'
        }
        
        log_success(f"✅ Imagen original guardada: {original_dest_path}")
        
    except Exception as e:
        log_error(f"❌ Error guardando imagen original: {str(e)}")
        original_info = {
            'filename': original_dest_filename,
            'error': str(e),
            'status': 'error'
        }
    
    # 2. 🎯 GUARDAR IMÁGENES GENERADAS (ya filtradas según include_upscale)
    log_info(f"🎯 Guardando {len(generated_images)} imágenes generadas...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 🔍 VERIFICAR ARCHIVOS EXISTENTES EN EL DIRECTORIO
    existing_files = []
    if os.path.exists(output_dir):
        existing_files = [f.lower() for f in os.listdir(output_dir)]
    
    # Verificar si ya existe una imagen upscale
    existing_upscale = any('upscale_' in f for f in existing_files)
    if existing_upscale:
        log_info(f"📈 Ya existe una imagen upscale en {output_dir}, se omitirán nuevas imágenes upscale")
    
    for i, img_info in enumerate(generated_images):
        try:
            # Verificar tipo de imagen
            img_type = img_info.get('image_type', 'generated')
            
            # 🚫 SALTAR UPSCALE SI YA EXISTE UNA
            if img_type == 'upscale' and existing_upscale:
                log_warning(f"⚠️ Imagen upscale saltada (ya existe una): {img_info['filename']}")
                # Buscar la imagen upscale existente para agregarla a la respuesta
                for existing_file in os.listdir(output_dir):
                    if 'upscale_' in existing_file.lower():
                        # Crear entrada para la imagen existente
                        with open(os.path.join(output_dir, existing_file), 'rb') as img_file:
                            session_url = session_manager.save_job_image(job_id, img_file.read(), existing_file)
                        
                        saved_images.append({
                            'filename': existing_file,
                            'url': f"/get-image/{os.path.basename(output_dir)}/{existing_file}",
                            'session_url': session_url,
                            'original_filename': img_info['filename'],
                            'node_id': img_info.get('node_id'),
                            'image_type': img_type,
                            'status': 'existing'  # Marcar como existente
                        })
                        log_info(f"📈 Usando imagen upscale existente: {existing_file}")
                        break
                continue
            
            # Buscar archivo fuente en ComfyUI output
            source_path = find_image_file(img_info['filename'], img_info['subfolder'])
            if not source_path:
                log_error(f"❌ No se pudo encontrar: {img_info['filename']}")
                continue
            
            # Crear nombre descriptivo
            original_ext = img_info['filename'].rsplit('.', 1)[1] if '.' in img_info['filename'] else 'png'
            
            # Preparar componentes para el nombre del archivo
            workflow_clean = workflow_name.replace('/', '_').replace('-', '_') if workflow_name else 'workflow'
            style_clean = style_id if style_id and style_id != 'default' else 'nostyle'
            photo_name = secure_filename(original_filename.rsplit('.', 1)[0] if '.' in original_filename else 'image')
            
            # Nombres descriptivos según tipo
            if img_type == 'composition':
                # Formato: workflow_estilo_nombreFoto_timestamp.ext
                dest_filename = f"{workflow_clean}_{style_clean}_{photo_name}_{timestamp}.{original_ext}"
                log_info(f"🎯 Nombre de composición generado: {dest_filename}")
                log_info(f"   📝 Componentes: workflow={workflow_clean}, estilo={style_clean}, foto={photo_name}, timestamp={timestamp}")
            elif img_type == 'upscale':
                # Formato: upscale_nombreFoto_timestamp.ext (más simple para upscale)
                dest_filename = f"upscale_{photo_name}_{timestamp}.{original_ext}"
                log_info(f"📈 Nombre de upscale generado: {dest_filename}")
                # Marcar que ahora tenemos upscale para futuras verificaciones
                existing_upscale = True
            else:
                # Formato genérico: generated_numeroSecuencia_timestamp.ext
                dest_filename = f"generated_{i+1}_{timestamp}.{original_ext}"
            
            dest_path = os.path.join(output_dir, dest_filename)
            
            # Verificar si ya existe este archivo específico
            if os.path.exists(dest_path):
                log_warning(f"⚠️ Archivo específico ya existe, saltando: {dest_filename}")
                continue
            
            # Copiar archivo
            shutil.copy2(source_path, dest_path)
            
            # Guardar también en sesión
            with open(dest_path, 'rb') as img_file:
                session_url = session_manager.save_job_image(job_id, img_file.read(), dest_filename)
            
            # Agregar a lista de guardadas
            saved_image_info = {
                'filename': dest_filename,
                'url': f"/get-image/{os.path.basename(output_dir)}/{dest_filename}",
                'session_url': session_url,
                'original_filename': img_info['filename'],
                'node_id': img_info.get('node_id'),
                'image_type': img_type,
                'status': 'saved'
            }
            
            saved_images.append(saved_image_info)
            log_success(f"✅ {img_type.upper()} guardada: {dest_path}")
            
        except Exception as e:
            log_error(f"❌ Error guardando imagen {img_info['filename']}: {str(e)}")
            # Agregar entrada de error
            saved_images.append({
                'filename': img_info['filename'],
                'error': str(e),
                'image_type': img_info.get('image_type', 'unknown'),
                'status': 'error'
            })
    
    # 3. 📊 RESUMEN FINAL
    successful_saves = len([img for img in saved_images if img.get('status') == 'saved'])
    log_success(f"✅ Guardado completado: {successful_saves}/{len(generated_images)} imágenes generadas + 1 original")
    log_info(f"📁 Directorio: {output_dir}")
    
    return original_info, saved_images

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
    job_id = None
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
        include_upscale = request.form.get('include_upscale', 'true').lower() == 'true'  # Incluir imagen upscale en resultados
        
        # ===== CREAR TRABAJO DE SESIÓN =====
        job_id = session_manager.create_job(
            job_type='individual',
            workflow=workflow_name,
            frame_color=frame_color,
            style=style_id,
            style_node=style_node_id,
            original_filename=original_filename,
            include_upscale=include_upscale  # Agregar parámetro de upscale
        )
        
        log_info(f"Trabajo de sesión creado: {job_id}")
        log_info(f"Parámetros: workflow={workflow_name}, frame_color={frame_color}, style={style_id}, style_node={style_node_id}, file={original_filename}, include_upscale={include_upscale}")
        
        # Actualizar estado del trabajo
        session_manager.update_job(job_id, 
            status='processing', 
            current_operation='Validando parámetros...'
        )
        
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
        
        session_manager.update_job(job_id, current_operation='Preparando archivos...')
        
        # 🚫 NO guardar imagen original aquí - se guardará después con las demás de manera organizada
        log_info("💾 Imagen original se guardará después junto con las generadas en nuestro directorio personalizado")
        
        # Guardar en input de ComfyUI (para que ComfyUI pueda procesarla)
        input_path, workflow_filename = save_uploaded_image(file, base_name)
        
        session_manager.update_job(job_id, current_operation='Verificando acceso a la imagen...')
        
        # Verificar que ComfyUI puede acceder al archivo (sin fallar si no puede)
        log_info("Verificando acceso a la imagen desde ComfyUI...")
        accessibility_check = verify_image_accessibility(workflow_filename)
        if not accessibility_check:
            log_warning("ComfyUI no puede verificar la imagen, pero continuando...")
            # Esperar un poco más para que el archivo se asiente
            time.sleep(1)
        
        session_manager.update_job(job_id, current_operation='Cargando workflow...')
        
        # Cargar y actualizar workflow
        log_info(f"Cargando workflow: {workflow_name}")
        workflow = load_workflow(workflow_name)
        updated_workflow = update_workflow(workflow, workflow_filename, frame_color, style_id, style_node_id, base_name)
        
        session_manager.update_job(job_id, current_operation='Enviando a ComfyUI...')
        
        # Enviar a ComfyUI
        log_info("Enviando a ComfyUI...")
        prompt_id = submit_workflow_to_comfyui(updated_workflow)
        
        session_manager.update_job(job_id, 
            current_operation='Esperando resultados de ComfyUI...',
            prompt_id=prompt_id
        )
        
        # Esperar resultados
        log_info("Esperando resultados...")
        outputs = wait_for_completion(prompt_id)
        
        session_manager.update_job(job_id, current_operation='Extrayendo imágenes generadas...')
        
        # Extraer imágenes generadas
        log_info("Extrayendo imágenes...")
        generated_images = extract_generated_images(outputs, original_filename, include_upscale)
        
        log_info(f"📊 Resumen de imágenes extraídas: {len(generated_images)} imágenes (include_upscale={include_upscale})")
        for i, img in enumerate(generated_images):
            log_info(f"   {i+1}. Tipo: {img.get('image_type', 'unknown')}, Archivo: {img['filename']}, Nodo: {img.get('node_id', 'N/A')}")
        
        session_manager.update_job(job_id, current_operation='Guardando imágenes en nuestro directorio personalizado...')
        
        # 🎯 USAR NUESTRO NUEVO SISTEMA DE GUARDADO ORGANIZADO
        log_info("💾 Guardando imágenes de manera organizada en nuestro directorio personalizado...")
        original_info, saved_images = save_images_to_our_output(
            output_dir=output_dir,
            original_file=file,
            generated_images=generated_images,
            original_filename=original_filename,
            include_upscale=include_upscale,
            job_id=job_id,
            workflow_name=workflow_name,
            style_id=style_id
        )
        
        # Agregar información adicional a las imágenes guardadas
        for img in saved_images:
            img['workflow'] = workflow_name
            img['style'] = style_id if style_id != 'default' else 'default'
        
        # 🎯 FILTRAR IMÁGENES PARA EL FRONTEND - SOLO COMPOSICIÓN FINAL
        log_info("🎯 Filtrando imágenes para el frontend - solo composición final...")
        frontend_images = [img for img in saved_images if img.get('image_type') == 'composition']
        
        if not frontend_images:
            # Fallback: si no hay composición, buscar cualquier imagen generada
            log_warning("⚠️ No se encontró imagen de composición, usando fallback...")
            frontend_images = saved_images[:1]  # Solo la primera
        
        log_info(f"📤 Para frontend: {len(frontend_images)} imagen(es) de {len(saved_images)} guardadas")
        log_info(f"💾 Guardadas en disco: {len(saved_images)} imágenes + 1 original")
        
        # Log detallado de lo que se está enviando al frontend vs lo que se guarda
        log_info("📋 RESUMEN DE FILTRADO PARA FRONTEND:")
        log_info(f"   💾 GUARDADAS EN DISCO ({len(saved_images)} imágenes):")
        for i, img in enumerate(saved_images):
            tipo = img.get('image_type', 'unknown')
            log_info(f"      {i+1}. {tipo.upper()}: {img['filename']}")
        
        log_info(f"   📤 ENVIADAS AL FRONTEND ({len(frontend_images)} imágenes):")
        for i, img in enumerate(frontend_images):
            tipo = img.get('image_type', 'unknown')
            log_info(f"      {i+1}. {tipo.upper()}: {img['filename']}")
        
        # Verificar si se están filtrando upscales
        upscale_count = len([img for img in saved_images if img.get('image_type') == 'upscale'])
        if upscale_count > 0:
            log_success(f"✅ FILTRADO CORRECTO: {upscale_count} imagen(es) upscale guardadas en disco pero excluidas del frontend")
        
        # Crear respuesta
        processing_mode = "text2img + controlnet_0.85" if (style_id and style_id != 'default') else "img2img_preserving_original"
        
        # Seleccionar imagen final principal (composición)
        final_image_info = None
        final_image_url = None
        if frontend_images:
            final_image_info = frontend_images[0]
            final_image_url = final_image_info['session_url']
            log_success(f"✅ Imagen final para frontend: {final_image_info['filename']} (nodo: {final_image_info.get('node_id', 'N/A')})")
        
        response = {
            "success": True,
            "job_id": job_id,  # Agregar ID del trabajo
            "prompt_id": prompt_id,
            "workflow_used": workflow_name,
            "processing_mode": processing_mode,
            "frame_color": frame_color,
            "style_used": style_id,
            "style_node_used": style_node_id if style_node_id else "auto-detectado",
            "include_upscale": include_upscale,  # Incluir configuración de upscale
            "base_name": base_name,
            "output_dir": output_dir,
            # � IMAGEN ORIGINAL: Incluir información de la imagen original guardada
            "original_image": original_info,
            "final_image_url": final_image_url,  # Nueva imagen final para el frontend
            "final_image": final_image_info,  # Información completa de la imagen final
            "generated_images": frontend_images,  # ✅ SOLO IMÁGENES PARA FRONTEND (composición únicamente)
            "total_images": len(frontend_images),  # Total para frontend
            "total_images_saved": len(saved_images),  # Total guardadas en disco
            "total_files_saved": len(saved_images) + 1,  # +1 por la original
            "include_upscale": include_upscale,  # Indicar si se incluyó upscale
            "our_output_dir": OUR_OUTPUT_DIR,  # Información del directorio personalizado
            "message": f"✅ Procesamiento completado en modo {processing_mode}. {len(saved_images) + 1} archivos guardados en directorio personalizado: 1 original + {len(saved_images)} generadas {'(composición + upscale)' if include_upscale else '(solo composición)'}. Frontend mostrará solo composición."
        }
        
        # Actualizar trabajo de sesión como completado
        session_manager.update_job(job_id,
            status='completed',
            current_operation='Completado',
            results=frontend_images,  # ✅ SOLO IMÁGENES PARA FRONTEND (composición únicamente)
            response_data=response
        )
        
        log_success("=== PROCESAMIENTO COMPLETADO ===")
        return jsonify(response)
        
    except FileNotFoundError as e:
        if job_id:
            session_manager.update_job(job_id, status='error', error=f"Workflow no encontrado: {str(e)}")
        log_error(f"Workflow no encontrado: {str(e)}")
        return jsonify({"error": f"Workflow no encontrado: {str(e)}"}), 404
    except TimeoutError as e:
        if job_id:
            session_manager.update_job(job_id, status='error', error=f"Timeout en procesamiento: {str(e)}")
        log_error(f"Timeout en procesamiento: {str(e)}")
        return jsonify({"error": f"Timeout en procesamiento: {str(e)}"}), 408
    except Exception as e:
        if job_id:
            session_manager.update_job(job_id, status='error', error=str(e))
        log_error(f"Error en procesamiento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-image/<base_name>/<filename>', methods=['GET'])
def get_image(base_name, filename):
    """Descarga una imagen del directorio de salida (mantener compatibilidad)"""
    try:
        # Sanitizar parámetros
        base_name = secure_filename(base_name)
        filename = secure_filename(filename)
        
        # 1. Buscar primero en nuestro directorio personalizado
        our_file_path = os.path.join(OUR_OUTPUT_DIR, base_name, filename)
        if os.path.exists(our_file_path):
            log_success(f"📤 Enviando archivo desde nuestro directorio: {our_file_path}")
            return send_file(our_file_path, as_attachment=True, download_name=filename)
        
        # 2. Buscar en el directorio de ComfyUI como respaldo
        comfyui_file_path = os.path.join(COMFYUI_OUTPUT_DIR, base_name, filename)
        if os.path.exists(comfyui_file_path):
            log_success(f"📤 Enviando archivo desde ComfyUI output: {comfyui_file_path}")
            return send_file(comfyui_file_path, as_attachment=True, download_name=filename)
        
        log_error(f"❌ Archivo no encontrado en ningún directorio: {filename}")
        return jsonify({"error": "Archivo no encontrado"}), 404
        
    except Exception as e:
        log_error(f"❌ Error al obtener imagen: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/workflow-nodes/<path:workflow_name>', methods=['GET'])
def get_workflow_nodes(workflow_name):
    """Obtiene los nodos candidatos para aplicar estilos en un workflow específico"""
    try:
        log_info(f"🔍 Buscando nodos para workflow: {workflow_name}")
        
        # Use the existing load_workflow function that handles path resolution
        workflow_data = load_workflow(workflow_name)
        
        # Collect SeargeTextInputV2 nodes as style candidates
        candidates = []
        for node_id, node in workflow_data.items():
            if node.get('class_type') == 'SeargeTextInputV2':
                title = node.get('_meta', {}).get('title', '')
                current_prompt = node.get('inputs', {}).get('prompt', '')
                
                # Determine if this is a recommended style node
                is_recommended = 'style' in title.lower() or node_id == '6'
                
                # Create node info with all properties the client expects
                node_info = {
                    'id': node_id,
                    'title': title,
                    'name': title or f'Nodo {node_id}',
                    'type': 'SeargeTextInputV2',
                    'description': f'Nodo de texto para prompts ({title})' if title else f'Nodo de texto {node_id}',
                    'recommended': is_recommended,
                    'current_value': current_prompt[:100] + '...' if len(current_prompt) > 100 else current_prompt,
                    'class_type': node.get('class_type')
                }
                
                candidates.append(node_info)
                log_info(f"📝 Nodo encontrado: {node_id} - {title} (recomendado: {is_recommended})")
        
        # Sort candidates: recommended first, then by node ID
        candidates.sort(key=lambda x: (not x['recommended'], int(x['id']) if x['id'].isdigit() else x['id']))
        
        log_success(f"✅ {len(candidates)} nodos candidatos encontrados para {workflow_name}")
        return jsonify({
            'success': True,
            'workflow_name': workflow_name, 
            'nodes': candidates,
            'candidate_nodes': candidates,  # For client compatibility
            'total_nodes': len(candidates)
        })
        
    except FileNotFoundError:
        log_error(f"❌ Workflow no encontrado: {workflow_name}")
        return jsonify({'success': False, 'error': 'Workflow not found'}), 404
    except Exception as e:
        log_error(f"❌ Error getting workflow nodes for {workflow_name}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/batch-status/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """
    Obtiene el status actual de un batch en progreso con información de sesión
    """
    with BATCH_LOCK:
        if batch_id not in ACTIVE_BATCHES:
            return jsonify({"error": "Batch no encontrado"}), 404
        
        batch_info = ACTIVE_BATCHES[batch_id].copy()
    
    # Agregar información del job de sesión si está disponible
    session_job_id = batch_info.get('session_job_id')
    if session_job_id:
        session_job = session_manager.get_job(session_job_id)
        if session_job:
            batch_info['session_job'] = {
                'id': session_job_id,
                'status': session_job.get('status'),
                'created_at': session_job.get('created_at'),
                'original_image_url': f"/session/images/{session_job_id}/original.png",
                'results_count': len(session_job.get('results', []))
            }
    
    return jsonify(batch_info)

@app.route('/batch-status/<batch_id>', methods=['DELETE'])
def clear_batch_status(batch_id):
    """
    Limpia un batch completado del tracking (mantiene la sesión persistente)
    """
    with BATCH_LOCK:
        if batch_id in ACTIVE_BATCHES:
            session_job_id = ACTIVE_BATCHES[batch_id].get('session_job_id')
            del ACTIVE_BATCHES[batch_id]
            
            message = f"Batch {batch_id} eliminado del tracking"
            if session_job_id:
                message += f". Job de sesión {session_job_id} mantenido para persistencia"
            
            return jsonify({
                "success": True, 
                "message": message,
                "session_job_id": session_job_id
            })
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

# ===== ENDPOINTS DE PERSISTENCIA DE SESIÓN =====

@app.route('/session/jobs', methods=['GET'])
def get_session_jobs():
    """Obtiene todos los trabajos de la sesión actual"""
    try:
        jobs = session_manager.get_all_active_jobs()
        summary = session_manager.get_session_summary()
        
        return jsonify({
            "success": True,
            "jobs": jobs,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/session/jobs/<job_id>', methods=['GET'])
def get_session_job(job_id):
    """Obtiene un trabajo específico de la sesión"""
    try:
        job = session_manager.get_job(job_id)
        if job:
            # Agregar URLs de imágenes si existen
            job['image_urls'] = session_manager.get_job_images(job_id)
            return jsonify({"success": True, "job": job})
        else:
            return jsonify({"success": False, "error": "Trabajo no encontrado"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/session/jobs/<job_id>', methods=['DELETE'])
def delete_session_job(job_id):
    """Elimina un trabajo de la sesión"""
    try:
        success = session_manager.delete_job(job_id)
        if success:
            return jsonify({"success": True, "message": "Trabajo eliminado"})
        else:
            return jsonify({"success": False, "error": "Trabajo no encontrado"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/session/images/<job_id>/<filename>', methods=['GET'])
def serve_session_image(job_id, filename):
    """Sirve imágenes de trabajos de sesión"""
    try:
        # Sanitizar parámetros
        job_id = secure_filename(job_id)
        filename = secure_filename(filename)
        
        image_path = os.path.join(session_manager.session_dir, job_id, filename)
        
        log_info(f"Buscando imagen de sesión: {image_path}")
        
        if os.path.exists(image_path):
            log_success(f"Imagen de sesión encontrada: {image_path}")
            return send_file(image_path)
        else:
            log_error(f"Imagen de sesión no encontrada: {image_path}")
            return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
        log_error(f"Error sirviendo imagen de sesión: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/session/cleanup', methods=['POST'])
def cleanup_session():
    """Limpia trabajos antiguos de la sesión"""
    try:
        hours = request.json.get('hours', 24) if request.is_json else 24
        cleaned_count = session_manager.cleanup_old_jobs(hours)
        
        return jsonify({
            "success": True,
            "message": f"Se limpiaron {cleaned_count} trabajos antiguos",
            "cleaned_count": cleaned_count
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/session/clear', methods=['POST'])
def clear_session():
    """Limpia completamente toda la sesión - todos los trabajos e imágenes"""
    try:
        log_info("🧹 Iniciando limpieza completa de sesión...")
        
        result = session_manager.clear_all_session()
        
        if result["success"]:
            log_success(f"✅ {result['message']}")
        else:
            log_error(f"❌ Error limpiando sesión: {result['error']}")
            
        return jsonify(result)
        
    except Exception as e:
        log_error(f"❌ Error en endpoint clear_session: {str(e)}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "jobs_cleared": 0,
            "session_reset": False
        }), 500

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
    Procesa una imagen con múltiples workflows simultáneamente con persistencia
    """
    batch_job_id = None
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
        include_upscale = batch_config.get('include_upscale', True)  # Default True para compatibilidad
        if isinstance(include_upscale, str):
            include_upscale = include_upscale.lower() == 'true'
        original_filename = request.form.get('original_filename', image_file.filename)
        
        # Verificar que tenemos un nombre válido
        if not original_filename or original_filename.strip() == '':
            original_filename = image_file.filename
            log_warning(f"⚠️ original_filename vacío, usando filename del archivo: '{original_filename}'")
        
        log_info(f"📋 Nombre archivo original para batch: '{original_filename}' (de form: '{request.form.get('original_filename')}', filename: '{image_file.filename}')")
        log_info(f"📈 Incluir upscale en batch: {include_upscale}")
        
        # ===== CREAR TRABAJO DE SESIÓN PARA BATCH =====
        batch_job_id = session_manager.create_job(
            job_type='batch',
            batch_config=batch_config,
            frame_color=frame_color,
            style=style,
            include_upscale=include_upscale,
            original_filename=original_filename,
            total_workflows=0,  # Se actualizará después
            completed_workflows=0,
            successful=0,
            failed=0
        )
        
        log_info(f"🆔 Trabajo de sesión batch creado: {batch_job_id}")
        
        # Actualizar estado del trabajo
        session_manager.update_job(batch_job_id, 
            status='processing', 
            current_operation='Validando parámetros del batch...'
        )
        
        log_info(f"📋 Configuración del batch: {batch_config}")
        log_info(f"🎨 Parámetros: frame_color={frame_color}, style={style}")
        
        # Actualizar estado del trabajo
        session_manager.update_job(batch_job_id, current_operation='Validando estilo...')
        
        # Validar estilo
        available_styles = get_available_styles()
        available_style_ids = [style['id'] for style in available_styles]
        if style not in available_style_ids:
            session_manager.update_job(batch_job_id, status='error', error=f"Estilo no encontrado: {style}")
            return jsonify({"error": f"Estilo no encontrado: {style}. Estilos disponibles: {available_style_ids}"}), 400
        
        # Actualizar estado del trabajo
        session_manager.update_job(batch_job_id, current_operation='Obteniendo workflows disponibles...')
        
        # Obtener workflows disponibles
        available_workflows = get_available_workflows()
        
        # Actualizar estado del trabajo
        session_manager.update_job(batch_job_id, current_operation='Filtrando workflows...')
        
        # Filtrar workflows según criterios del batch
        filtered_workflows = filter_workflows_for_batch(batch_config, available_workflows)
        
        if not filtered_workflows:
            error_msg = "No se encontraron workflows que coincidan con los criterios especificados"
            session_manager.update_job(batch_job_id, status='error', error=error_msg)
            return jsonify({
                "error": error_msg,
                "available_workflows": len(available_workflows),
                "criteria": batch_config
            }), 400
        
        # Actualizar total de workflows en el job de sesión
        session_manager.update_job(batch_job_id, 
            total_workflows=len(filtered_workflows),
            workflows=[w["id"] for w in filtered_workflows],
            current_operation=f'Preparando procesamiento de {len(filtered_workflows)} workflows...'
        )
        
        log_info(f"🎯 Workflows seleccionados: {len(filtered_workflows)}/{len(available_workflows)}")
        
        # Guardar imagen original en la sesión inmediatamente

        session_manager.update_job(batch_job_id, current_operation='Guardando imagen original...')
        image_file.seek(0)
        original_image_data = image_file.read()
        session_original_url = session_manager.save_job_image(batch_job_id, original_image_data, 'original.png')
        log_info(f"🖼️ Imagen original guardada en sesión: {session_original_url}")
        
        # Preparar parámetros comunes
        common_params = {
            "frame_color": frame_color,
            "style": style,
            "include_upscale": include_upscale,
            "original_filename": original_filename  # Agregar nombre de imagen original
        }
        
        log_info(f"🔧 Parámetros comunes para batch: {common_params}")
        
        # Obtener nodos de estilo si es necesario
        if filtered_workflows:
            sample_workflow = load_workflow(filtered_workflows[0]["id"])
            style_nodes = get_workflow_nodes_for_style(sample_workflow)
            if style_nodes:
                common_params["style_node"] = style_nodes[0]["id"]
        
        # Generar ID único para este batch (diferente del job_id de sesión)
        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
        
        # Almacenar referencia entre batch_id y job_id de sesión
        session_manager.update_job(batch_job_id, batch_tracking_id=batch_id)
        
        # Inicializar tracking del batch
        with BATCH_LOCK:
            ACTIVE_BATCHES[batch_id] = {
                "batch_id": batch_id,
                "session_job_id": batch_job_id,  # Referencia al job de sesión
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
        log_info(f"🆔 Session Job ID: {batch_job_id}")
        
        # Guardar el contenido de la imagen en memoria antes de iniciar el thread
        image_file.seek(0)
        image_data = BytesIO(image_file.read())
        image_data.seek(0)
        
        # Iniciar procesamiento en thread separado
        def process_batch_async():
            try:
                results = process_all_workflows_simultáneamente_with_tracking(
                    image_data, filtered_workflows, common_params, batch_id, batch_job_id
                )
                
                # Finalizar batch Y sesión
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        batch_info = ACTIVE_BATCHES[batch_id]
                        batch_info["status"] = "completed"
                        batch_info["total_processing_time"] = round(time.time() - batch_info["start_time"], 2)
                        batch_info["final_results"] = results
                
                # Finalizar job de sesión
                successful_results = [r for r in results if r.get('success', False)]
                failed_results = [r for r in results if not r.get('success', False)]
                
                session_manager.update_job(batch_job_id,
                    status='completed',
                    successful=len(successful_results),
                    failed=len(failed_results),
                    results=results,
                    current_operation=f'Completado: {len(successful_results)} exitosos, {len(failed_results)} fallidos'
                )
                
                log_success(f"✅ Batch {batch_id} completado: {len(successful_results)}/{len(results)} exitosos")
                        
            except Exception as e:
                log_error(f"❌ Error en procesamiento async de batch {batch_id}: {str(e)}")
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        ACTIVE_BATCHES[batch_id]["status"] = "error"
                        ACTIVE_BATCHES[batch_id]["error"] = str(e)
                
                # Actualizar job de sesión con error
                session_manager.update_job(batch_job_id, 
                    status='error', 
                    error=str(e),
                    current_operation=f'Error: {str(e)}'
                )
        
        # Iniciar thread
        thread = threading.Thread(target=process_batch_async)
        thread.daemon = True
        thread.start()
        
        # Retornar inmediatamente el ID del batch para tracking
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "session_job_id": batch_job_id,  # También devolver el job ID de sesión
            "processing_mode": "asynchronous_with_tracking",
            "status": "processing",
            "total_workflows": len(filtered_workflows),
            "message": "Batch iniciado. Use GET /batch-status/{batch_id} para consultar progreso o /session/jobs/{session_job_id} para persistencia",
            "status_endpoint": f"/batch-status/{batch_id}",
            "session_endpoint": f"/session/jobs/{batch_job_id}",
            "workflow_list": [w["id"] for w in filtered_workflows],
            "batch_config": batch_config,
            "common_params": common_params,
            "original_image_url": session_original_url
        })
        
    except Exception as e:
        log_error(f"❌ Error en procesamiento batch: {str(e)}")
        
        # Actualizar job de sesión si existe
        if batch_job_id:
            session_manager.update_job(batch_job_id, status='error', error=str(e))
        
        return jsonify({
            "success": False, 
            "error": str(e),
            "processing_mode": "simultaneous",
            "session_job_id": batch_job_id
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
        original_image_name = common_params.get('original_filename', 'batch_image')
        include_upscale = common_params.get('include_upscale', True)
        generated_images = extract_generated_images(outputs, original_image_name, include_upscale)
        
        # Crear directorio de salida basado en nombre de imagen original
        # Usar la misma lógica que en process_image individual
        original_image_name = common_params.get('original_filename', 'batch_image')
        base_image_name = secure_filename(original_image_name.rsplit('.', 1)[0] if '.' in original_image_name else 'image')
        
        log_info(f"📁 Creando directorio para batch: original_filename='{original_image_name}' -> base_name='{base_image_name}'")
        
        # Crear carpeta con nombre de imagen original
        batch_output_dir = create_output_directory(base_image_name)
        
        # Copiar imágenes generadas con nombre unificado (evitando duplicados)
        # Las imágenes en generated_images ya están filtradas según include_upscale
        saved_images = []
        include_upscale = common_params.get('include_upscale', True)
        log_info(f"📊 Batch - Resumen de imágenes extraídas: {len(generated_images)} imágenes (include_upscale={include_upscale})")
        for i, img in enumerate(generated_images):
            log_info(f"   {i+1}. Tipo: {img.get('image_type', 'unknown')}, Archivo: {img['filename']}, Nodo: {img.get('node_id', 'N/A')}")
        
        for img_info in generated_images:
            
            source_path = find_image_file(img_info['filename'], img_info['subfolder'])
            if source_path:
                # Crear nombre unificado: workflow_estilo_fecha_numero.extension
                style_name = common_params.get('style', 'default')
                workflow_clean = workflow_info['id'].replace('/', '_').replace('-', '_')
                
                # Obtener extensión original
                if '.' in img_info['filename']:
                    original_ext = img_info['filename'].rsplit('.', 1)[1]
                else:
                    original_ext = 'png'
                
                # Generar nombre único: workflow_estilo_fechahora_numero.extension
                img_number = len(saved_images) + 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{workflow_clean}_{style_name}_{timestamp}_{img_number:03d}.{original_ext}"
                
                dest_path = os.path.join(batch_output_dir, new_filename)
                
                # ✅ VERIFICAR SI YA EXISTE PARA EVITAR DUPLICADOS
                if os.path.exists(dest_path):
                    log_warning(f"⚠️ Archivo de lote ya existe, saltando: {new_filename}")
                    # Aún así lo agregamos a la lista con la info existente
                    saved_images.append({
                        'filename': new_filename,
                        'url': f"/get-image/{base_image_name}/{new_filename}",
                        'original_filename': img_info['filename'],
                        'workflow': workflow_info['id'],
                        'style': style_name,
                        'status': 'existing'  # Marcar como existente
                    })
                    continue
                
                # Copiar archivo si no existe
                shutil.copy2(source_path, dest_path)
                saved_images.append({
                    'filename': new_filename,
                    'url': f"/get-image/{base_image_name}/{new_filename}",
                    'original_filename': img_info['filename'],
                    'workflow': workflow_info['id'],
                    'style': style_name,
                    'status': 'new'  # Marcar como nuevo
                })
                log_success(f"✅ Imagen de lote nueva copiada: {dest_path}")
        
        # Guardar imagen original solo una vez por batch (no por workflow)
        original_dest = os.path.join(batch_output_dir, 'original.png')
        if not os.path.exists(original_dest):  # Solo si no existe ya
            image_file.seek(0)
            image = Image.open(image_file.stream)
            image.save(original_dest, format='PNG')
        
        processing_time = time.time() - start_time
        
        # 🎯 FILTRAR IMÁGENES PARA EL FRONTEND EN BATCH - SOLO COMPOSICIÓN FINAL
        log_info(f"🎯 Filtrando imágenes para frontend en batch - solo composición final...")
        frontend_images = []
        
        # En batch, todas las imágenes guardadas en saved_images ya son filtradas por extract_generated_images
        # pero necesitamos filtrar aún más para el frontend (solo composición)
        for img in saved_images:
            # En batch, las imágenes no tienen 'image_type' porque son renombradas,
            # pero sabemos que si include_upscale=False, solo hay composición
            # Si include_upscale=True, la primera imagen es composición y la segunda upscale
            if len(frontend_images) == 0:  # Siempre incluir la primera (composición)
                frontend_images.append(img)
                log_info(f"✅ Batch - Imagen de composición para frontend: {img['filename']}")
            # No incluir más imágenes (evitar upscale en frontend)
        
        log_info(f"📤 Batch - Para frontend: {len(frontend_images)} imagen(es) de {len(saved_images)} guardadas")
        log_info(f"💾 Batch - Guardadas en disco: {len(saved_images)} imágenes + 1 original")
        
        return {
            "workflow_id": workflow_info["id"],
            "workflow_info": workflow_info,
            "success": True,
            "generated_images": frontend_images,  # ✅ SOLO IMÁGENES PARA FRONTEND (composición únicamente)
            "all_images_saved": saved_images,  # Todas las imágenes guardadas en disco (para debugging)
            "original_image": {
                "filename": "original.png",
                "url": f"/get-image/{base_image_name}/original.png"
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

def process_all_workflows_simultáneamente_with_tracking(image_data, workflows, common_params, batch_id, session_job_id=None):
    """
    Procesa todos los workflows simultáneamente con tracking en tiempo real y persistencia
    image_data: BytesIO object con el contenido de la imagen
    session_job_id: ID del job de sesión para persistencia
    """
    import concurrent.futures
    
    results = []
    submitted_prompts = {}  # prompt_id -> workflow_info
    
    # Actualizar status: enviando workflows
    with BATCH_LOCK:
        if batch_id in ACTIVE_BATCHES:
            ACTIVE_BATCHES[batch_id]["status"] = "submitting"
            ACTIVE_BATCHES[batch_id]["current_operation"] = "Enviando workflows a ComfyUI..."
    
    # Actualizar también el job de sesión
    if session_job_id:
        session_manager.update_job(session_job_id, 
            status='processing',
            current_operation="Enviando workflows a ComfyUI..."
        )
    
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
        
        # Actualizar también el job de sesión
        if session_job_id:
            session_manager.update_job(session_job_id, 
                status='error',
                error=f"Error pre-cargando imagen: {str(e)}"
            )
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
            # Usar el nombre base de la imagen original para mantener consistencia
            original_image_name = common_params.get('original_filename', 'batch_image')
            base_image_name = secure_filename(original_image_name.rsplit('.', 1)[0] if '.' in original_image_name else 'image')
            
            log_info(f"🔧 Workflow {i+1}/{len(workflows)} - original: '{original_image_name}' -> base: '{base_image_name}'")
            
            workflow = load_workflow(workflow_info["id"])
            workflow = update_workflow(
                workflow, 
                unique_filename, 
                common_params["frame_color"], 
                common_params["style"], 
                common_params.get("style_node"),
                base_image_name  # output_subfolder basado en imagen original, no en workflow
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
        
        # Actualizar también el job de sesión
        if session_job_id:
            session_manager.update_job(session_job_id, 
                status='error',
                error="No se pudo enviar ningún workflow"
            )
        return results
    
    # Actualizar status: procesando
    with BATCH_LOCK:
        if batch_id in ACTIVE_BATCHES:
            ACTIVE_BATCHES[batch_id]["status"] = "processing"
            ACTIVE_BATCHES[batch_id]["current_operation"] = f"Procesando {len(submitted_prompts)} workflows..."
    
    # Actualizar también el job de sesión
    if session_job_id:
        session_manager.update_job(session_job_id, 
            current_operation=f"Procesando {len(submitted_prompts)} workflows..."
        )
    
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
            outputs = wait_for_completion(prompt_id, timeout=60000) # 10 minutos timeout
            
            # Extraer imágenes generadas
            original_image_name = common_params.get('original_filename', 'batch_image')
            include_upscale = common_params.get('include_upscale', True)
            generated_images = extract_generated_images(outputs, original_image_name, include_upscale)
            
            # Obtener nombre base de la imagen original usando la misma lógica que process_image individual
            original_image_name = common_params.get('original_filename', 'batch_image')
            base_image_name = secure_filename(original_image_name.rsplit('.', 1)[0] if '.' in original_image_name else 'image')
            
            log_info(f"📁 Procesando batch - original: '{original_image_name}' -> base: '{base_image_name}'")
            
            # Crear directorio de salida basado en nombre de imagen original (shared)
            batch_output_dir = create_output_directory(base_image_name)
            
            # 🔍 VERIFICAR ARCHIVOS EXISTENTES EN EL DIRECTORIO PARA EVITAR DUPLICADOS DE UPSCALE
            existing_files = []
            if os.path.exists(batch_output_dir):
                existing_files = [f.lower() for f in os.listdir(batch_output_dir)]
            
            # Verificar si ya existe una imagen upscale
            existing_upscale = any('upscale_' in f for f in existing_files)
            if existing_upscale:
                log_info(f"📈 Ya existe una imagen upscale en {batch_output_dir}, se omitirán nuevas imágenes upscale")
            
            # Copiar imágenes generadas con nombre de workflow y estilo (evitando duplicados)
            # Las imágenes en generated_images ya están filtradas según include_upscale
            saved_images = []
            session_images = []  # Para URLs de sesión
            include_upscale = common_params.get('include_upscale', True)
            log_info(f"📊 Tracking Batch - Resumen de imágenes extraídas: {len(generated_images)} imágenes (include_upscale={include_upscale})")
            for i, img in enumerate(generated_images):
                log_info(f"   {i+1}. Tipo: {img.get('image_type', 'unknown')}, Archivo: {img['filename']}, Nodo: {img.get('node_id', 'N/A')}")
            
            for img_info in generated_images:
                
                source_path = find_image_file(img_info['filename'], img_info['subfolder'])
                if source_path:
                    # Obtener extensión original
                    if '.' in img_info['filename']:
                        original_ext = img_info['filename'].rsplit('.', 1)[1]
                    else:
                        original_ext = 'png'
                    
                    # Diferentes estrategias de naming según el tipo de imagen
                    image_type = img_info.get('image_type', 'unknown')
                    
                    # 🔍 LOG DETALLADO PARA DEBUGGING EN BATCH TRACKING
                    log_info(f"🔍 BATCH TRACKING - Procesando imagen: {img_info['filename']}")
                    log_info(f"   📋 Tipo detectado: {image_type}")
                    log_info(f"   📋 Nodo origen: {img_info.get('node_id', 'N/A')}")
                    log_info(f"   📋 Workflow: {workflow_info['id']}")
                    log_info(f"   📋 Archivo original de ComfyUI: {img_info['filename']}")
                    log_info(f"   📋 Subfolder: {img_info.get('subfolder', 'N/A')}")
                    
                    if image_type == 'upscale':
                        # 🔍 VERIFICAR SI YA EXISTE UPSCALE ANTES DE PROCESAR
                        if existing_upscale:
                            log_warning(f"⚠️ Ya existe imagen upscale, saltando: {img_info['filename']}")
                            # Buscar el archivo upscale existente para referenciarlo
                            existing_upscale_file = next((f for f in os.listdir(batch_output_dir) if 'upscale_' in f.lower()), None)
                            if existing_upscale_file:
                                # Agregar referencia al archivo existente
                                saved_images.append({
                                    'filename': existing_upscale_file,
                                    'url': f"/get-image/{base_image_name}/{existing_upscale_file}",
                                    'original_filename': img_info['filename'],
                                    'workflow': workflow_info['id'],
                                    'image_type': image_type,
                                    'status': 'existing_previous'  # Marcar como existente de workflow anterior
                                })
                                log_info(f"📈 Referenciando upscale existente: {existing_upscale_file}")
                            continue
                        
                        # ✅ UPSCALE: Nombre consistente basado en imagen original (no en workflow)
                        # Formato: upscale_nombreoriginal_timestamp.ext
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        new_filename = f"upscale_{base_image_name}_{timestamp}.{original_ext}"
                        
                        log_info(f"📈 BATCH TRACKING UPSCALE - Nombre generado: {new_filename}")
                        log_info(f"   📈 Razón: image_type='{image_type}' -> usando formato upscale_[base]_[timestamp]")
                    else:
                        # ✅ COMPOSICIÓN: Nombre único con workflow para distinguir diferentes composiciones
                        # Formato: workflow_estilo_timestamp_numero.ext
                        style_name = common_params.get('style', 'default')
                        workflow_clean = workflow_info['id'].replace('/', '_').replace('-', '_')
                        img_number = len(saved_images) + 1
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        new_filename = f"{workflow_clean}_{style_name}_{timestamp}_{img_number:03d}.{original_ext}"
                        
                        log_info(f"🎯 BATCH TRACKING COMPOSICIÓN - Nombre generado: {new_filename}")
                        log_info(f"   🎯 Razón: image_type='{image_type}' -> usando formato [workflow]_[style]_[timestamp]_[num]")
                        log_info(f"   🎯 Componentes: workflow='{workflow_clean}', style='{style_name}', num={img_number:03d}")
                    
                    dest_path = os.path.join(batch_output_dir, new_filename)
                    
                    # ✅ VERIFICAR SI YA EXISTE PARA EVITAR DUPLICADOS
                    if os.path.exists(dest_path):
                        log_warning(f"⚠️ Archivo de tracking ya existe, saltando: {new_filename}")
                        # Intentar guardarlo en sesión si no está ya guardado
                        session_url = None
                        if session_job_id:
                            try:
                                with open(dest_path, 'rb') as img_file:
                                    session_url = session_manager.save_job_image(session_job_id, img_file.read(), new_filename)
                            except Exception as e:
                                log_warning(f"⚠️ No se pudo guardar archivo existente en sesión: {str(e)}")
                        
                        saved_images.append({
                            'filename': new_filename,
                            'url': f"/get-image/{base_image_name}/{new_filename}",
                            'session_url': session_url,
                            'original_filename': img_info['filename'],
                            'workflow': workflow_info['id'],
                            'image_type': image_type,  # Agregar tipo de imagen
                            'status': 'existing'  # Marcar como existente
                        })
                        
                        if session_url:
                            session_images.append(session_url)
                        continue
                    
                    # Copiar archivo si no existe
                    shutil.copy2(source_path, dest_path)
                    
                    # Guardar también en sesión
                    with open(dest_path, 'rb') as img_file:
                        session_url = session_manager.save_job_image(session_job_id, img_file.read(), new_filename)
                    
                    # Agregar a lista de guardadas
                    saved_images.append({
                        'filename': new_filename,
                        'url': f"/get-image/{base_image_name}/{new_filename}",
                        'session_url': session_url,  # URL de sesión persistente
                        'original_filename': img_info['filename'],
                        'workflow': workflow_info['id'],
                        'image_type': image_type,  # Agregar tipo de imagen
                        'status': 'new'  # Marcar como nuevo
                    })
                    
                    # Log específico para upscales y composiciones en batch tracking
                    if image_type == 'upscale':
                        log_info(f"📈 BATCH TRACKING UPSCALE guardado con nombre consistente: {new_filename}")
                        # Marcar que ya existe upscale para evitar duplicados en siguientes workflows del batch
                        existing_upscale = True
                    else:
                        log_info(f"🎯 BATCH TRACKING COMPOSICIÓN guardada con nombre único: {new_filename}")
                    
                    if session_url:
                        session_images.append(session_url)
            
            # Guardar imagen original solo una vez (check si ya existe)
            original_dest = os.path.join(batch_output_dir, 'original.png')
            if not os.path.exists(original_dest):  # Solo si no existe ya
                master_image.save(original_dest, format='PNG')
                log_info(f"💾 Imagen original guardada: {original_dest}")
            
            # Guardar también imagen original en la sesión (solo una vez por batch)
            original_session_url = None
            if session_job_id:
                try:
                    # Verificar si ya se guardó la original en sesión
                    existing_images = session_manager.get_job_images(session_job_id)
                    original_already_saved = any('original.png' in img for img in existing_images)
                    
                    if not original_already_saved:
                        with open(original_dest, 'rb') as img_file:
                            original_session_url = session_manager.save_job_image(session_job_id, img_file.read(), 'original.png')
                except Exception as e:
                    log_warning(f"⚠️ No se pudo guardar imagen original en sesión: {str(e)}")
            
            processing_time = time.time() - start_time
            
            # 🎯 FILTRAR IMÁGENES PARA EL FRONTEND EN BATCH TRACKING - SOLO COMPOSICIÓN FINAL
            log_info(f"🎯 Filtrando imágenes para frontend en batch tracking - solo composición final...")
            frontend_images = []
            
            # En batch tracking, filtrar para mostrar solo la primera imagen (composición)
            if saved_images:
                frontend_images = [saved_images[0]]  # Solo la primera (composición)
                log_info(f"✅ Batch tracking - Imagen de composición para frontend: {saved_images[0]['filename']}")
            
            log_info(f"📤 Batch tracking - Para frontend: {len(frontend_images)} imagen(es) de {len(saved_images)} guardadas")
            
            result = {
                "workflow_id": workflow_info["id"],
                "workflow_info": workflow_info,
                "success": True,
                "generated_images": frontend_images,  # ✅ SOLO IMÁGENES PARA FRONTEND (composición únicamente)
                "all_images_saved": saved_images,  # Todas las imágenes guardadas en disco (para debugging)
                "session_images": session_images,  # URLs de sesión persistentes
                "original_image": {
                    "filename": "original.png",
                    "url": f"/get-image/{base_image_name}/original.png",
                    "session_url": original_session_url  # URL de sesión para imagen original
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
            
            # *** ACTUALIZAR TAMBIÉN EL JOB DE SESIÓN ***
            if session_job_id:
                # Obtener estado actual del batch
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        batch_info = ACTIVE_BATCHES[batch_id]
                        session_manager.update_job(session_job_id,
                            completed_workflows=batch_info["completed_workflows"],
                            successful=batch_info["successful"],
                            failed=batch_info["failed"],
                            current_operation=batch_info["current_operation"],
                            results=batch_info["results"][:10]  # Solo los últimos 10 para no sobrecargar
                        )
            
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
            
            # *** ACTUALIZAR TAMBIÉN EL JOB DE SESIÓN EN CASO DE ERROR ***
            if session_job_id:
                # Obtener estado actual del batch
                with BATCH_LOCK:
                    if batch_id in ACTIVE_BATCHES:
                        batch_info = ACTIVE_BATCHES[batch_id]
                        session_manager.update_job(session_job_id,
                            completed_workflows=batch_info["completed_workflows"],
                            successful=batch_info["successful"],
                            failed=batch_info["failed"],
                            current_operation=batch_info["current_operation"],
                            results=batch_info["results"][:10]  # Solo los últimos 10 para no sobrecargar
                        )
            
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
    import os
    # Solo ejecutar el arranque si es el proceso principal del reloader
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        log_info("🚀 Iniciando ComfyUI API REST v2.0.0...")
        log_info(f"📁 Directorio de workflows: {WORKFLOWS_DIR}")
        log_info(f"📁 Directorio de input: {COMFYUI_INPUT_DIR}")
        log_info(f"📁 Directorio de output: {COMFYUI_OUTPUT_DIR}")
        log_info(f"🌐 ComfyUI URL: {COMFYUI_URL}")
        # Verificar conexión con ComfyUI
        try:
            response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
            if response.status_code == 200:
                log_success("Conexión exitosa con ComfyUI")
            else:
                log_warning(f"No se pudo conectar con ComfyUI: status {response.status_code}")
        except Exception as e:
            log_warning(f"⚠️ No se pudo conectar con ComfyUI: {str(e)}")
        # Contar workflows disponibles
        try:
            workflows = []
            if os.path.exists(WORKFLOWS_DIR):
                for root, dirs, files in os.walk(WORKFLOWS_DIR):
                    for filename in files:
                        if filename.endswith('.json'):
                            workflows.append(filename)
            log_info(f"📊 {len(workflows)} workflows encontrados")
        except Exception as e:
            log_warning(f"⚠️ Error contando workflows: {str(e)}")
        # Iniciar servidor
        log_info("🌟 Servidor iniciado en http://localhost:5000")
        log_info("📱 Cliente web disponible en: http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
