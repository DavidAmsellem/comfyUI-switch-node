import requests
import uuid
import time
import os
import json
import websocket 
from config import COMFYUI_URL, COMFYUI_INPUT_DIR, COMFYUI_HOST, COMFYUI_PORT
from utils.logger import log_info, log_success, log_error, log_warning

CLIENT_ID = str(uuid.uuid4())

def verify_image_accessibility(filename):
    try:
        input_path = os.path.join(COMFYUI_INPUT_DIR, filename)
        if not os.path.exists(input_path): return False
        response = requests.get(f"{COMFYUI_URL}/view", params={'filename': filename}, timeout=10)
        return response.status_code == 200
    except: return False

def submit_workflow_to_comfyui(workflow):
    prompt_data = {"prompt": workflow, "client_id": CLIENT_ID}
    try:
        response = requests.post(f"{COMFYUI_URL}/prompt", json=prompt_data, timeout=60)
        response.raise_for_status()
        return response.json().get('prompt_id')
    except Exception as e:
        log_error(f"Error enviando workflow: {str(e)}")
        raise

# --- FUNCIÓN ACTUALIZADA PARA LEER NOMBRES DE NODOS ---
def wait_for_completion(prompt_id, timeout=600, callback=None, workflow_data=None):
    """
    Espera resultados y traduce IDs de nodos a nombres legibles.
    """
    ws = websocket.WebSocket()
    ws_url = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws?clientId={CLIENT_ID}"
    
    # Crear mapa de ID -> Título (ej: "10" -> "Load Checkpoint")
    node_titles = {}
    if workflow_data:
        for node_id, node_info in workflow_data.items():
            title = node_info.get('_meta', {}).get('title')
            class_type = node_info.get('class_type', 'Node')
            # Preferir título personalizado, luego título meta, luego tipo
            node_titles[str(node_id)] = title if title else class_type

    try:
        log_info(f"🔌 Conectando WS para prompt {prompt_id}...")
        ws.connect(ws_url)
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError("Timeout esperando ComfyUI")

            try:
                out = ws.recv()
                if not isinstance(out, str): continue
                
                message = json.loads(out)
                msg_type = message['type']
                data = message['data']

                # 1. Estado de ejecución (TRADUCCIÓN DE NOMBRE)
                if msg_type == 'executing':
                    node_id = data.get('node')
                    if node_id is None:
                        break # Fin
                    
                    # Traducir ID a Nombre
                    node_name = node_titles.get(str(node_id), f"Nodo {node_id}")
                    
                    # Mensajes amigables según el tipo de nodo
                    status_text = f"Procesando: {node_name}"
                    if "checkpoint" in node_name.lower(): status_text = f"📥 Cargando Modelo ({node_name})..."
                    if "ksampler" in node_name.lower(): status_text = "🎨 Generando imagen..."
                    if "save" in node_name.lower(): status_text = "💾 Guardando resultado..."
                    
                    if callback: callback(status_text, None)

                # 2. Barra de progreso
                elif msg_type == 'progress':
                    val = data['value']
                    max_val = data['max']
                    percent = int((val / max_val) * 100)
                    if callback: callback(f"Generando: {percent}%", percent)

                # 3. Éxito
                elif msg_type == 'execution_success':
                    if data['prompt_id'] == prompt_id:
                        if callback: callback("Finalizando...", 100)
                        break
            
            except websocket.WebSocketConnectionClosedException:
                break # Fallback
            except Exception:
                pass # Ignorar errores de parseo menores
                
    except Exception as e:
        log_warning(f"⚠️ Error WS: {e}")
    finally:
        try:
            if ws.connected: ws.close()
        except: pass

    return _get_history(prompt_id)

def _get_history(prompt_id):
    for _ in range(5): # Reintentos
        try:
            res = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
            if res.status_code == 200:
                hist = res.json()
                if prompt_id in hist: return hist[prompt_id]['outputs']
        except: pass
        time.sleep(1)
    return None

def get_system_status():
    try:
        response = requests.get(f"{COMFYUI_URL}/prompt", timeout=2)
        if response.status_code == 200:
            data = response.json()
            queue = data.get('exec_info', {}).get('queue_remaining', 0)
            if queue > 0: return {"online": True, "status": "processing", "message": f"Cola: {queue}"}
            return {"online": True, "status": "idle", "message": "Listo"}
    except: pass
    return {"online": False, "status": "offline", "message": "Offline"}