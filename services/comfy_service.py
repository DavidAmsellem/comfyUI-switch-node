import requests
import uuid
import time
import os
import json
import websocket 
from config import COMFYUI_URL, COMFYUI_INPUT_DIR, COMFYUI_HOST, COMFYUI_PORT
from utils.logger import log_info, log_error, log_warning

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
        # print(f"📤 [DEBUG] Enviando workflow...") 
        response = requests.post(f"{COMFYUI_URL}/prompt", json=prompt_data, timeout=60)
        response.raise_for_status()
        pid = response.json().get('prompt_id')
        return pid
    except Exception as e:
        log_error(f"Error enviando workflow: {str(e)}")
        raise

def interrupt_current_processing():
    """Manda una señal para detener la generación actual inmediatamente"""
    try:
        requests.post(f"{COMFYUI_URL}/interrupt", timeout=2)
        log_info("🛑 Señal de interrupción enviada a ComfyUI")
        return True
    except Exception as e:
        log_error(f"Error enviando interrupt: {e}")
        return False

def delete_queue_items(prompt_ids):
    """Borra una lista de IDs específicos de la cola de espera de ComfyUI"""
    try:
        if not prompt_ids: return
        
        payload = {"delete": prompt_ids}
        requests.post(f"{COMFYUI_URL}/queue", json=payload, timeout=2)
        log_info(f"🗑️ Eliminados de la cola de ComfyUI: {prompt_ids}")
        return True
    except Exception as e:
        log_error(f"Error borrando items de cola: {e}")
        return False

def wait_for_completion(prompt_id, timeout=600, callback=None, workflow_data=None):
    """
    Espera resultados de forma robusta: WebSocket + Polling Fallback
    """
    start_time = time.time()
    
    # 1. Intentar vía WebSocket
    ws = websocket.WebSocket()
    try:
        url = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws?clientId={CLIENT_ID}"
        ws.connect(url)
        
        while True:
            if time.time() - start_time > timeout: break
            
            try:
                out = ws.recv()
                if not isinstance(out, str): continue
                message = json.loads(out)
                
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break 
                
                if message['type'] == 'execution_success' and message['data']['prompt_id'] == prompt_id:
                    break 
                    
            except Exception:
                break 
                
    except Exception as e:
        log_warning(f"⚠️ WebSocket inestable ({e}), cambiando a Polling...")
    finally:
        try: ws.close()
        except: pass

    # 2. PLAN B: Polling al Historial
    polling_attempts = 0
    max_polling_time = 30 
    
    while polling_attempts < max_polling_time:
        history = _get_history_direct(prompt_id)
        if history:
            return history
        
        time.sleep(1)
        polling_attempts += 1
        if time.time() - start_time > timeout:
            raise TimeoutError("Timeout global esperando a ComfyUI")

    return None

def _get_history_direct(prompt_id):
    try:
        res = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
        if res.status_code == 200:
            hist = res.json()
            if prompt_id in hist:
                return hist[prompt_id]['outputs']
    except: pass
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