from flask import Blueprint, jsonify, send_file
from datetime import datetime
import os
import requests
from config import COMFYUI_URL, WORKFLOW_CONFIG
from style_presets import get_available_styles
from services.workflow_service import load_workflow, get_available_workflows
from services import comfy_service  # Importamos el servicio para el status

general_bp = Blueprint('general_routes', __name__)

@general_bp.route('/health', methods=['GET'])
def health_check():
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        comfyui_status = "ok" if response.status_code == 200 else "error"
    except: comfyui_status = "error"
    return jsonify({"status": "ok", "comfyui_connection": comfyui_status, "timestamp": datetime.now().isoformat()})

@general_bp.route('/system-status', methods=['GET'])
def system_status():
    """Devuelve el estado detallado de ComfyUI (Cola, Idle, Offline)"""
    status = comfy_service.get_system_status()
    return jsonify(status)

@general_bp.route('/styles', methods=['GET'])
def list_styles():
    return jsonify({
        "styles": get_available_styles(),
        "total": len(get_available_styles()),
        "message": "Estilos cargados correctamente"
    })

@general_bp.route('/workflows', methods=['GET'])
def list_workflows():
    """Lista workflows disponibles organizados por tipo y orientación"""
    # Obtener lista plana desde el servicio
    workflows_list = get_available_workflows()
    
    # Reconstruir estructura jerárquica para el frontend (room_type -> orientation -> list)
    workflows_structure = {}
    for wf in workflows_list:
        room_type = wf.get('room_type')
        orientation = wf.get('orientation')
        
        if room_type and orientation:
            if room_type not in workflows_structure:
                workflows_structure[room_type] = {}
            if orientation not in workflows_structure[room_type]:
                workflows_structure[room_type][orientation] = []
            
            workflows_structure[room_type][orientation].append(wf)
    
    # Retornar estructura completa que espera el frontend
    return jsonify({
        "workflows": workflows_list,
        "structure": workflows_structure,
        "total": len(workflows_list),
        "config": WORKFLOW_CONFIG,
        "available_colors": WORKFLOW_CONFIG.get("frame_colors", ["black", "white", "brown", "gold"]),
        "available_styles": get_available_styles()
    })

@general_bp.route('/workflow-nodes/<path:workflow_name>', methods=['GET'])
def get_workflow_nodes(workflow_name):
    try:
        workflow_data = load_workflow(workflow_name)
        candidates = []
        for node_id, node in workflow_data.items():
            if node.get('class_type') == 'SeargeTextInputV2':
                title = node.get('_meta', {}).get('title', '')
                candidates.append({'id': node_id, 'title': title})
        return jsonify({'success': True, 'nodes': candidates})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500