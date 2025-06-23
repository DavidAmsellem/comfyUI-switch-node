#!/usr/bin/env python3
"""
API REST SIMPLIFICADA para ComfyUI
"""

import os
import json
import uuid
import time
import random
import shutil
from io import BytesIO
from typing import Dict, Any

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import requests
from werkzeug.utils import secure_filename

# Configuración
app = Flask(__name__)
CORS(app)

# Configuración de ComfyUI
COMFYUI_HOST = os.getenv('COMFYUI_HOST', 'localhost')
COMFYUI_PORT = os.getenv('COMFYUI_PORT', '8188')
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

# Directorios
UPLOAD_FOLDER = 'temp_uploads'
WORKFLOWS_FOLDER = 'workflows'
COMFYUI_INPUT_FOLDER = '/media/davidadmin/Nuevo vol/comfyUI/ComfyUI/input'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Crear directorios
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "ok", "comfyui_connection": "ok", "version": "1.0.0"})
        else:
            return jsonify({"status": "ok", "comfyui_connection": "error", "version": "1.0.0"})
    except:
        return jsonify({"status": "ok", "comfyui_connection": "error", "version": "1.0.0"})

@app.route('/workflows', methods=['GET'])
def list_workflows():
    """Lista workflows disponibles"""
    workflows = []
    
    if os.path.exists(WORKFLOWS_FOLDER):
        for filename in os.listdir(WORKFLOWS_FOLDER):
            if filename.endswith('.json'):
                workflow_id = filename.replace('.json', '')
                workflows.append({
                    "id": workflow_id,
                    "path": f"workflows/{filename}",
                    "status": "compatible",
                    "has_required_node": True,
                    "total_nodes": 0,
                    "current_image_node_97": "example.png"
                })
    
    return jsonify({
        "available_workflows": workflows,
        "total_workflows": len(workflows),
        "compatible_workflows": len(workflows),
        "required_node_id": 97,
        "workflows_folder": WORKFLOWS_FOLDER
    })

def save_image_to_comfyui(file):
    """Guarda la imagen en el directorio de ComfyUI"""
    if not file or file.filename == '':
        raise ValueError("No se proporcionó ningún archivo")
    
    if not allowed_file(file.filename):
        raise ValueError(f"Tipo de archivo no permitido")
    
    # Generar nombre único
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Guardar en el directorio de ComfyUI
    comfyui_path = os.path.join(COMFYUI_INPUT_FOLDER, unique_filename)
    file.save(comfyui_path)
    
    return unique_filename

def load_workflow(workflow_name):
    """Carga un workflow desde archivo"""
    workflow_path = os.path.join(WORKFLOWS_FOLDER, f"{workflow_name}.json")
    
    if not os.path.exists(workflow_path):
        raise ValueError(f"Workflow {workflow_name} no encontrado")
    
    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_workflow_image_and_seeds(workflow, image_filename):
    """Actualiza el nodo 97 con la nueva imagen y randomiza seeds"""
    import copy
    workflow_copy = copy.deepcopy(workflow)
    
    # Actualizar nodo 97 con la nueva imagen
    if "97" in workflow_copy:
        if 'inputs' not in workflow_copy["97"]:
            workflow_copy["97"]['inputs'] = {}
        workflow_copy["97"]['inputs']['image'] = image_filename
        print(f"✓ Actualizado nodo 97 con imagen: {image_filename}")
    else:
        raise ValueError("No se encontró el nodo 97 en el workflow")
    
    # Randomizar seeds para generar imágenes diferentes
    for node_id, node_data in workflow_copy.items():
        if isinstance(node_data, dict) and 'inputs' in node_data:
            inputs = node_data['inputs']
            if 'seed' in inputs:
                old_seed = inputs['seed']
                new_seed = random.randint(1, 2**32-1)
                inputs['seed'] = new_seed
                print(f"✓ Randomizado seed en nodo {node_id}: {old_seed} → {new_seed}")
    
    return workflow_copy

