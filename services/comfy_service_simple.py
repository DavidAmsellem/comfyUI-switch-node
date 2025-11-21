import requests
import time
from config import COMFYUI_URL
from utils.logger import log_info, log_warning, log_error

def wait_for_completion_simple(prompt_id, timeout=600):
    """
    Espera a que ComfyUI complete el procesamiento usando la lógica simple que funciona en batch
    VERSIÓN TEMPORAL PARA DEBUG - Usando lógica de app_new.py que sabemos que funciona
    Retorna: outputs del workflow
    """
    log_info(f"🔌 [WAIT-SIMPLE {prompt_id[:8]}] Iniciando wait_for_completion SIMPLE...")
    
    for i in range(timeout):
        try:
            log_info(f"📊 [WAIT-SIMPLE {prompt_id[:8]}] Polling simple attempt #{i + 1}/{timeout}")
            
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30)
            
            if response.status_code == 200:
                history = response.json()
                log_info(f"📊 [WAIT-SIMPLE {prompt_id[:8]}] Historia recibida, keys: {list(history.keys())}")
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    log_info(f"🎯 [WAIT-SIMPLE {prompt_id[:8]}] Prompt encontrado en historial!")
                    
                    # Verificar si hay outputs
                    if 'outputs' in prompt_history:
                        log_info(f"✅ [WAIT-SIMPLE {prompt_id[:8]}] ¡Procesamiento completado con éxito!")
                        return prompt_history['outputs']
                    
                    # Verificar errores
                    if 'status' in prompt_history and 'error' in prompt_history['status']:
                        error_msg = prompt_history['status']['error']
                        log_error(f"❌ [WAIT-SIMPLE {prompt_id[:8]}] Error en ComfyUI: {error_msg}")
                        raise Exception(f"Error en ComfyUI: {error_msg}")
                else:
                    log_info(f"⏳ [WAIT-SIMPLE {prompt_id[:8]}] Prompt aún no está en historial, esperando...")
            else:
                log_warning(f"⚠️ [WAIT-SIMPLE {prompt_id[:8]}] Status code: {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            log_warning(f"⚠️ [WAIT-SIMPLE {prompt_id[:8]}] Request error: {e}, continuando...")
            time.sleep(1)
            continue
        except Exception as e:
            log_error(f"❌ [WAIT-SIMPLE {prompt_id[:8]}] Error inesperado: {e}")
            
        # Usar intervalo simple de 1 segundo como en app_new.py que funciona
        time.sleep(1)
            
        # Log de progreso cada 10 segundos
        if i % 10 == 0 and i > 0:
            log_info(f"⏰ [WAIT-SIMPLE {prompt_id[:8]}] Esperando... {i}/{timeout}s")
    
    log_error(f"⏰ [WAIT-SIMPLE {prompt_id[:8]}] Timeout después de {timeout} segundos")
    raise TimeoutError(f"Timeout esperando completion después de {timeout} segundos")
