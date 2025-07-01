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
from datetime import datetime
from io import BytesIO

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import requests
from werkzeug.utils import secure_filename

# Configuración básica
app = Flask(__name__)
CORS(app)

# URLs y directorios
COMFYUI_HOST = os.getenv('COMFYUI_HOST', 'localhost')
COMFYUI_PORT = os.getenv('COMFYUI_PORT', '8188')
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

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

def update_workflow(workflow, image_filename, frame_color='black', output_subfolder=None):
    """
    Actualiza el workflow con la nueva imagen y configuraciones
    Retorna: workflow actualizado
    """
    workflow_copy = copy.deepcopy(workflow)
    
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
    
    log_success("Workflow actualizado correctamente")
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
        "available_colors": WORKFLOW_CONFIG.get("frame_colors", ["black", "white", "brown", "gold", "silver"])
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
        original_filename = request.form.get('original_filename', file.filename)
        
        log_info(f"Parámetros: workflow={workflow_name}, frame_color={frame_color}, file={original_filename}")
        
        # Validar color del marco
        if frame_color not in WORKFLOW_CONFIG['frame_colors']:
            frame_color = 'black'
            log_warning(f"Color de marco no válido, usando: {frame_color}")
        
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
        updated_workflow = update_workflow(workflow, workflow_filename, frame_color, base_name)
        
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
        response = {
            "success": True,
            "prompt_id": prompt_id,
            "workflow_used": workflow_name,
            "frame_color": frame_color,
            "base_name": base_name,
            "output_dir": output_dir,
            "original_image": {
                "filename": "original.png",
                "url": f"/get-image/{base_name}/original.png"
            },
            "generated_images": saved_images,
            "total_images": len(saved_images),
            "message": f"Procesamiento completado. {len(saved_images)} imágenes generadas."
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
                "endpoints": ["/health", "/workflows", "/process-image", "/get-image"],
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
    """Sirve el cliente web original"""
    client_path = os.path.join(BASE_DIR, 'web_client.html')
    if os.path.exists(client_path):
        return send_file(client_path)
    else:
        return jsonify({"error": "Cliente web original no encontrado"}), 404

# ==================== INICIO DE LA APLICACIÓN ====================

if __name__ == '__main__':
    log_info("=== INICIANDO COMFYUI API REST v2.0 ===")
    log_info(f"ComfyUI URL: {COMFYUI_URL}")
    log_info(f"Directorio de workflows: {WORKFLOWS_DIR}")
    log_info(f"Directorio de input: {COMFYUI_INPUT_DIR}")
    log_info(f"Directorio de output: {COMFYUI_OUTPUT_DIR}")
    
    # Verificar que los directorios existen
    if os.path.exists(COMFYUI_INPUT_DIR):
        log_success(f"✅ Directorio input existe: {COMFYUI_INPUT_DIR}")
    else:
        log_error(f"❌ Directorio input NO existe: {COMFYUI_INPUT_DIR}")
    
    if os.path.exists(COMFYUI_OUTPUT_DIR):
        log_success(f"✅ Directorio output existe: {COMFYUI_OUTPUT_DIR}")
    else:
        log_error(f"❌ Directorio output NO existe: {COMFYUI_OUTPUT_DIR}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
