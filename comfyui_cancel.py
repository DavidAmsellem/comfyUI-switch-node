#!/usr/bin/env python3
"""
Módulo para cancelar y gestionar trabajos en ComfyUI
Permite cancelar trabajos individuales o limpiar toda la cola de procesamiento
"""
import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class ComfyUICancelManager:
    """Gestor para cancelar trabajos en ComfyUI"""
    
    def __init__(self, comfyui_host: str = 'localhost', comfyui_port: str = '8188'):
        self.host = comfyui_host
        self.port = comfyui_port
        self.base_url = f"http://{self.host}:{self.port}"
        
    def log_info(self, message: str):
        """Log con timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🔄 CANCEL: {message}")
    
    def log_success(self, message: str):
        """Log de éxito"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ✅ CANCEL: {message}")
    
    def log_warning(self, message: str):
        """Log de advertencia"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ⚠️ CANCEL: {message}")
    
    def log_error(self, message: str):
        """Log de error"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ❌ CANCEL: {message}")
    
    def get_queue_status(self) -> Optional[Dict]:
        """Obtiene el estado actual de la cola de ComfyUI"""
        try:
            response = requests.get(f"{self.base_url}/queue", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                self.log_error(f"Error obteniendo estado de cola: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            self.log_error(f"Error conectando con ComfyUI: {str(e)}")
            return None
    
    def get_running_jobs(self) -> Tuple[List[str], List[str]]:
        """
        Obtiene los trabajos en ejecución y en cola
        Returns: (running_prompt_ids, queued_prompt_ids)
        """
        queue_status = self.get_queue_status()
        if not queue_status:
            return [], []
        
        running_ids = []
        queued_ids = []
        
        # Trabajos en ejecución
        if 'queue_running' in queue_status:
            for job in queue_status['queue_running']:
                if isinstance(job, list) and len(job) >= 2:
                    prompt_id = job[1]  # El ID del prompt está en la posición 1
                    running_ids.append(prompt_id)
        
        # Trabajos en cola
        if 'queue_pending' in queue_status:
            for job in queue_status['queue_pending']:
                if isinstance(job, list) and len(job) >= 2:
                    prompt_id = job[1]  # El ID del prompt está en la posición 1
                    queued_ids.append(prompt_id)
        
        return running_ids, queued_ids
    
    def interrupt_current_job(self) -> bool:
        """Interrumpe el trabajo actual en ejecución"""
        try:
            self.log_info("Interrumpiendo trabajo actual...")
            response = requests.post(f"{self.base_url}/interrupt", timeout=10)
            
            if response.status_code == 200:
                self.log_success("Trabajo actual interrumpido correctamente")
                return True
            else:
                self.log_error(f"Error interrumpiendo trabajo: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Error enviando interrupción: {str(e)}")
            return False
    
    def clear_queue(self, clear_type: str = "queue") -> bool:
        """
        Limpia la cola de ComfyUI
        
        Args:
            clear_type: Tipo de limpieza
                - "queue": Solo cola pendiente
                - "interrupt": Solo interrumpir actual
                - "all": Interrumpir actual + limpiar cola
        """
        try:
            success = True
            
            if clear_type in ["interrupt", "all"]:
                self.log_info("Interrumpiendo trabajo en ejecución...")
                interrupt_success = self.interrupt_current_job()
                if not interrupt_success:
                    success = False
                
                # Esperar un momento para que se complete la interrupción
                time.sleep(1)
            
            if clear_type in ["queue", "all"]:
                self.log_info("Limpiando cola de trabajos pendientes...")
                
                # Usar el endpoint de limpieza de cola
                clear_data = {"clear": True}
                response = requests.post(
                    f"{self.base_url}/queue", 
                    json=clear_data,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    self.log_success("Cola limpiada correctamente")
                else:
                    self.log_error(f"Error limpiando cola: HTTP {response.status_code}")
                    success = False
            
            return success
            
        except requests.exceptions.RequestException as e:
            self.log_error(f"Error durante limpieza: {str(e)}")
            return False
    
    def cancel_specific_job(self, prompt_id: str) -> bool:
        """Cancela un trabajo específico por su ID"""
        try:
            self.log_info(f"Cancelando trabajo específico: {prompt_id}")
            
            # Usar el endpoint de eliminación de trabajo específico
            delete_data = {"delete": [prompt_id]}
            response = requests.post(
                f"{self.base_url}/queue",
                json=delete_data,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                self.log_success(f"Trabajo {prompt_id} cancelado correctamente")
                return True
            else:
                self.log_error(f"Error cancelando trabajo {prompt_id}: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_error(f"Error cancelando trabajo {prompt_id}: {str(e)}")
            return False
    
    def get_queue_summary(self) -> Dict:
        """Obtiene un resumen del estado de la cola"""
        running_ids, queued_ids = self.get_running_jobs()
        
        return {
            'running_count': len(running_ids),
            'queued_count': len(queued_ids),
            'total_jobs': len(running_ids) + len(queued_ids),
            'running_ids': running_ids,
            'queued_ids': queued_ids,
            'comfyui_accessible': True if running_ids is not None else False
        }
    
    def cancel_all_jobs(self) -> Dict:
        """
        Cancela todos los trabajos (en ejecución y en cola)
        Retorna un resumen de la operación
        """
        self.log_info("🚨 INICIANDO CANCELACIÓN MASIVA DE TODOS LOS TRABAJOS")
        
        # Obtener estado inicial
        initial_summary = self.get_queue_summary()
        
        if not initial_summary['comfyui_accessible']:
            return {
                'success': False,
                'error': 'ComfyUI no está accesible',
                'initial_jobs': 0,
                'cancelled_jobs': 0
            }
        
        initial_total = initial_summary['total_jobs']
        self.log_info(f"📊 Estado inicial: {initial_summary['running_count']} ejecutándose, {initial_summary['queued_count']} en cola")
        
        if initial_total == 0:
            self.log_info("✅ No hay trabajos para cancelar")
            return {
                'success': True,
                'message': 'No había trabajos en procesamiento',
                'initial_jobs': 0,
                'cancelled_jobs': 0
            }
        
        # Realizar cancelación masiva
        success = self.clear_queue("all")
        
        # Esperar un momento y verificar el resultado
        time.sleep(2)
        final_summary = self.get_queue_summary()
        
        if success and final_summary['comfyui_accessible']:
            cancelled_count = initial_total - final_summary['total_jobs']
            
            self.log_success(f"🎯 CANCELACIÓN COMPLETADA: {cancelled_count} de {initial_total} trabajos cancelados")
            
            if final_summary['total_jobs'] == 0:
                self.log_success("✅ Todos los trabajos fueron cancelados exitosamente")
            else:
                self.log_warning(f"⚠️ Quedan {final_summary['total_jobs']} trabajos sin cancelar")
            
            return {
                'success': True,
                'message': f'Cancelados {cancelled_count} de {initial_total} trabajos',
                'initial_jobs': initial_total,
                'cancelled_jobs': cancelled_count,
                'remaining_jobs': final_summary['total_jobs']
            }
        else:
            return {
                'success': False,
                'error': 'Error durante la cancelación masiva',
                'initial_jobs': initial_total,
                'cancelled_jobs': 0
            }


# Instancia global para uso fácil
cancel_manager = ComfyUICancelManager()


def cancel_all_comfyui_jobs() -> Dict:
    """Función de conveniencia para cancelar todos los trabajos"""
    return cancel_manager.cancel_all_jobs()


def get_comfyui_queue_status() -> Dict:
    """Función de conveniencia para obtener el estado de la cola"""
    return cancel_manager.get_queue_summary()


def cancel_specific_comfyui_job(prompt_id: str) -> bool:
    """Función de conveniencia para cancelar un trabajo específico"""
    return cancel_manager.cancel_specific_job(prompt_id)
