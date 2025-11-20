import json
import os
import copy
import random
from config import WORKFLOWS_DIR, WORKFLOW_CONFIG
from utils.logger import log_info
from services.style_service import get_wall_color_for_style, get_depth_intensity_for_style, get_perspective_style_for_style
from style_presets import apply_style_to_workflow, style_forces_text2img

def get_available_workflows():
    workflows = []
    if os.path.exists(WORKFLOWS_DIR):
        for root, dirs, files in os.walk(WORKFLOWS_DIR):
            for filename in files:
                if filename.endswith('.json'):
                    rel_path = os.path.relpath(os.path.join(root, filename), WORKFLOWS_DIR)
                    parts = rel_path.replace('\\', '/').split('/')
                    if len(parts) >= 3:
                        wid = f"{parts[0]}/{parts[1]}/{parts[2].replace('.json','')}"
                        workflows.append({
                            "id": wid, "name": parts[2].replace('.json',''),
                            "room_type": parts[0], "orientation": parts[1],
                            "filename": filename, "path": rel_path
                        })
    return workflows

def filter_workflows_for_batch(batch_config, all_workflows):
    filtered = []
    types = batch_config.get("room_types", [])
    orients = batch_config.get("orientations", [])
    specific = batch_config.get("specific_workflows", [])
    
    for w in all_workflows:
        if specific and w["id"] not in specific: continue
        if types and w["room_type"] not in types: continue
        if orients and w["orientation"] not in orients: continue
        filtered.append(w)
    return filtered

def load_workflow(workflow_name):
    workflow_name = workflow_name.strip()
    paths = []
    if '/' in workflow_name:
        paths.append(os.path.join(WORKFLOWS_DIR, workflow_name + '.json'))
    paths.append(os.path.join(WORKFLOWS_DIR, workflow_name))
    paths.append(os.path.join(WORKFLOWS_DIR, f"{workflow_name}.json"))
    
    final_path = None
    for p in paths:
        if os.path.exists(p):
            final_path = p
            break
    
    if not final_path:
        # Fallback recursivo
        for root, _, files in os.walk(WORKFLOWS_DIR):
            if f"{workflow_name}.json" in files:
                final_path = os.path.join(root, f"{workflow_name}.json")
                break
    
    if not final_path: raise FileNotFoundError(f"Workflow {workflow_name} no encontrado")
    
    with open(final_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_workflow(workflow, image_filename, frame_color='black', style_id='default', style_node_id=None, output_subfolder=None):
    w_copy = copy.deepcopy(workflow)
    force_txt2img = style_forces_text2img(style_id) if style_id and style_id != 'default' else False
    
    # Load Image
    lid = WORKFLOW_CONFIG['load_image_node_id']
    if lid in w_copy: w_copy[lid]['inputs']['image'] = image_filename
    
    # Frame Node
    fid = WORKFLOW_CONFIG['frame_node_id']
    if fid in w_copy:
        node = w_copy[fid]
        defaults = WORKFLOW_CONFIG['frame_node_defaults']
        
        if frame_color == 'none':
            node['inputs']['preset'] = 'black'
            node['inputs']['frame_width'] = 0
        else:
            node['inputs']['preset'] = frame_color
            node['inputs']['frame_width'] = defaults['frame_width']
            
        node['inputs']['wall_color'] = get_wall_color_for_style(style_id)
        node['inputs']['depth_intensity'] = get_depth_intensity_for_style(style_id)
        node['inputs']['perspective_style'] = get_perspective_style_for_style(style_id)
        node['inputs']['depth_enabled'] = True

    # Mode & ControlNet
    if force_txt2img:
        # Lógica para text2img
        for nid, ndata in w_copy.items():
            if isinstance(ndata, dict) and ndata.get('class_type') == 'SeargeOperatingMode':
                ndata['inputs']['workflow_mode'] = 'text-to-image'
            if isinstance(ndata, dict) and ndata.get('class_type') == 'SeargeControlnetAdapterV2':
                ndata['inputs']['strength'] = 0.85
        w_copy = apply_style_to_workflow(w_copy, style_id, style_node_id)
    else:
        # Lógica img2img
        for nid, ndata in w_copy.items():
            if isinstance(ndata, dict) and ndata.get('class_type') == 'SeargeOperatingMode':
                ndata['inputs']['workflow_mode'] = 'image-to-image'
    
    # Subfolder
    if output_subfolder:
        for nid, ndata in w_copy.items():
            if isinstance(ndata, dict) and ndata.get('class_type') == 'SaveImage':
                if 'filename_prefix' in ndata['inputs']:
                    ndata['inputs']['filename_prefix'] = output_subfolder + "/" + ndata['inputs']['filename_prefix']

    # Seeds
    for nid, ndata in w_copy.items():
        if isinstance(ndata, dict) and 'seed' in ndata.get('inputs', {}):
            ndata['inputs']['seed'] = random.randint(1, 2**32-1)
            
    return w_copy