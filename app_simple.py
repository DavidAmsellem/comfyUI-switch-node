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
from image_save_utils import prepare_output_dir, save_generated_image, save_original_to_comfyui_input

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
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=10)
        if response.status_code == 200:
            return jsonify({"status": "ok", "comfyui_connection": "ok", "version": "1.0.0"})
        else:
            return jsonify({"status": "ok", "comfyui_connection": "error", "version": "1.0.0"})
    except:
        return jsonify({"status": "ok", "comfyui_connection": "error", "version": "1.0.0"})

@app.route('/workflows', methods=['GET'])
def list_workflows():
    """Lista workflows disponibles (ahora recursivo en subcarpetas)"""
    workflows = []
    if os.path.exists(WORKFLOWS_FOLDER):
        for root, dirs, files in os.walk(WORKFLOWS_FOLDER):
            for filename in files:
                if filename.endswith('.json'):
                    workflow_id = os.path.splitext(os.path.relpath(os.path.join(root, filename), WORKFLOWS_FOLDER))[0].replace(os.sep, '_')
                    workflows.append({
                        "id": workflow_id,
                        "path": os.path.relpath(os.path.join(root, filename)),
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

def get_comfyui_input_dir():
    """Devuelve la ruta absoluta a la carpeta input de ComfyUI, relativa al directorio actual del backend."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'input'))
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def get_comfyui_output_dir():
    """Devuelve la ruta absoluta a la carpeta output de ComfyUI, relativa al directorio actual del backend."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'output'))
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def save_image_to_comfyui(file):
    """Guarda la imagen en el directorio de ComfyUI/input (ruta portable)"""
    if not file or file.filename == '':
        raise ValueError("No se proporcionó ningún archivo")
    
    if not allowed_file(file.filename):
        raise ValueError(f"Tipo de archivo no permitido")
    
    # Generar nombre único
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    comfyui_input_dir = get_comfyui_input_dir()
    comfyui_path = os.path.join(comfyui_input_dir, unique_filename)
    file.save(comfyui_path)
    
    return unique_filename  # Solo el nombre del archivo, para el workflow

def save_image_to_comfyui_with_path(image_file, relative_path):
    """Guarda la imagen en la ruta relativa a ComfyUI/input, creando subcarpetas si es necesario (ruta portable)"""
    comfyui_input_dir = get_comfyui_input_dir()
    full_path = os.path.join(comfyui_input_dir, *relative_path.replace('\\', '/').split('/'))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    image_file.save(full_path)

def load_workflow(workflow_name):
    """Carga un workflow desde archivo y lo normaliza a dict por ID si es necesario"""
    workflow_path = os.path.join(WORKFLOWS_FOLDER, f"{workflow_name}.json")
    if not os.path.exists(workflow_path):
        raise ValueError(f"Workflow {workflow_name} no encontrado")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    # Si el workflow tiene 'nodes' como lista, convertir a dict por ID
    if isinstance(workflow, dict) and 'nodes' in workflow and isinstance(workflow['nodes'], list):
        nodes_dict = {}
        for node in workflow['nodes']:
            node_id = str(node.get('id'))
            # ComfyUI usa 'type', pero el backend espera 'class_type'
            if 'type' in node and 'class_type' not in node:
                node['class_type'] = node['type']
            nodes_dict[node_id] = node
        workflow = nodes_dict
    return workflow

def update_workflow_for_processing(workflow, image_file):
    """Actualiza el workflow con la imagen y randomiza seeds (versión fija para nodos específicos)"""
    import copy
    workflow_copy = copy.deepcopy(workflow)
    print(f"🔄 Actualizando workflow para procesamiento (nodos fijos)")

    loadimage_node_id = '699'  # Cambia este valor si tu workflow cambia
    if loadimage_node_id in workflow_copy and workflow_copy[loadimage_node_id].get('class_type') == 'LoadImage':
        # Obtener la ruta esperada por el workflow
        expected_path = workflow_copy[loadimage_node_id]['inputs'].get('image', None)
        if expected_path:
            save_image_to_comfyui_with_path(image_file, expected_path)
            workflow_copy[loadimage_node_id]['inputs']['image'] = expected_path
            print(f"✓ Actualizado nodo LoadImage {loadimage_node_id} con imagen: {expected_path}")
        else:
            print(f"⚠️ No se encontró ruta de imagen esperada en el workflow, usando nombre único")
            unique_filename = save_image_to_comfyui(image_file)
            workflow_copy[loadimage_node_id]['inputs']['image'] = unique_filename
    else:
        print(f"⚠️ Nodo LoadImage {loadimage_node_id} no encontrado o no es LoadImage")

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
    response = requests.post(f"{COMFYUI_URL}/prompt", json=prompt_data, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"Error enviando a ComfyUI: {response.status_code} - {response.text}")
    
    result = response.json()
    if 'prompt_id' not in result:
        raise Exception(f"ComfyUI no devolvió prompt_id: {result}")
    
    prompt_id = result['prompt_id']
    print(f"✓ Workflow enviado, prompt_id: {prompt_id}")
    return prompt_id

def wait_for_completion(prompt_id, timeout=1200):
    """Espera a que ComfyUI complete el procesamiento"""
    print(f"Esperando completion para prompt_id: {prompt_id}")
    
    for i in range(timeout):
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30)
            
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
    """Extrae la imagen de salida del nodo SaveImage específico (691) como imagen final"""
    output_images = []
    final_image = None
    save_image_node_id = '691'  # Cambia este valor si tu workflow cambia
    if save_image_node_id in outputs and 'images' in outputs[save_image_node_id]:
        for image_info in outputs[save_image_node_id]['images']:
            if 'filename' in image_info:
                final_image = {
                    'filename': image_info['filename'],
                    'subfolder': image_info.get('subfolder', ''),
                    'type': image_info.get('type', 'output'),
                    'node_id': save_image_node_id,
                    'is_final': True
                }
                break
    if final_image:
        output_images.append(final_image)
        print(f"✓ Imagen final encontrada en nodo SaveImage ({save_image_node_id}): {final_image['filename']}")
    # Agregar otras imágenes si es necesario (opcional)
    return output_images

def upscale_and_save(input_path, output_path, scale=2):
    print(f"[LOG] Upscaling imagen: {input_path} x{scale}")
    img = Image.open(input_path)
    new_size = (img.width * scale, img.height * scale)
    upscaled = img.resize(new_size, Image.LANCZOS)
    upscaled.save(output_path, format='PNG')
    print(f"[LOG] Upscaled {input_path} -> {output_path} ({new_size[0]}x{new_size[1]})")

@app.route('/process-image', methods=['POST'])
def process_image():
    """Procesa una imagen usando un workflow con estilo específico"""
    try:
        print("[LOG] Iniciando endpoint /process-image")
        if 'image' not in request.files:
            print("[ERROR] No se proporcionó ninguna imagen en la petición")
            return jsonify({"error": "No se proporcionó ninguna imagen"}), 400
        file = request.files['image']
        workflow_name = request.form.get('workflow', 'workflow_cuadro_bedroomV15x202')
        print(f"[LOG] Workflow recibido: {workflow_name}")
        # Crear carpeta y guardar imagen original como PNG
        output_dir, original_path, base_name = prepare_output_dir(file)
        print(f"[LOG] Imagen original guardada en: {original_path} (output_dir: {output_dir}, base_name: {base_name})")
        # Upscale automático x4 (manteniendo ambos archivos)
        upscaled_path = os.path.join(output_dir, 'original_upscaled.png')
        upscale_and_save(original_path, upscaled_path, scale=4)
        print(f"[LOG] Imagen original upscaleada guardada en: {upscaled_path}")
        # Guardar también en input de ComfyUI
        comfyui_image_relpath = save_original_to_comfyui_input(file, base_name, COMFYUI_INPUT_FOLDER)
        print(f"[LOG] Imagen original guardada en input ComfyUI: {comfyui_image_relpath}")
        # Usar comfyui_image_relpath como nombre de imagen para el workflow
        workflow = load_workflow(workflow_name)
        print(f"[LOG] Workflow cargado: {workflow_name}")
        updated_workflow = update_workflow_for_processing(workflow, file)
        print(f"[LOG] Workflow actualizado para procesamiento")
        # Enviar a ComfyUI
        prompt_id = submit_to_comfyui(updated_workflow)
        print(f"[LOG] Prompt enviado a ComfyUI, prompt_id: {prompt_id}")
        # Esperar resultados
        outputs = wait_for_completion(prompt_id)
        print(f"[LOG] Resultados recibidos de ComfyUI para prompt_id: {prompt_id}")
        # Extraer imágenes
        output_images = extract_output_images(outputs)
        print(f"[LOG] Imágenes extraídas: {output_images}")
        # Guardar cada imagen generada en output_dir como PNG
        for img in output_images:
            # Usar ruta portable para output de ComfyUI
            comfyui_output_folder = get_comfyui_output_dir()
            subfolder = img.get('subfolder', '').strip('/\\')
            if subfolder:
                comfyui_img_path = os.path.join(comfyui_output_folder, subfolder, img['filename'])
            else:
                comfyui_img_path = os.path.join(comfyui_output_folder, img['filename'])
            print(f"[DEBUG] Buscando imagen generada en output: {comfyui_img_path}")
            if os.path.exists(comfyui_img_path):
                print(f"[DEBUG] Imagen encontrada, guardando en: {output_dir}")
                with open(comfyui_img_path, 'rb') as f:
                    img_bytes = f.read()
                # Guardar SIEMPRE en la subcarpeta outputs/<base_name>/
                save_generated_image(img_bytes, output_dir, img['filename'])
                print(f"[LOG] Imagen generada guardada en: {os.path.join(output_dir, img['filename'])}")
            else:
                print(f"[ERROR] Imagen NO encontrada en output: {subfolder}/{img['filename']}")
        # Limpiar archivo temporal si existe
        # temp_path = os.path.join(UPLOAD_FOLDER, image_filename)
        # if os.path.exists(temp_path):
        #     os.remove(temp_path)
        
        print(f"[LOG] Procesamiento completado! {len(output_images)} imágenes generadas")
        
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
            # Añadir la URL de descarga
            response_data["final_image_url"] = f"/get-image/{final_image['filename']}?subfolder={final_image.get('subfolder','')}&type={final_image.get('type','output')}"
            response_data["message"] += f" (imagen final: {final_image['filename']})"
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
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
        # Crear carpeta y guardar imagen original como PNG
        output_dir, original_path, base_name = prepare_output_dir(file)
        print(f"✓ Imagen original guardada en: {original_path}")
        # Guardar también en input de ComfyUI
        comfyui_image_relpath = save_original_to_comfyui_input(file, base_name, COMFYUI_INPUT_FOLDER)
        print(f"✓ Imagen original guardada en input ComfyUI: {comfyui_image_relpath}")
        results = []
        errors = []
        for workflow_name in workflow_names:
            try:
                print(f"🎨 Procesando con workflow: {workflow_name}")
                workflow = load_workflow(workflow_name)
                updated_workflow = update_workflow_for_processing(workflow, file)
                prompt_id = submit_to_comfyui(updated_workflow)
                outputs = wait_for_completion(prompt_id)
                output_images = extract_output_images(outputs)
                for img in output_images:
                    comfyui_output_folder = get_comfyui_output_dir()
                    comfyui_img_path = os.path.join(comfyui_output_folder, img.get('subfolder', ''), img['filename'])
                    print(f"[DEBUG] Buscando imagen generada en output: {comfyui_img_path}")
                    if os.path.exists(comfyui_img_path):
                        print(f"[DEBUG] Imagen encontrada, guardando en: {output_dir}")
                        with open(comfyui_img_path, 'rb') as f:
                            img_bytes = f.read()
                        # Guardar en subcarpeta con el nombre base del archivo original (para múltiples workflows)
                        save_generated_image(img_bytes, output_dir, img['filename'], force_base_name=base_name)
                    else:
                        print(f"[DEBUG] Imagen NO encontrada en output: {img['filename']}")
                results.append({
                    "workflow": workflow_name,
                    "prompt_id": prompt_id,
                    "output_images": output_images,
                    "success": True
                })
                print(f"✅ {workflow_name} completado con {len(output_images)} imágenes")
            except Exception as e:
                print(f"❌ Error en {workflow_name}: {str(e)}")
                errors.append({"workflow": workflow_name, "error": str(e)})
        return jsonify({
            "success": len(results) > 0,
            "results": results,
            "errors": errors,
            "output_dir": output_dir
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-image/<filename>', methods=['GET'])
def get_image(filename):
    """Descarga una imagen generada desde outputs/<base_name>/"""
    try:
        base_name = request.args.get('base_name', None)
        if not base_name:
            return jsonify({'error': 'Parámetro base_name requerido'}), 400
        # Sanitizar filename y base_name
        filename = secure_filename(filename)
        base_name = secure_filename(base_name)
        output_dir = os.path.join('outputs', base_name)
        image_path = os.path.join(output_dir, filename)
        # Prevenir path traversal
        abs_outputs = os.path.abspath('outputs')
        abs_image_path = os.path.abspath(image_path)
        if not abs_image_path.startswith(abs_outputs):
            return jsonify({'error': 'Ruta no permitida'}), 403
        if not os.path.exists(abs_image_path):
            return jsonify({'error': 'Archivo no encontrado'}), 404
        return send_file(abs_image_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def serve_client():
    """Sirve el cliente web"""
    return send_file('web_client.html')

@app.route('/workflow-groups', methods=['GET'])
def get_workflow_groups():
    """Obtiene workflows agrupados por dimensiones, tipo, orientación y subcarpetas (estructura recursiva)"""
    try:
        import re
        groups = {}
        # Recorrer recursivamente todas las subcarpetas
        for root, dirs, files in os.walk(WORKFLOWS_FOLDER):
            for filename in files:
                if filename.endswith('.json'):
                    rel_dir = os.path.relpath(root, WORKFLOWS_FOLDER)
                    rel_path = os.path.join(rel_dir, filename) if rel_dir != '.' else filename
                    # Extraer tipo
                    tipo = None
                    for t in ['bedroom', 'salon', 'bathroom', 'office']:
                        if t in filename.lower() or t in rel_dir.lower():
                            tipo = t
                            break
                    if not tipo:
                        continue
                    # Extraer dimensiones
                    dimension_match = re.search(r'(\d+x\d+)', rel_path)
                    if not dimension_match:
                        dimension_match = re.search(r'V?(\d+x\d+)', filename)
                    if not dimension_match:
                        continue
                    dimension = dimension_match.group(1)
                    group_key = f"{tipo}-{dimension}"
                    if group_key not in groups:
                        groups[group_key] = {
                            'name': f'{tipo.title()} {dimension}',
                            'dimension': dimension,
                            'type': tipo,
                            'workflows': []
                        }
                    # Extraer estilo
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
                    elif 'modern' in filename.lower():
                        style = 'modern'
                    elif 'beach' in filename.lower():
                        style = 'beach'
                    elif 'close' in filename.lower():
                        style = 'close'
                    # Extraer orientación
                    orientation = 'vertical'
                    if re.search(r'[-_H]60x80', filename) or 'horizontal' in filename.lower() or re.search(r'-H', filename):
                        orientation = 'horizontal'
                    elif re.search(r'[-_V]60x80', filename) or 'vertical' in filename.lower() or re.search(r'-V', filename):
                        orientation = 'vertical'
                    # Guardar subcarpeta relativa
                    subfolder = rel_dir if rel_dir != '.' else ''
                    # Añadir workflow
                    groups[group_key]['workflows'].append({
                        'filename': rel_path.replace('.json', ''),
                        'style': style,
                        'orientation': orientation,
                        'subfolder': subfolder,
                        'display_name': f'{tipo.title()} {style.title()} {dimension} ({orientation})',
                    })
        # Agrupar por orientación dentro de cada grupo
        for group in groups.values():
            orient_dict = {'vertical': [], 'horizontal': []}
            for wf in group['workflows']:
                orient_dict[wf['orientation']].append(wf)
            group['by_orientation'] = orient_dict
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
        output_dir, _, _ = prepare_output_dir(file)  # Asegura que output_dir esté definido
        
        for i, workflow_name in enumerate(workflows):
            try:
                print(f"🔄 Procesando workflow {i+1}/{len(workflows)}: {workflow_name}")
                
                # Cargar workflow
                workflow = load_workflow(workflow_name)
                print(f"✓ Workflow cargado: {len(workflow)} nodos")
                
                # Actualizar workflow (incluye imagen y seeds aleatorios)
                updated_workflow = update_workflow_for_processing(workflow, file)
                # Enviar a ComfyUI
                prompt_id = submit_to_comfyui(updated_workflow)
                # Esperar resultados
                outputs = wait_for_completion(prompt_id)
                # Extraer imágenes
                output_images = extract_output_images(outputs)
                # Guardar cada imagen generada en output_dir como PNG
                for img in output_images:
                    # Usar ruta portable para output, incluyendo subfolder si existe (sanitizado)
                    comfyui_output_folder = get_comfyui_output_dir()
                    subfolder = img.get('subfolder', '').strip('/\\')  # Elimina cualquier / o \\ al inicio/fin
                    if subfolder:
                        comfyui_img_path = os.path.join(comfyui_output_folder, subfolder, img['filename'])
                    else:
                        comfyui_img_path = os.path.join(comfyui_output_folder, img['filename'])
                    print(f"[DEBUG] Buscando imagen generada en output: {comfyui_img_path}")
                    if os.path.exists(comfyui_img_path):
                        print(f"[DEBUG] Imagen encontrada, guardando en: {output_dir}")
                        with open(comfyui_img_path, 'rb') as f:
                            img_bytes = f.read()
                        # Guardar SIEMPRE en la subcarpeta outputs/<base_name>/
                        save_generated_image(img_bytes, output_dir, img['filename'])
                    else:
                        print(f"[DEBUG] Imagen NO encontrada en output: {img['filename']}")
                # Limpiar archivo temporal si existe
                # temp_path = os.path.join(UPLOAD_FOLDER, image_filename)
                # if os.path.exists(temp_path):
                #     os.remove(temp_path)
                
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
                    # Añadir la URL de descarga
                    response_data["final_image_url"] = f"/get-image/{final_image['filename']}?subfolder={final_image.get('subfolder','')}&type={final_image.get('type','output')}"
                    response_data["message"] += f" (imagen final: {final_image['filename']})"
                
                results.append(response_data)
                print(f"✓ Workflow {workflow_name} procesado exitosamente")
            except Exception as e:
                error_msg = f"Error procesando {workflow_name}: {str(e)}"
                print(f"❌ {error_msg}")
                failed_workflows.append({
                    'workflow': workflow_name,
                    'error': error_msg
                })
        
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
                workflow = update_workflow_for_processing(workflow, file)
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
        outputs = wait_for_completion(prompt_id, timeout=30)  # timeout más largo para polling en desarrollo
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