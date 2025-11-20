import requests
import uuid
import time
import os
import json
import websocket # pip install websocket-client
from config import COMFYUI_URL, COMFYUI_INPUT_DIR, COMFYUI_HOST, COMFYUI_PORT
from utils.logger import log_info, log_success, log_error, log_warning

# Obtener ID del cliente para WebSocket
CLIENT_ID = str(uuid.uuid4())

def verify_image_accessibility(filename):
    try:
        input_path = os.path.join(COMFYUI_INPUT_DIR, filename)
        if not os.path.exists(input_path):
            return False
        response = requests.get(f"{COMFYUI_URL}/view", params={'filename': filename}, timeout=10)
        return response.status_code == 200
    except:
        return False

def submit_workflow_to_comfyui(workflow):
    prompt_data = {"prompt": workflow, "client_id": CLIENT_ID}
    try:
        response = requests.post(f"{COMFYUI_URL}/prompt", json=prompt_data, timeout=60)
        response.raise_for_status()
        return response.json().get('prompt_id')
    except Exception as e:
        log_error(f"Error enviando workflow: {str(e)}")
        raise

def wait_for_completion(prompt_id, timeout=300, callback=None, workflow_data=None):
    """
    Espera a que termine el prompt escuchando el WebSocket para dar feedback detallado.
    callback: función(mensaje, progreso) para actualizar la UI
    """
    ws = websocket.WebSocket()
    try:
        # Conectar al WebSocket de ComfyUI
        ws_url = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws?clientId={CLIENT_ID}"
        ws.connect(ws_url)
        log_info(f"🔌 Conectado a WS para monitorear {prompt_id}")
        
        start_time = time.time()
        
        # Mapa de títulos de nodos para mostrar nombres bonitos
        node_titles = {}
        if workflow_data:
            for nid, n in workflow_data.items():
                title = n.get('_meta', {}).get('title')
                class_type = n.get('class_type', 'Nodo')
                node_titles[nid] = title if title else class_type

        while True:
            # Timeout de seguridad
            if time.time() - start_time > timeout:
                raise TimeoutError("Timeout esperando respuesta de ComfyUI")

            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                msg_type = message['type']
                data = message['data']
                
                # 1. Nodo ejecutándose actualmente
                if msg_type == 'executing':
                    node_id = data.get('node')
                    if node_id is None:
                        break # Ejecución terminada (node es null)
                    
                    # Buscar nombre bonito del nodo
                    node_name = node_titles.get(str(node_id), f"Nodo {node_id}")
                    status_msg = f"Procesando: {node_name}"
                    
                    if callback: callback(status_msg, None)
                
                # 2. Progreso de la barra (KSampler)
                elif msg_type == 'progress':
                    val = data['value']
                    max_val = data['max']
                    percent = int((val / max_val) * 100)
                    if callback: callback(None, percent)
                
                # 3. Ejecución completada exitosamente
                elif msg_type == 'execution_success':
                    if data['prompt_id'] == prompt_id:
                        break

    except Exception as e:
        log_warning(f"⚠️ Error en WebSocket, cambiando a modo polling simple: {e}")
        # Fallback al método antiguo si falla el WS
        _wait_with_polling(prompt_id, timeout)
    finally:
        if ws.connected:
            ws.close()

    # Obtener historial final
    return _get_history(prompt_id)

def _wait_with_polling(prompt_id, timeout):
    # Método de respaldo antiguo
    for _ in range(timeout):
        try:
            if _get_history(prompt_id): return
        except: pass
        time.sleep(1)
    raise TimeoutError("Timeout en polling")

def _get_history(prompt_id):
    res = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
    if res.status_code == 200:
        hist = res.json()
        if prompt_id in hist:
            return hist[prompt_id]['outputs']
    return None

def get_system_status():
    """Obtiene el estado global de ComfyUI (Cola y Estado de ejecución)"""
    try:
        # Consultamos la cola actual (/prompt devuelve {exec_info: ..., queue_remaining: ...})
        response = requests.get(f"{COMFYUI_URL}/prompt", timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            exec_info = data.get('exec_info', {})
            queue_remaining = exec_info.get('queue_remaining', 0)
            
            # Determinamos el estado
            if queue_remaining > 0:
                status = 'processing'
                message = f'Procesando (Cola: {queue_remaining})'
            else:
                status = 'idle'
                message = 'Listo / Ocioso'
                
            return {
                "online": True,
                "status": status,
                "queue_size": queue_remaining,
                "message": message
            }
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        log_error(f"Error checking system status: {e}")
    
    return {
        "online": False,
        "status": "offline",
        "queue_size": 0,
        "message": "Desconectado"
    }