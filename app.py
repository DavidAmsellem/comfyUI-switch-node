#!/usr/bin/env python3
"""
API REST para ComfyUI que permite enviar una imagen para ser procesada
en un flujo automático de generación de imágenes.
"""

import os
import json
import uuid
import asyncio
import logging
import base64
import time
import shutil
from io import BytesIO
from typing import Optional, Dict, Any

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import websocket
import requests
from werkzeug.utils import secure_filename

# Configuración
app = Flask(__name__)
CORS(app)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de ComfyUI
COMFYUI_HOST = os.getenv('COMFYUI_HOST', 'localhost')
COMFYUI_PORT = os.getenv('COMFYUI_PORT', '8188')
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
COMFYUI_WS_URL = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws"

# Directorio para archivos temporales
UPLOAD_FOLDER = 'temp_uploads'
OUTPUT_FOLDER = 'outputs'
WORKFLOWS_FOLDER = 'workflows'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Directorio de ComfyUI para imágenes de entrada
COMFYUI_INPUT_FOLDER = '/media/davidadmin/Nuevo vol/comfyUI/ComfyUI/input'

# Crear directorios si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(WORKFLOWS_FOLDER, exist_ok=True)
os.makedirs(COMFYUI_INPUT_FOLDER, exist_ok=True)

# Workflow por defecto (formato API)
DEFAULT_WORKFLOW = 'workflow_api.json'


def allowed_file(filename: str) -> bool:
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS





def load_workflow_from_file(workflow_path: str) -> Dict[str, Any]:
    """Carga un workflow directamente desde un archivo JSON."""
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error al cargar workflow desde {workflow_path}: {str(e)}")
        raise


def get_available_workflows() -> Dict[str, Dict[str, Any]]:
    """
    Obtiene todos los workflows disponibles con información adicional incluyendo dimensiones.
    """
    workflows = {}
    
    # Workflows en la carpeta workflows/
    if os.path.exists(WORKFLOWS_FOLDER):
        for filename in os.listdir(WORKFLOWS_FOLDER):
            if filename.endswith('.json'):
                try:
                    workflow_id = filename.replace('.json', '')
                    workflow_path = os.path.join(WORKFLOWS_FOLDER, filename)
                    
                    logger.info(f"Cargando workflow: {workflow_path}")
                    
                    # Cargar workflow directamente desde archivo
                    workflow = load_workflow_from_file(workflow_path)
                    
                    # Verificar compatibilidad (nodo ID 97)
                    has_target_node = "97" in workflow
                    is_load_image = False
                    
                    if has_target_node:
                        target_node = workflow["97"]
                        is_load_image = target_node.get('class_type') == 'LoadImage'
                    
                    workflows[workflow_id] = {
                        "path": workflow_path,
                        "total_nodes": len(workflow),
                        "has_target_node": has_target_node,
                        "is_compatible": has_target_node and is_load_image,
                        "status": "compatible" if (has_target_node and is_load_image) else "incompatible"
                    }
                    
                except Exception as e:
                    logger.error(f"Error cargando workflow {filename}: {e}")
                    workflows[workflow_id] = {
                        "path": os.path.join(WORKFLOWS_FOLDER, filename),
                        "error": str(e),
                        "status": "error"
                    }
    
    # Workflow por defecto
    if os.path.exists(DEFAULT_WORKFLOW):
        try:
            workflow = load_workflow_from_file(DEFAULT_WORKFLOW)
            workflows["default"] = {
                "path": DEFAULT_WORKFLOW,
                "total_nodes": len(workflow),
                "status": "default"
            }
        except Exception as e:
            logger.error(f"Error al cargar workflow por defecto: {str(e)}")
            workflows["default"] = {
                "path": DEFAULT_WORKFLOW,
                "total_nodes": 0,
                "status": "error",
                "error": str(e)
            }
    
    return workflows


def load_workflow(workflow_name: str = 'default') -> Dict[str, Any]:
    """Carga un workflow específico desde el archivo JSON."""
    try:
        # Determinar la ruta del archivo
        if workflow_name == 'default':
            workflow_path = DEFAULT_WORKFLOW
        else:
            workflow_path = os.path.join(WORKFLOWS_FOLDER, f"{workflow_name}.json")
        
        # Verificar si el archivo existe
        if not os.path.exists(workflow_path):
            if workflow_name != 'default':
                logger.warning(f"Workflow '{workflow_name}' no encontrado, usando 'default'")
                workflow_path = DEFAULT_WORKFLOW
            
            if not os.path.exists(workflow_path):
                raise FileNotFoundError(f"No se encontró ningún workflow válido")
        
        logger.info(f"Cargando workflow: {workflow_path}")
        return load_workflow_from_file(workflow_path)
        
    except Exception as e:
        logger.error(f"Error al cargar workflow '{workflow_name}': {str(e)}")
        raise


