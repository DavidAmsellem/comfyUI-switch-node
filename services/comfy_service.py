import requests
import uuid
import time
import os
import json
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

def get_current_executing_prompt():
    """Obtiene el prompt_id que está siendo ejecutado actualmente en ComfyUI"""
    try:
        status_response = requests.get(f"{COMFYUI_URL}/prompt", timeout=5)
        if status_response.status_code == 200:
            queue_data = status_response.json()
            # El job que está ejecutándose estará en queue_running[0] si existe
            queue_running = queue_data.get('queue_running', [])
            if queue_running and len(queue_running) > 0:
                return queue_running[0][1]  # [priority, prompt_id, ...]
        return None
    except:
        return None

def wait_for_completion(prompt_id, timeout=600, callback=None, workflow_data=None):
    """
    Espera a que ComfyUI complete el procesamiento usando polling optimizado
    Solo hace polling cuando el job está siendo ejecutado activamente
    Retorna: outputs del workflow
    """
    from utils.logger import log_info, log_warning, log_error
    
    log_info(f"🔌 [WAIT {prompt_id[:8]}] Iniciando wait_for_completion con polling optimizado...")
    
    # Verificar estado de la cola antes de comenzar
    try:
        status_response = requests.get(f"{COMFYUI_URL}/prompt", timeout=5)
        if status_response.status_code == 200:
            queue_data = status_response.json()
            queue_remaining = queue_data.get('exec_info', {}).get('queue_remaining', 0)
            log_info(f"📊 [WAIT {prompt_id[:8]}] Cola de ComfyUI: {queue_remaining} trabajos pendientes")
        else:
            log_warning(f"⚠️ [WAIT {prompt_id[:8]}] No se pudo consultar estado de cola")
    except Exception as e:
        log_warning(f"⚠️ [WAIT {prompt_id[:8]}] Error consultando cola: {e}")
    
    start_time = time.time()
    
    # Fase 1: Esperar hasta que nuestro job esté siendo ejecutado
    log_info(f"⏳ [WAIT {prompt_id[:8]}] Esperando turno en cola...")
    while time.time() - start_time < timeout:
        current_executing = get_current_executing_prompt()
        if current_executing == prompt_id:
            log_info(f"🎯 [WAIT {prompt_id[:8]}] ¡Nuestro job está siendo ejecutado!")
            break
        
        # Si hay algo ejecutándose pero no es nuestro job, esperar más tiempo
        if current_executing:
            log_info(f"⌛ [WAIT {prompt_id[:8]}] Esperando... (ejecutándose: {current_executing[:8]})")
            time.sleep(5)  # Esperar más tiempo cuando no es nuestro turno
        else:
            time.sleep(2)  # Polling más frecuente si no hay nada ejecutándose
    
    # Fase 2: Polling activo del historial una vez que estamos ejecutando
    log_info(f"🔄 [WAIT {prompt_id[:8]}] Iniciando polling del historial...")
    
    for i in range(timeout):
        try:
            log_info(f"📊 [WAIT {prompt_id[:8]}] Polling attempt #{i + 1}/{timeout}")
            
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30)
            
            if response.status_code == 200:
                history = response.json()
                log_info(f"� [WAIT {prompt_id[:8]}] Historia recibida, keys: {list(history.keys())}")
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    log_info(f"🎯 [WAIT {prompt_id[:8]}] Prompt encontrado en historial!")
                    
                    # Verificar si hay outputs
                    if 'outputs' in prompt_history:
                        log_info(f"� [WAIT {prompt_id[:8]}] ¡Procesamiento completado con éxito!")
                        return prompt_history['outputs']
                    
                    # Verificar errores
                    if 'status' in prompt_history and 'error' in prompt_history['status']:
                        error_msg = prompt_history['status']['error']
                        log_error(f"❌ [WAIT {prompt_id[:8]}] Error en ComfyUI: {error_msg}")
                        raise Exception(f"Error en ComfyUI: {error_msg}")
                else:
                    log_info(f"⏳ [WAIT {prompt_id[:8]}] Prompt aún no está en historial, esperando...")
            else:
                log_warning(f"⚠️ [WAIT {prompt_id[:8]}] Status code: {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            log_warning(f"⚠️ [WAIT {prompt_id[:8]}] Request error: {e}, continuando...")
        except Exception as e:
            log_error(f"❌ [WAIT {prompt_id[:8]}] Error inesperado: {e}")
            
        # Polling adaptativo basado en quien está ejecutando:
        current_executing = get_current_executing_prompt()
        if current_executing == prompt_id:
            # Es nuestro turno: polling frecuente
            time.sleep(2)
        elif current_executing:
            # Otro job ejecutándose: esperar más tiempo
            time.sleep(5) 
        else:
            # Nada ejecutándose: polling medio
            time.sleep(3)
            
        # Log de progreso cada 30 segundos
        if i % 30 == 0 and i > 0:
            elapsed = time.time() - start_time
            log_info(f"⏰ [WAIT {prompt_id[:8]}] Esperando... {i}/{timeout}s (elapsed: {elapsed:.1f}s)")
    
    elapsed = time.time() - start_time
    log_error(f"⏰ [WAIT {prompt_id[:8]}] Timeout después de {timeout} segundos (elapsed: {elapsed:.1f}s)")
    raise TimeoutError(f"Timeout esperando completion después de {timeout} segundos")

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

def wait_for_completion_simple(prompt_id, timeout=300):
    """
    Función simple de wait_for_completion como en app_new.py - SOLO para batch processing
    Retorna: outputs del workflow
    """
    from utils.logger import log_info, log_error
    
    log_info(f"⏳ [BATCH SIMPLE] Esperando completion del prompt: {prompt_id[:8]}")
    
    for i in range(timeout):
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30)
            
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    
                    # Verificar si hay outputs
                    if 'outputs' in prompt_history:
                        log_info(f"✅ [BATCH SIMPLE] Procesamiento completado para {prompt_id[:8]}")
                        return prompt_history['outputs']
                    
                    # Verificar errores
                    if 'status' in prompt_history and 'error' in prompt_history['status']:
                        error_msg = prompt_history['status']['error']
                        log_error(f"❌ [BATCH SIMPLE] Error en ComfyUI para {prompt_id[:8]}: {error_msg}")
                        raise Exception(f"Error en ComfyUI: {error_msg}")
                        
        except requests.exceptions.RequestException:
            log_info(f"⚠️ [BATCH SIMPLE] Request timeout, reintentando... ({i}/{timeout})")
            
        time.sleep(1)  # Polling simple cada segundo
    
    raise TimeoutError(f"Timeout esperando completion después de {timeout} segundos")