def submit_to_comfyui(workflow):
    """Envía el workflow a ComfyUI"""
    client_id = str(uuid.uuid4())
    
    prompt_data = {
        "prompt": workflow,
        "client_id": client_id
    }
    
    print(f"Enviando workflow a ComfyUI...")
    response = requests.post(f"{COMFYUI_URL}/prompt", json=prompt_data, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Error enviando a ComfyUI: {response.status_code} - {response.text}")
    
    result = response.json()
    if 'prompt_id' not in result:
        raise Exception(f"ComfyUI no devolvió prompt_id: {result}")
    
    prompt_id = result['prompt_id']
    print(f"✓ Workflow enviado, prompt_id: {prompt_id}")
    return prompt_id

def wait_for_completion(prompt_id, timeout=300):
    """Espera a que ComfyUI complete el procesamiento"""
    print(f"Esperando completion para prompt_id: {prompt_id}")
    
    for i in range(timeout):
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    
                    if 'outputs' in prompt_history:
                        print(f"✓ Procesamiento completado!")
                        return prompt_history['outputs']
                    
                    if 'status' in prompt_history and 'error' in prompt_history['status']:
                        raise Exception(f"Error en ComfyUI: {prompt_history['status']['error']}")
            
            if i % 10 == 0 and i > 0:
                print(f"Esperando... {i}/{timeout} segundos")
            
            time.sleep(1)
            
        except requests.exceptions.RequestException:
            time.sleep(1)
            continue
    
    raise Exception(f"Timeout esperando completion después de {timeout} segundos")

def extract_output_images(outputs):
    """Extrae las imágenes de salida"""
    output_images = []
    
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            for image_info in node_output['images']:
                if 'filename' in image_info:
                    output_images.append({
                        'filename': image_info['filename'],
                        'subfolder': image_info.get('subfolder', ''),
                        'type': image_info.get('type', 'output'),
                        'node_id': node_id
                    })
    
    return output_images

@app.route('/process-image', methods=['POST'])
def process_image():
    """Procesa una imagen usando un workflow"""
    try:
        # Verificar que se envió un archivo
        if 'image' not in request.files:
            return jsonify({"error": "No se proporcionó ninguna imagen"}), 400
        
        file = request.files['image']
        workflow_name = request.form.get('workflow', 'workflow_cuadro_bedroomV15x202')
        
        print(f"🔄 Procesando imagen con workflow: {workflow_name}")
        
        # Guardar imagen en ComfyUI
        image_filename = save_image_to_comfyui(file)
        print(f"✓ Imagen guardada: {image_filename}")
        
        # Cargar workflow
        workflow = load_workflow(workflow_name)
        print(f"✓ Workflow cargado: {len(workflow)} nodos")
        
        # Actualizar workflow con nueva imagen y seeds aleatorios
        updated_workflow = update_workflow_image_and_seeds(workflow, image_filename)
        
        # Enviar a ComfyUI
        prompt_id = submit_to_comfyui(updated_workflow)
        
        # Esperar resultados
        outputs = wait_for_completion(prompt_id)
        
        # Extraer imágenes
        output_images = extract_output_images(outputs)
        
        # Limpiar archivo temporal si existe
        temp_path = os.path.join(UPLOAD_FOLDER, image_filename)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        print(f"✅ Procesamiento completado! {len(output_images)} imágenes generadas")
        
        return jsonify({
            "success": True,
            "prompt_id": prompt_id,
            "workflow_used": workflow_name,
            "output_images": output_images,
            "message": f"Imagen procesada exitosamente con {len(output_images)} resultados"
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process-image-multiple', methods=['POST'])
def process_image_multiple():
    """Procesa una imagen usando múltiples workflows"""
    try:
        # Verificar que se envió un archivo
        if 'image' not in request.files:
            return jsonify({"error": "No se proporcionó ninguna imagen"}), 400
        
        file = request.files['image']
        workflows_param = request.form.get('workflows', '')
        
        if not workflows_param:
            return jsonify({"error": "No se especificaron workflows"}), 400
        
        try:
            workflow_names = json.loads(workflows_param)
        except:
            return jsonify({"error": "Formato de workflows inválido"}), 400
        
        if len(workflow_names) > 5:
            return jsonify({"error": "Máximo 5 workflows permitidos"}), 400
        
        print(f"🔄 Procesando imagen con {len(workflow_names)} workflows: {workflow_names}")
        
        # Guardar imagen en ComfyUI
        image_filename = save_image_to_comfyui(file)
        print(f"✓ Imagen guardada: {image_filename}")
        
        results = []
        errors = []
        
        for workflow_name in workflow_names:
            try:
                print(f"🎨 Procesando con workflow: {workflow_name}")
                
                # Cargar workflow
                workflow = load_workflow(workflow_name)
                
                # Actualizar workflow
                updated_workflow = update_workflow_image_and_seeds(workflow, image_filename)
                
                # Enviar a ComfyUI
                prompt_id = submit_to_comfyui(updated_workflow)
                
                # Esperar resultados
                outputs = wait_for_completion(prompt_id)
                
                # Extraer imágenes
                output_images = extract_output_images(outputs)
                
                results.append({
                    "workflow": workflow_name,
                    "prompt_id": prompt_id,
                    "output_images": output_images,
                    "success": True
                })
                
                print(f"✅ {workflow_name} completado con {len(output_images)} imágenes")
                
            except Exception as e:
                print(f"❌ Error en {workflow_name}: {str(e)}")
                errors.append({
                    "workflow": workflow_name,
                    "error": str(e)
                })
        
        # Limpiar archivo temporal
        temp_path = os.path.join(UPLOAD_FOLDER, image_filename)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        print(f"🏁 Procesamiento múltiple completado: {len(results)} exitosos, {len(errors)} errores")
        
        return jsonify({
            "success": True,
            "total_workflows": len(workflow_names),
            "successful_results": results,
            "errors": errors,
            "summary": {
                "successful": len(results),
                "failed": len(errors),
                "total_images": sum(len(r["output_images"]) for r in results)
            }
        })
        
    except Exception as e:
        print(f"❌ Error en procesamiento múltiple: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-image/<filename>', methods=['GET'])
def get_image(filename):
    """Descarga una imagen generada"""
    try:
        subfolder = request.args.get('subfolder', '')
        image_type = request.args.get('type', 'output')
        
        params = {
            'filename': filename,
            'subfolder': subfolder,
            'type': image_type
        }
        
        response = requests.get(f"{COMFYUI_URL}/view", params=params)
        
        if response.status_code != 200:
            return jsonify({"error": "Imagen no encontrada"}), 404
        
        img_io = BytesIO(response.content)
        img_io.seek(0)
        
        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve_client():
    """Sirve el cliente web"""
    return send_file('web_client.html')

if __name__ == '__main__':
    print("🚀 Iniciando API REST simplificada para ComfyUI")
    print(f"ComfyUI URL: {COMFYUI_URL}")
    print(f"Workflows folder: {WORKFLOWS_FOLDER}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('API_PORT', '5000')),
        debug=True
    )