def find_load_image_nodes(workflow: Dict[str, Any]) -> list:
    """Encuentra todos los nodos LoadImage en el workflow."""
    load_image_nodes = []
    for node in workflow.get('nodes', []):
        if isinstance(node, dict) and node.get('type') == 'LoadImage':
            load_image_nodes.append((node.get('id'), node))
    return load_image_nodes


def update_workflow_with_image(workflow: Dict[str, Any], image_filename: str, target_node_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Actualiza el workflow API para usar la imagen subida.
    SOLO modifica el nodo ID "97" que está conectado al SimpleFrameGenerator.
    NO permite modificar ningún otro nodo LoadImage por seguridad.
    """
    import copy
    workflow_copy = copy.deepcopy(workflow)
    
    # ID FIJO del nodo LoadImage conectado al SimpleFrameGenerator - NO MODIFICABLE
    FIXED_TARGET_NODE_ID = "97"
    
    logger.info(f"Actualizando workflow con imagen: {image_filename}")
    
    # RECHAZAR cualquier intento de usar otro nodo
    if target_node_id is not None and str(target_node_id) != str(FIXED_TARGET_NODE_ID):
        raise ValueError(f"ACCESO DENEGADO: Solo se permite modificar el nodo ID {FIXED_TARGET_NODE_ID}. Se intentó usar el nodo {target_node_id}")
    
    # Verificar que el nodo existe en el workflow API
    if FIXED_TARGET_NODE_ID not in workflow_copy:
        raise ValueError(f"ERROR CRÍTICO: No se encontró el nodo ID {FIXED_TARGET_NODE_ID} en el workflow API")
    
    target_node = workflow_copy[FIXED_TARGET_NODE_ID]
    logger.info(f"Nodo 97 original: {target_node}")
    
    # Doble verificación de seguridad: debe ser LoadImage
    if target_node.get('class_type') != 'LoadImage':
        raise ValueError(f"ERROR CRÍTICO: El nodo ID {FIXED_TARGET_NODE_ID} no es de tipo LoadImage (encontrado: {target_node.get('class_type')})")
    
    # Guardar imagen anterior para log de seguridad
    previous_image = target_node.get('inputs', {}).get('image', 'ninguna')
    
    # Actualizar ÚNICAMENTE el nodo ID "97"
    if 'inputs' not in target_node:
        target_node['inputs'] = {}
    
    target_node['inputs']['image'] = image_filename
    
    logger.info(f"NODO ID {FIXED_TARGET_NODE_ID}: '{previous_image}' → '{image_filename}'")
    logger.info(f"Nodo 97 actualizado: {target_node}")
    return workflow_copy


def save_image_from_request(file) -> str:
    """Guarda la imagen del request y devuelve el nombre del archivo."""
    if not file or file.filename == '':
        raise ValueError("No se proporcionó ningún archivo")
    
    if not allowed_file(file.filename):
        raise ValueError(f"Tipo de archivo no permitido. Tipos permitidos: {ALLOWED_EXTENSIONS}")
    
    # Generar nombre único para el archivo
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Guardar en la carpeta input de ComfyUI
    comfyui_filepath = os.path.join(COMFYUI_INPUT_FOLDER, unique_filename)
    
    # También guardar una copia en nuestro directorio temporal
    temp_filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # Guardar archivo en ambas ubicaciones
    file.save(temp_filepath)
    
    # Verificar que es una imagen válida
    try:
        with Image.open(temp_filepath) as img:
            img.verify()
    except Exception as e:
        os.remove(temp_filepath)
        raise ValueError(f"El archivo no es una imagen válida: {e}")
    
    # Copiar a la carpeta de ComfyUI
    try:
        shutil.copy2(temp_filepath, comfyui_filepath)
        logger.info(f"Imagen guardada en ComfyUI input: {unique_filename}")
    except Exception as e:
        logger.error(f"Error copiando imagen a ComfyUI: {e}")
        os.remove(temp_filepath)
        raise ValueError(f"No se pudo copiar la imagen a ComfyUI: {e}")
    
    logger.info(f"Imagen guardada: {unique_filename}")
    return unique_filename


async def submit_workflow_to_comfyui(workflow: Dict[str, Any]) -> str:
    """Envía el workflow a ComfyUI usando el endpoint /prompt."""
    try:
        client_id = str(uuid.uuid4())
        
        # Debug: verificar que el nodo 97 tiene la imagen correcta
        if "97" in workflow:
            node_97 = workflow["97"]
            logger.info(f"Nodo 97 antes de enviar: {node_97}")
        else:
            logger.warning("¡Nodo 97 no encontrado en el workflow!")
        
        # Preparar datos para el endpoint /prompt (formato API)
        prompt_data = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        logger.info(f"Enviando workflow a ComfyUI con client_id: {client_id}")
        
        # Enviar a ComfyUI usando /prompt
        response = requests.post(
            f"{COMFYUI_URL}/prompt",
            json=prompt_data,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Error al enviar workflow: {response.status_code} - {response.text}")
            raise Exception(f"ComfyUI respondió con error {response.status_code}: {response.text}")
        
        # El endpoint /prompt devuelve el prompt_id
        response_data = response.json()
        logger.info(f"Respuesta de ComfyUI: {response_data}")
        
        if 'prompt_id' in response_data:
            prompt_id = response_data['prompt_id']
            logger.info(f"Workflow enviado a ComfyUI con prompt_id: {prompt_id}")
            return prompt_id
        else:
            logger.error(f"Respuesta inesperada de ComfyUI: {response_data}")
            raise Exception(f"ComfyUI no devolvió prompt_id: {response_data}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión con ComfyUI: {e}")
        raise Exception(f"No se pudo conectar con ComfyUI: {e}")



def convert_workflow_to_api_format(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte workflow UI de ComfyUI al formato API."""
    api_workflow = {}
    
    for node in workflow.get('nodes', []):
        if not isinstance(node, dict):
            continue
            
        node_id = str(node.get('id', ''))
        if not node_id:
            continue
        
        api_node = {
            "class_type": node.get('type', ''),
            "inputs": {}
        }
        
        # Convertir inputs de links
        for input_info in node.get('inputs', []):
            if isinstance(input_info, dict) and 'link' in input_info:
                input_name = input_info.get('name', '')
                link_id = input_info.get('link')
                
                # Buscar el nodo origen del link
                source_node = find_node_by_output_link(workflow, link_id)
                if source_node:
                    source_node_id = str(source_node.get('id', ''))
                    output_index = find_output_index_by_link(source_node, link_id)
                    if source_node_id and output_index is not None:
                        api_node["inputs"][input_name] = [source_node_id, output_index]
        
        # Convertir widgets_values
        if 'widgets_values' in node:
            # Para LoadImage, el primer widget_value es el nombre de la imagen
            if node.get('type') == 'LoadImage' and node['widgets_values']:
                api_node["inputs"]["image"] = node['widgets_values'][0]
                if len(node['widgets_values']) > 1:
                    api_node["inputs"]["upload"] = node['widgets_values'][1]
            else:
                # Para otros tipos de nodos, convertir widgets según el tipo
                widget_inputs = get_widget_inputs_for_node_type(node.get('type', ''), node['widgets_values'])
                api_node["inputs"].update(widget_inputs)
        
        api_workflow[node_id] = api_node
    
    return api_workflow


def find_node_by_output_link(workflow: Dict[str, Any], link_id: int) -> Optional[Dict[str, Any]]:
    """Encuentra el nodo que produce un link específico."""
    for node in workflow.get('nodes', []):
        if isinstance(node, dict):
            for output in node.get('outputs', []):
                if isinstance(output, dict) and 'links' in output:
                    links = output.get('links', [])
                    if isinstance(links, list) and link_id in links:
                        return node
    return None


def find_output_index_by_link(node: Dict[str, Any], link_id: int) -> Optional[int]:
    """Encuentra el índice de salida que corresponde a un link."""
    for i, output in enumerate(node.get('outputs', [])):
        if isinstance(output, dict) and 'links' in output:
            links = output.get('links', [])
            if isinstance(links, list) and link_id in links:
                return i
    return None


def get_widget_inputs_for_node_type(node_type: str, widgets_values: list) -> Dict[str, Any]:
    """Convierte widgets_values a inputs según el tipo de nodo."""
    inputs = {}
    
    # Mapeo básico para tipos comunes de nodos
    if node_type == "KSampler":
        widget_names = ["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"]
        for i, value in enumerate(widgets_values[:len(widget_names)]):
            inputs[widget_names[i]] = value
    elif node_type == "CheckpointLoaderSimple":
        if widgets_values:
            inputs["ckpt_name"] = widgets_values[0]
    elif node_type == "CLIPTextEncode":
        if widgets_values:
            inputs["text"] = widgets_values[0]
    elif node_type == "EmptyLatentImage":
        widget_names = ["width", "height", "batch_size"]
        for i, value in enumerate(widgets_values[:len(widget_names)]):
            inputs[widget_names[i]] = value
    # Agregar más tipos según necesidad
    
    return inputs


def wait_for_completion(prompt_id: str, timeout: int = 600) -> Dict[str, Any]:
    """
    Espera a que ComfyUI complete el procesamiento.
    Timeout aumentado para sistemas lentos.
    """
    try:
        import time
        
        logger.info(f"Esperando completion para prompt_id: {prompt_id} (timeout: {timeout}s)")
        
        # Consultar el historial para verificar si está completo
        for i in range(timeout):
            try:
                response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
                
                if response.status_code == 200:
                    history = response.json()
                    if prompt_id in history:
                        prompt_history = history[prompt_id]
                        
                        # Verificar si hay outputs (completado)
                        if 'outputs' in prompt_history:
                            logger.info(f"Procesamiento completado para prompt_id: {prompt_id}")
                            return prompt_history['outputs']
                        
                        # Verificar si hay error
                        if 'status' in prompt_history:
                            status = prompt_history['status']
                            if 'error' in status:
                                raise Exception(f"Error en ComfyUI: {status['error']}")
                
                # Log de progreso cada 30 segundos
                if i % 30 == 0 and i > 0:
                    logger.info(f"Esperando completion... {i}/{timeout} segundos transcurridos")
                
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                if i % 60 == 0:  # Log cada minuto
                    logger.warning(f"Error temporal consultando ComfyUI (reintentando): {e}")
                time.sleep(1)
                continue
        
        raise Exception(f"Timeout esperando completion del prompt_id: {prompt_id} después de {timeout} segundos")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error consultando historial de ComfyUI: {e}")
        raise Exception(f"Error consultando estado: {e}")


def get_output_images(outputs: Dict[str, Any]) -> list:
    """Extrae las rutas de las imágenes de salida."""
    output_images = []
    
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            for image_info in node_output['images']:
                if 'filename' in image_info and 'subfolder' in image_info:
                    output_images.append({
                        'filename': image_info['filename'],
                        'subfolder': image_info['subfolder'],
                        'type': image_info.get('type', 'output')
                    })
    
    return output_images


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud."""
    try:
        # Verificar conexión con ComfyUI
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        comfyui_status = "ok" if response.status_code == 200 else "error"
    except:
        comfyui_status = "error"
    
    return jsonify({
        "status": "ok",
        "comfyui_connection": comfyui_status,
        "version": "1.0.0"
    })


@app.route('/process-image', methods=['POST'])
def process_image():
    """
    Endpoint principal para procesar una imagen.
    Recibe una imagen y la procesa usando ÚNICAMENTE el nodo ID 97 del workflow seleccionado.
    """
    try:
        # Verificar que se envió un archivo
        if 'image' not in request.files:
            return jsonify({"error": "No se proporcionó ninguna imagen"}), 400
        
        file = request.files['image']
        
        # Obtener workflow seleccionado (opcional)
        workflow_name = request.form.get('workflow', 'default')
        
        # BLOQUEAR cualquier intento de especificar target_node_id
        if 'target_node_id' in request.form:
            return jsonify({
                "error": "ACCESO DENEGADO: No se permite especificar target_node_id. Solo se usa el nodo ID 97"
            }), 403
        
        # Verificar que el workflow existe
        available_workflows = get_available_workflows()
        if workflow_name not in available_workflows:
            return jsonify({
                "error": f"Workflow '{workflow_name}' no encontrado. Disponibles: {list(available_workflows.keys())}"
            }), 400
        
        # Guardar la imagen
        image_filename = save_image_from_request(file)
        
        # Cargar y actualizar el workflow seleccionado (SOLO nodo ID 97)
        workflow = load_workflow(workflow_name)
        updated_workflow = update_workflow_with_image(workflow, image_filename, None)  # None fuerza uso del ID 97
        
        # Enviar a ComfyUI
        prompt_id = asyncio.run(submit_workflow_to_comfyui(updated_workflow))
        
        # Esperar a que complete
        outputs = wait_for_completion(prompt_id)
        
        # Obtener imágenes de salida
        output_images = get_output_images(outputs)
        
        # Limpiar archivo temporal
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, image_filename))
        except:
            pass
        
        return jsonify({
            "success": True,
            "prompt_id": prompt_id,
            "workflow_used": workflow_name,
            "workflow_path": available_workflows[workflow_name],
            "output_images": output_images,
            "message": f"Imagen procesada exitosamente usando nodo ID 97 en workflow '{workflow_name}'",
            "security_note": "Solo se permite modificar el nodo LoadImage ID 97"
        })
        
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@app.route('/get-image/<filename>', methods=['GET'])
def get_image(filename):
    """Endpoint para descargar imágenes generadas."""
    try:
        subfolder = request.args.get('subfolder', '')
        image_type = request.args.get('type', 'output')
        
        # Construir la URL de ComfyUI para obtener la imagen
        params = {
            'filename': filename,
            'subfolder': subfolder,
            'type': image_type
        }
        
        response = requests.get(f"{COMFYUI_URL}/view", params=params)
        
        if response.status_code != 200:
            return jsonify({"error": "Imagen no encontrada"}), 404
        
        # Crear un objeto de archivo temporal para enviar
        img_io = BytesIO(response.content)
        img_io.seek(0)
        
        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo imagen: {e}")
        return jsonify({"error": f"Error obteniendo imagen: {str(e)}"}), 500


@app.route('/workflow-info', methods=['GET'])
def workflow_info():
    """
    Endpoint para obtener información sobre el workflow.
    SOLO muestra información del nodo ID 97 por seguridad.
    """
    try:
        workflow = load_workflow()
        
        # SOLO buscar el nodo ID 97
        ALLOWED_NODE_ID = 97
        target_node_info = None
        total_load_image_nodes = 0
        
        nodes = workflow.get('nodes', [])
        for node in nodes:
            if isinstance(node, dict) and node.get('type') == 'LoadImage':
                total_load_image_nodes += 1
                
                # Solo mostrar info del nodo permitido (ID 97)
                if node.get('id') == ALLOWED_NODE_ID:
                    current_image = "No especificada"
                    if 'widgets_values' in node and len(node['widgets_values']) > 0:
                        current_image = node['widgets_values'][0]
                    
                    target_node_info = {
                        'id': node.get('id'),
                        'pos': node.get('pos'),
                        'current_image': current_image,
                        'type': node.get('type'),
                        'connection': 'Conectado al SimpleFrameGenerator'
                    }
        
        if target_node_info is None:
            return jsonify({"error": f"CRÍTICO: No se encontró el nodo LoadImage ID {ALLOWED_NODE_ID}"}), 500
        
        return jsonify({
            "default_workflow": DEFAULT_WORKFLOW,
            "workflows_folder": WORKFLOWS_FOLDER,
            "total_nodes": len(nodes),
            "total_load_image_nodes": total_load_image_nodes,
            "allowed_node": target_node_info,
            "security_info": f"Solo se permite modificar el nodo ID {ALLOWED_NODE_ID}",
            "blocked_nodes": total_load_image_nodes - 1,
            "last_node_id": workflow.get('last_node_id'),
            "last_link_id": workflow.get('last_link_id')
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo info del workflow: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500


@app.route('/workflows', methods=['GET'])
def list_workflows():
    """Endpoint para listar todos los workflows disponibles."""
    try:
        available_workflows = get_available_workflows()
        
        workflows_info = []
        for workflow_name, workflow_info in available_workflows.items():
            try:
                # Cargar workflow para obtener información básica
                workflow_data = load_workflow(workflow_name)
                
                # Verificar si tiene nodo ID 97
                has_node_97 = False
                node_97_image = "No especificada"
                
                # Verificar en formato API
                if '97' in workflow_data:
                    has_node_97 = True
                    if 'inputs' in workflow_data['97'] and 'image' in workflow_data['97']['inputs']:
                        node_97_image = workflow_data['97']['inputs']['image']
                
                workflows_info.append({
                    'id': workflow_name,
                    'path': workflow_info.get('path', ''),
                    'has_required_node': has_node_97,
                    'current_image_node_97': node_97_image,
                    'total_nodes': len(workflow_data),
                    'status': 'compatible' if has_node_97 else 'incompatible'
                })
                
            except Exception as e:
                workflows_info.append({
                    'id': workflow_name,
                    'path': workflow_info.get('path', ''),
                    'error': str(e),
                    'status': 'error'
                })
        
        return jsonify({
            "available_workflows": workflows_info,
            "total_workflows": len(workflows_info),
            "compatible_workflows": len([w for w in workflows_info if w.get('status') == 'compatible']),
            "required_node_id": 97,
            "workflows_folder": WORKFLOWS_FOLDER
        })
        
    except Exception as e:
        logger.error(f"Error listando workflows: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500


@app.route('/workflow-groups', methods=['GET'])
def get_workflow_groups():
    """Endpoint para obtener workflows agrupados por categorías."""
    try:
        available_workflows = get_available_workflows()
        
        # Agrupar workflows por palabras clave
        groups = {
            "bedroom": [],
            "salon": [],
            "cuadro": [],
            "style": [],
            "all": []
        }
        
        for workflow_id, workflow_path in available_workflows.items():
            groups["all"].append({
                "id": workflow_id,
                "path": workflow_path,
                "name": workflow_id.replace('_', ' ').title()
            })
            
            # Categorizar por palabras clave
            workflow_lower = workflow_id.lower()
            if "bedroom" in workflow_lower:
                groups["bedroom"].append({
                    "id": workflow_id,
                    "path": workflow_path,
                    "name": workflow_id.replace('_', ' ').title()
                })
            if "salon" in workflow_lower:
                groups["salon"].append({
                    "id": workflow_id,
                    "path": workflow_path,
                    "name": workflow_id.replace('_', ' ').title()
                })
            if "cuadro" in workflow_lower:
                groups["cuadro"].append({
                    "id": workflow_id,
                    "path": workflow_path,
                    "name": workflow_id.replace('_', ' ').title()
                })
            if "style" in workflow_lower:
                groups["style"].append({
                    "id": workflow_id,
                    "path": workflow_path,
                    "name": workflow_id.replace('_', ' ').title()
                })
        
        return jsonify({
            "groups": groups,
            "suggested_combinations": {
                "all_bedroom": [w["id"] for w in groups["bedroom"]],
                "all_salon": [w["id"] for w in groups["salon"]],
                "all_cuadro": [w["id"] for w in groups["cuadro"]],
                "all_styles": [w["id"] for w in groups["style"]]
            },
            "total_workflows": len(available_workflows),
            "max_simultaneous": 5
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo grupos de workflows: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500


@app.route('/process-image-multiple', methods=['POST'])
def process_image_multiple():
    """
    Endpoint para procesar una imagen con múltiples workflows simultáneamente.
    Permite generar varias variaciones de la misma imagen usando diferentes estilos.
    """
    try:
        # Verificar que se envió un archivo
        if 'image' not in request.files:
            return jsonify({"error": "No se proporcionó ninguna imagen"}), 400
        
        file = request.files['image']
        
        # Obtener workflows seleccionados (como lista separada por comas)
        workflows_param = request.form.get('workflows', 'default')
        selected_workflows = [w.strip() for w in workflows_param.split(',') if w.strip()]
        
        if not selected_workflows:
            return jsonify({"error": "No se especificaron workflows"}), 400
        
        # BLOQUEAR cualquier intento de especificar target_node_id
        if 'target_node_id' in request.form:
            return jsonify({
                "error": "ACCESO DENEGADO: No se permite especificar target_node_id. Solo se usa el nodo ID 97"
            }), 403
        
        # Verificar que todos los workflows existen
        available_workflows = get_available_workflows()
        invalid_workflows = [w for w in selected_workflows if w not in available_workflows]
        if invalid_workflows:
            return jsonify({
                "error": f"Workflows no encontrados: {invalid_workflows}. Disponibles: {list(available_workflows.keys())}"
            }), 400
        
        # Limitar número máximo de workflows por razones de rendimiento
        max_workflows = 5
        if len(selected_workflows) > max_workflows:
            return jsonify({
                "error": f"Máximo {max_workflows} workflows permitidos por petición. Recibidos: {len(selected_workflows)}"
            }), 400
        
        # Guardar la imagen una sola vez
        image_filename = save_image_from_request(file)
        
        # Verificar estado de ComfyUI antes de iniciar
        try:
            queue_response = requests.get(f"{COMFYUI_URL}/queue", timeout=5)
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                running_queue = queue_data.get('queue_running', [])
                pending_queue = queue_data.get('queue_pending', [])
                
                if running_queue:
                    logger.warning(f"ComfyUI está procesando. Queue running: {len(running_queue)}, pending: {len(pending_queue)}")
                    # Continuar de todos modos, pero dar aviso
                
                logger.info(f"Estado inicial de ComfyUI - Running: {len(running_queue)}, Pending: {len(pending_queue)}")
            else:
                return jsonify({"error": f"ComfyUI no responde: {queue_response.status_code}"}), 500
        except Exception as e:
            return jsonify({"error": f"No se puede conectar con ComfyUI: {e}"}), 500

        # Procesar cada workflow con delay entre envíos
        results = []
        errors = []
        
        for i, workflow_name in enumerate(selected_workflows):
            try:
                logger.info(f"Procesando workflow {i+1}/{len(selected_workflows)}: {workflow_name}")
                
                # Añadir delay entre workflows (excepto el primero)
                if i > 0:
                    time.sleep(2)  # 2 segundos de espera entre envíos
                    logger.info(f"Esperando 2s antes de enviar workflow {workflow_name}...")
                
                # Cargar y actualizar el workflow
                workflow = load_workflow(workflow_name)
                updated_workflow = update_workflow_with_image(workflow, image_filename, None)
                
                # Enviar a ComfyUI
                prompt_id = asyncio.run(submit_workflow_to_comfyui(updated_workflow))
                logger.info(f"Workflow {workflow_name} enviado con prompt_id: {prompt_id}")
                
                # Verificar que el prompt está en la cola
                try:
                    queue_response = requests.get(f"{COMFYUI_URL}/queue", timeout=5)
                    if queue_response.status_code == 200:
                        queue_data = queue_response.json()
                        total_in_queue = len(queue_data.get('queue_pending', [])) + len(queue_data.get('queue_running', []))
                        logger.info(f"Total de workflows en cola después de enviar {workflow_name}: {total_in_queue}")
                except Exception as e:
                    logger.warning(f"No se pudo verificar la cola: {e}")
                
                # Solo añadir a resultados sin esperar a que complete
                results.append({
                    "workflow_name": workflow_name,
                    "workflow_path": available_workflows[workflow_name],
                    "prompt_id": prompt_id,
                    "status": "queued"
                })
                
                logger.info(f"Workflow {workflow_name} añadido a la cola exitosamente")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error enviando workflow {workflow_name}: {error_msg}")
                
                errors.append({
                    "workflow_name": workflow_name,
                    "error": error_msg,
                    "status": "failed"
                })
        
        # Limpiar archivo temporal
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, image_filename))
        except:
            pass
        
        # Preparar respuesta
        total_workflows = len(selected_workflows)
        successful_workflows = len(results)
        failed_workflows = len(errors)
        
        response_data = {
            "success": successful_workflows > 0,
            "total_workflows_requested": total_workflows,
            "successful_workflows": successful_workflows,
            "failed_workflows": failed_workflows,
            "results": results,
            "errors": errors if errors else None,
            "image_filename_used": image_filename,
            "security_note": "Solo se permite modificar el nodo LoadImage ID 97",
            "processing_mode": "queued",
            "note": "Los workflows han sido enviados a la cola de ComfyUI. Use /check-prompt/<prompt_id> para verificar el estado de cada uno."
        }
        
        if successful_workflows == 0:
            response_data["message"] = "Ningún workflow se procesó exitosamente"
            return jsonify(response_data), 500
        elif failed_workflows == 0:
            response_data["message"] = f"Todos los {successful_workflows} workflows se procesaron exitosamente"
        else:
            response_data["message"] = f"{successful_workflows} workflows exitosos, {failed_workflows} fallaron"
        
        return jsonify(response_data)
        
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error procesando múltiples imágenes: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@app.route('/check-prompt/<prompt_id>', methods=['GET'])
def check_prompt_status(prompt_id):
    """Endpoint para verificar el estado de un prompt específico."""
    try:
        response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        
        if response.status_code == 200:
            history = response.json()
            if prompt_id in history:
                prompt_history = history[prompt_id]
                
                status_info = {
                    "prompt_id": prompt_id,
                    "found": True,
                    "completed": 'outputs' in prompt_history,
                    "has_error": False,
                    "error_message": None,
                    "outputs_count": 0
                }
                
                if 'outputs' in prompt_history:
                    outputs = prompt_history['outputs']
                    total_images = 0
                    for node_output in outputs.values():
                        if 'images' in node_output:
                            total_images += len(node_output['images'])
                    status_info["outputs_count"] = total_images
                
                if 'status' in prompt_history and 'error' in prompt_history['status']:
                    status_info["has_error"] = True
                    status_info["error_message"] = prompt_history['status']['error']
                
                return jsonify(status_info)
            else:
                return jsonify({
                    "prompt_id": prompt_id,
                    "found": False,
                    "message": "Prompt no encontrado en historial (puede estar en cola)"
                })
        else:
            return jsonify({
                "prompt_id": prompt_id,
                "error": f"Error consultando ComfyUI: {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error verificando prompt {prompt_id}: {e}")
        return jsonify({
            "prompt_id": prompt_id,
            "error": f"Error de conexión: {str(e)}"
        }), 500


@app.route('/cancel-prompt/<prompt_id>', methods=['POST'])
def cancel_prompt(prompt_id):
    """Cancela un prompt en la cola de ComfyUI."""
    try:
        # Intentar cancelar el prompt en ComfyUI
        response = requests.delete(f"{COMFYUI_URL}/queue", 
                                 json={"delete": [prompt_id]},
                                 timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Prompt {prompt_id} cancelado exitosamente")
            return jsonify({
                "prompt_id": prompt_id,
                "cancelled": True,
                "message": "Prompt cancelado exitosamente"
            })
        else:
            logger.warning(f"No se pudo cancelar prompt {prompt_id}: {response.status_code}")
            return jsonify({
                "prompt_id": prompt_id,
                "cancelled": False,
                "message": f"Error al cancelar: {response.status_code}"
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Error cancelando prompt {prompt_id}: {e}")
        return jsonify({
            "prompt_id": prompt_id,
            "cancelled": False,
            "error": f"Error de conexión: {str(e)}"
        }), 500


@app.route('/check-multiple-prompts', methods=['POST'])
def check_multiple_prompts():
    """Verifica el estado de múltiples prompts y devuelve resultados completos cuando están listos."""
    try:
        data = request.get_json()
        prompt_ids = data.get('prompt_ids', [])
        
        if not prompt_ids:
            return jsonify({"error": "No se proporcionaron prompt_ids"}), 400
        
        results = []
        pending = []
        errors = []
        
        for prompt_id in prompt_ids:
            try:
                # Verificar estado del prompt
                response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
                
                if response.status_code == 200:
                    history_data = response.json()
                    
                    if prompt_id in history_data:
                        prompt_history = history_data[prompt_id]
                        
                        if 'outputs' in prompt_history:
                            # El prompt ha completado
                            output_images = get_output_images(prompt_history['outputs'])
                            results.append({
                                "prompt_id": prompt_id,
                                "status": "completed",
                                "output_images": output_images
                            })
                        else:
                            # El prompt falló
                            error_msg = prompt_history.get('status', {}).get('error', 'Error desconocido')
                            errors.append({
                                "prompt_id": prompt_id,
                                "status": "failed",
                                "error": error_msg
                            })
                    else:
                        # El prompt aún está en cola o procesándose
                        pending.append({
                            "prompt_id": prompt_id,
                            "status": "pending"
                        })
                else:
                    errors.append({
                        "prompt_id": prompt_id,
                        "status": "error",
                        "error": f"Error consultando ComfyUI: {response.status_code}"
                    })
                    
            except Exception as e:
                errors.append({
                    "prompt_id": prompt_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return jsonify({
            "completed": results,
            "pending": pending,
            "errors": errors,
            "summary": {
                "total": len(prompt_ids),
                "completed": len(results),
                "pending": len(pending),
                "failed": len(errors)
            }
        })
        
    except Exception as e:
        logger.error(f"Error verificando múltiples prompts: {e}")
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500


@app.route('/web_client.html')
def serve_web_client():
    """Sirve el cliente web HTML."""
    return send_file('web_client.html')

@app.route('/')
def serve_index():
    """Redirige a la página principal del cliente web."""
    return send_file('web_client.html')


if __name__ == '__main__':
    # Verificar que existan workflows disponibles
    try:
        available_workflows = get_available_workflows()
        logger.info(f"Workflows encontrados: {list(available_workflows.keys())}")
    except Exception as e:
        logger.error(f"No se encontraron workflows: {e}")
        logger.info("Creando workflow por defecto...")
        # Si no hay workflows, verificar al menos que existe el por defecto
        if not os.path.exists(DEFAULT_WORKFLOW):
            logger.error(f"Archivo de workflow por defecto no encontrado: {DEFAULT_WORKFLOW}")
            exit(1)
    
    logger.info(f"Iniciando API REST para ComfyUI")
    logger.info(f"ComfyUI URL: {COMFYUI_URL}")
    logger.info(f"Workflows folder: {WORKFLOWS_FOLDER}")
    logger.info(f"Default workflow: {DEFAULT_WORKFLOW}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('API_PORT', '5000')),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
