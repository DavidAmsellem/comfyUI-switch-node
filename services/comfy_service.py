import requests
import uuid
import time
import os
from config import COMFYUI_URL, COMFYUI_INPUT_DIR
from utils.logger import log_info, log_success, log_error, log_warning

def verify_image_accessibility(filename):
    try:
        input_path = os.path.join(COMFYUI_INPUT_DIR, filename)
        if not os.path.exists(input_path):
            return False
        
        # Intento 1
        response = requests.get(f"{COMFYUI_URL}/view", params={'filename': filename}, timeout=10)
        if response.status_code == 200: return True
        
        # Intento 2
        response2 = requests.get(f"{COMFYUI_URL}/view", params={'filename': filename, 'type': 'input'}, timeout=10)
        return response2.status_code == 200
    except Exception as e:
        log_warning(f"Error verificando acceso: {str(e)}")
        return False

def submit_workflow_to_comfyui(workflow):
    client_id = str(uuid.uuid4())
    try:
        response = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=60)
        response.raise_for_status()
        result = response.json()
        prompt_id = result.get('prompt_id')
        if not prompt_id: raise ValueError("Sin prompt_id")
        log_success(f"Enviado. ID: {prompt_id}")
        return prompt_id
    except Exception as e:
        log_error(f"Error enviando workflow: {str(e)}")
        raise

def wait_for_completion(prompt_id, timeout=300):
    log_info(f"Esperando prompt: {prompt_id}")
    for i in range(timeout):
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    data = history[prompt_id]
                    if 'outputs' in data: return data['outputs']
                    if 'status' in data and 'error' in data['status']:
                        raise Exception(data['status']['error'])
            time.sleep(1)
        except requests.exceptions.RequestException:
            time.sleep(1)
            continue
    raise TimeoutError(f"Timeout en prompt {prompt_id}")