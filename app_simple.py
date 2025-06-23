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

def update_workflow_for_processing(workflow, image_filename):
    """Actualiza el workflow con la imagen y randomiza seeds"""
    import copy
    
    workflow_copy = copy.deepcopy(workflow)
    
    print(f"🔄 Actualizando workflow para procesamiento")
    
    # Actualizar nodo 97 (imagen)
    if "97" in workflow_copy:
        if 'inputs' not in workflow_copy["97"]:
            workflow_copy["97"]['inputs'] = {}
        workflow_copy["97"]['inputs']['image'] = image_filename
        print(f"✓ Actualizado nodo 97 con imagen: {image_filename}")
    
    # Randomizar todos los seeds para mayor variabilidad
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
    """Extrae las imágenes de salida, priorizando el nodo 143 (imagen final)"""
    output_images = []
    final_image = None
    
    # Primero buscar el nodo 143 (imagen final)
    if '143' in outputs and 'images' in outputs['143']:
        for image_info in outputs['143']['images']:
            if 'filename' in image_info:
                final_image = {
                    'filename': image_info['filename'],
                    'subfolder': image_info.get('subfolder', ''),
                    'type': image_info.get('type', 'output'),
                    'node_id': '143',
                    'is_final': True
                }
                break
    
    # Si encontramos la imagen final, la ponemos primera
    if final_image:
        output_images.append(final_image)
        print(f"✓ Imagen final encontrada en nodo 143: {final_image['filename']}")
    
    # Luego agregar otras imágenes (excluyendo nodo 143 para evitar duplicados)
    for node_id, node_output in outputs.items():
        if node_id == '143':  # Ya procesamos este nodo
            continue
            
        if 'images' in node_output:
            for image_info in node_output['images']:
                if 'filename' in image_info:
                    output_images.append({
                        'filename': image_info['filename'],
                        'subfolder': image_info.get('subfolder', ''),
                        'type': image_info.get('type', 'output'),
                        'node_id': node_id,
                        'is_final': False
                    })
    
    print(f"✓ Total de imágenes extraídas: {len(output_images)} (final: {'Sí' if final_image else 'No'})")
    return output_images

@app.route('/process-image', methods=['POST'])
def process_image():
    """Procesa una imagen usando un workflow con estilo específico"""
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
        
        # Actualizar workflow (incluye imagen y seeds aleatorios)
        updated_workflow = update_workflow_for_processing(workflow, image_filename)
        
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
        
        # Identificar imagen final
        final_image = next((img for img in output_images if img.get('is_final')), None)
        
        response_data = {
            "success": True,
            "prompt_id": prompt_id,
            "workflow_used": workflow_name,
            "output_images": output_images,
            "total_images": len(output_images),
            "message": f"Imagen procesada exitosamente - {len(output_images)} resultados"
        }
        
        if final_image:
            response_data["final_image"] = final_image
            response_data["message"] += f" (imagen final: {final_image['filename']})"
        
        return jsonify(response_data)
        
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
                
                # Actualizar workflow (incluye imagen y seeds aleatorios)
                updated_workflow = update_workflow_for_processing(workflow, image_filename)
                
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

@app.route('/workflow-groups', methods=['GET'])
def get_workflow_groups():
    """Obtiene workflows agrupados por dimensiones y tipo"""
    try:
        groups = {}
        
        # Buscar en carpeta workflows
        if os.path.exists(WORKFLOWS_FOLDER):
            for filename in os.listdir(WORKFLOWS_FOLDER):
                if filename.endswith('.json'):
                    # Extraer información del nombre del archivo
                    if 'bedroom' in filename.lower():
                        # Extraer dimensiones del nombre
                        import re
                        dimension_match = re.search(r'V?(\d+x\d+)', filename)
                        if dimension_match:
                            dimension = dimension_match.group(1)
                            group_key = f"bedroom-{dimension}"
                            
                            if group_key not in groups:
                                groups[group_key] = {
                                    'name': f'Bedroom {dimension}',
                                    'dimension': dimension,
                                    'type': 'bedroom',
                                    'workflows': []
                                }
                            
                            # Extraer estilo del nombre
                            style = 'default'
                            if 'artistic' in filename.lower():
                                style = 'artistic'
                            elif 'classic' in filename.lower():
                                style = 'classic'
                            elif 'minimalism' in filename.lower():
                                style = 'minimalism'
                            elif 'scandinavian' in filename.lower():
                                style = 'scandinavian'
                            elif 'arquitecture' in filename.lower():
                                style = 'arquitecture'
                            elif 'minimalamp' in filename.lower():
                                style = 'minimalamp'
                            elif 'student' in filename.lower():
                                style = 'student'
                            elif 'wood' in filename.lower():
                                style = 'wood'
                            
                            groups[group_key]['workflows'].append({
                                'filename': filename.replace('.json', ''),
                                'style': style,
                                'display_name': f'Bedroom {style.title()} {dimension}'
                            })
        
        # Buscar en subcarpetas
        for subdir in os.listdir(WORKFLOWS_FOLDER):
            subdir_path = os.path.join(WORKFLOWS_FOLDER, subdir)
            if os.path.isdir(subdir_path):
                for filename in os.listdir(subdir_path):
                    if filename.endswith('.json') and 'bedroom' in filename.lower():
                        # Extraer dimensiones del nombre de carpeta o archivo
                        import re
                        dimension_match = re.search(r'(\d+x\d+)', subdir)
                        if not dimension_match:
                            dimension_match = re.search(r'V?(\d+x\d+)', filename)
                        
                        if dimension_match:
                            dimension = dimension_match.group(1)
                            group_key = f"bedroom-{dimension}"
                            
                            if group_key not in groups:
                                groups[group_key] = {
                                    'name': f'Bedroom {dimension}',
                                    'dimension': dimension,
                                    'type': 'bedroom',
                                    'workflows': []
                                }
                            
                            # Extraer estilo del nombre
                            style = 'default'
                            if 'artistic' in filename.lower():
                                style = 'artistic'
                            elif 'classic' in filename.lower():
                                style = 'classic'
                            elif 'minimalism' in filename.lower():
                                style = 'minimalism'
                            elif 'scandinavian' in filename.lower():
                                style = 'scandinavian'
                            elif 'arquitecture' in filename.lower():
                                style = 'arquitecture'
                            elif 'minimalamp' in filename.lower():
                                style = 'minimalamp'
                            elif 'student' in filename.lower():
                                style = 'student'
                            elif 'wood' in filename.lower():
                                style = 'wood'
                            
                            workflow_path = f"{subdir}/{filename.replace('.json', '')}"
                            groups[group_key]['workflows'].append({
                                'filename': workflow_path,
                                'style': style,
                                'display_name': f'Bedroom {style.title()} {dimension}'
                            })
        
        print(f"✓ Grupos de workflows encontrados: {list(groups.keys())}")
        return jsonify({"success": True, "groups": groups})
        
    except Exception as e:
        print(f"❌ Error obteniendo grupos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process-multiple-workflows', methods=['POST'])
def process_multiple_workflows():
    """Procesa una imagen con múltiples workflows en cola"""
    try:
        # Verificar que se envió un archivo
        if 'image' not in request.files:
            return jsonify({"error": "No se proporcionó ninguna imagen"}), 400
        
        file = request.files['image']
        workflows_param = request.form.get('workflows', '')
        
        if not workflows_param:
            return jsonify({"error": "No se especificaron workflows"}), 400
        
        # Parsear lista de workflows
        try:
            import json
            workflows = json.loads(workflows_param)
        except:
            workflows = workflows_param.split(',')
        
        print(f"🔄 Procesando imagen con {len(workflows)} workflows: {workflows}")
        
        # Guardar imagen una sola vez
        image_filename = save_image_to_comfyui(file)
        print(f"✓ Imagen guardada: {image_filename}")
        
        results = []
        failed_workflows = []
        
        for i, workflow_name in enumerate(workflows):
            try:
                print(f"🔄 Procesando workflow {i+1}/{len(workflows)}: {workflow_name}")
                
                # Cargar workflow
                workflow = load_workflow(workflow_name)
                print(f"✓ Workflow cargado: {len(workflow)} nodos")
                
                # Actualizar workflow con la imagen y randomizar seeds
                workflow = update_workflow_for_processing(workflow, image_filename)
                
                print(f"Enviando workflow a ComfyUI...")
                
                # Enviar a ComfyUI
                response = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
                
                if response.status_code != 200:
                    error_msg = f"Error enviando a ComfyUI: {response.status_code} - {response.text}"
                    print(f"❌ {error_msg}")
                    failed_workflows.append({
                        'workflow': workflow_name,
                        'error': error_msg
                    })
                    continue
                
                result = response.json()
                prompt_id = result['prompt_id']
                print(f"✓ Prompt enviado con ID: {prompt_id}")
                
                # Esperar resultados
                print("⏳ Esperando procesamiento...")
                outputs = wait_for_completion(prompt_id)
                
                if outputs:
                    output_images = extract_output_images(outputs)
                    print(f"✓ Workflow {workflow_name} completado: {len(output_images)} imágenes")
                    
                    results.append({
                        "workflow_name": workflow_name,
                        "prompt_id": prompt_id,
                        "output_images": output_images,
                        "success": True,
                        "order": i + 1
                    })
                else:
                    error_msg = f"Timeout o error en procesamiento"
                    print(f"❌ {error_msg}")
                    failed_workflows.append({
                        'workflow': workflow_name,
                        'error': error_msg
                    })
                
            except Exception as e:
                error_msg = f"Error procesando {workflow_name}: {str(e)}"
                print(f"❌ {error_msg}")
                failed_workflows.append({
                    'workflow': workflow_name,
                    'error': error_msg
                })
        
        # Limpiar imagen temporal
        cleanup_temp_image(image_filename)
        
        response_data = {
            "success": len(results) > 0,
            "total_workflows": len(workflows),
            "successful": len(results),
            "failed": len(failed_workflows),
            "results": results,
            "failed_workflows": failed_workflows,
            "message": f"Procesados {len(results)}/{len(workflows)} workflows exitosamente"
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process-multiple-workflows-async', methods=['POST'])
def process_multiple_workflows_async():
    """Procesa una imagen con múltiples workflows en modo asíncrono (solo envía, no espera resultados)"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No se proporcionó ninguna imagen"}), 400
        file = request.files['image']
        workflows_param = request.form.get('workflows', '')
        if not workflows_param:
            return jsonify({"error": "No se especificaron workflows"}), 400
        try:
            import json
            workflows = json.loads(workflows_param)
        except:
            workflows = workflows_param.split(',')
        print(f"🔄 Procesando imagen con {len(workflows)} workflows (async): {workflows}")
        image_filename = save_image_to_comfyui(file)
        print(f"✓ Imagen guardada: {image_filename}")
        prompt_ids = []
        workflow_names = []
        for i, workflow_name in enumerate(workflows):
            try:
                print(f"🔄 Enviando workflow {i+1}/{len(workflows)}: {workflow_name}")
                workflow = load_workflow(workflow_name)
                workflow = update_workflow_for_processing(workflow, image_filename)
                response = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
                if response.status_code != 200:
                    print(f"❌ Error enviando a ComfyUI: {response.status_code} - {response.text}")
                    continue
                result = response.json()
                prompt_id = result['prompt_id']
                prompt_ids.append(prompt_id)
                workflow_names.append(workflow_name)
                print(f"✓ Prompt enviado con ID: {prompt_id}")
            except Exception as e:
                print(f"❌ Error procesando {workflow_name}: {str(e)}")
                continue
        cleanup_temp_image(image_filename)
        response_data = {
            "success": len(prompt_ids) > 0,
            "prompt_ids": prompt_ids,
            "workflow_names": workflow_names,
            "message": f"{len(prompt_ids)}/{len(workflows)} workflows enviados a la cola de ComfyUI",
            "processing_mode": "queued"
        }
        return jsonify(response_data)
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-result/<prompt_id>', methods=['GET'])
def get_result(prompt_id):
    """Devuelve el resultado de un prompt_id si está listo"""
    try:
        outputs = wait_for_completion(prompt_id, timeout=1)  # timeout corto para polling
        if outputs:
            output_images = extract_output_images(outputs)
            return jsonify({
                "success": True,
                "output_images": output_images,
                "prompt_id": prompt_id
            })
        else:
            return jsonify({"success": False, "message": "Aún no disponible"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def cleanup_temp_image(image_filename):
    """Elimina la imagen temporal del directorio de uploads si existe"""
    try:
        path = os.path.join(UPLOAD_FOLDER, image_filename)
        if os.path.exists(path):
            os.remove(path)
            print(f"🧹 Imagen temporal eliminada: {path}")
    except Exception as e:
        print(f"⚠️ Error eliminando imagen temporal: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)