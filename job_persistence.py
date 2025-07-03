#!/usr/bin/env python3
"""
Sistema de persistencia temporal para trabajos de ComfyUI
Solo mantiene trabajos activos durante la sesión (max 24 horas)
"""
import os
import json
import uuid
import shutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class SessionJobManager:
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.session_dir = os.path.join(self.base_dir, 'session_jobs')
        self.session_file = os.path.join(self.base_dir, 'active_jobs.json')
        
        # Crear directorio de sesión
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Limpiar trabajos antiguos al inicializar
        self.cleanup_old_jobs()
        
        # Inicializar archivo de trabajos activos
        if not os.path.exists(self.session_file):
            self._save_active_jobs({})
    
    def _save_active_jobs(self, jobs: Dict):
        """Guarda los trabajos activos en memoria"""
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False, default=str)
    
    def _load_active_jobs(self) -> Dict:
        """Carga los trabajos activos"""
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def create_job(self, job_type: str = 'individual', **config) -> str:
        """Crea un nuevo trabajo y devuelve su ID"""
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        job_data = {
            'id': job_id,
            'type': job_type,
            'status': 'created',
            'created_at': timestamp,
            'config': config,
            'results': [],
            'workflows': [],
            'current_operation': 'Iniciando...'
        }
        
        # Guardar en memoria activa
        active_jobs = self._load_active_jobs()
        active_jobs[job_id] = job_data
        self._save_active_jobs(active_jobs)
        
        return job_id
    
    def update_job(self, job_id: str, **updates) -> bool:
        """Actualiza un trabajo existente"""
        active_jobs = self._load_active_jobs()
        
        if job_id not in active_jobs:
            return False
        
        # Actualizar campos
        for key, value in updates.items():
            active_jobs[job_id][key] = value
        
        # Marcar tiempo de completado si es necesario
        if updates.get('status') == 'completed':
            active_jobs[job_id]['completed_at'] = datetime.now().isoformat()
        
        self._save_active_jobs(active_jobs)
        return True
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Obtiene un trabajo específico"""
        active_jobs = self._load_active_jobs()
        return active_jobs.get(job_id)
    
    def get_all_active_jobs(self) -> Dict:
        """Obtiene todos los trabajos activos"""
        self.cleanup_old_jobs()  # Limpiar antes de devolver
        return self._load_active_jobs()
    
    def get_running_jobs(self) -> List[Dict]:
        """Obtiene solo los trabajos que están ejecutándose"""
        active_jobs = self._load_active_jobs()
        running_statuses = ['created', 'running', 'processing', 'pending']
        return [job for job in active_jobs.values() if job.get('status') in running_statuses]
    
    def delete_job(self, job_id: str) -> bool:
        """Elimina un trabajo de la sesión"""
        active_jobs = self._load_active_jobs()
        
        if job_id in active_jobs:
            del active_jobs[job_id]
            self._save_active_jobs(active_jobs)
            
            # Limpiar archivos asociados si existen
            job_dir = os.path.join(self.session_dir, job_id)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)
            
            return True
        return False
    
    def save_job_image(self, job_id: str, image_data: bytes, filename: str) -> str:
        """Guarda una imagen asociada a un trabajo"""
        job_dir = os.path.join(self.session_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        image_path = os.path.join(job_dir, filename)
        with open(image_path, 'wb') as f:
            f.write(image_data)
        
        # Devolver ruta correcta para el frontend
        return f"/session/images/{job_id}/{filename}"
    
    def get_job_images(self, job_id: str) -> List[str]:
        """Obtiene las rutas de todas las imágenes de un trabajo"""
        job_dir = os.path.join(self.session_dir, job_id)
        if not os.path.exists(job_dir):
            return []
        
        images = []
        for filename in os.listdir(job_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                images.append(f"/session/images/{job_id}/{filename}")
        
        return sorted(images)
    
    def cleanup_old_jobs(self, hours: int = 24):
        """Limpia trabajos más antiguos que X horas (por defecto 24h)"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        active_jobs = self._load_active_jobs()
        cleaned_jobs = {}
        
        for job_id, job_data in active_jobs.items():
            try:
                created_time = datetime.fromisoformat(job_data['created_at'])
                if created_time > cutoff_time:
                    cleaned_jobs[job_id] = job_data
                else:
                    # Eliminar archivos del trabajo antiguo
                    job_dir = os.path.join(self.session_dir, job_id)
                    if os.path.exists(job_dir):
                        shutil.rmtree(job_dir)
            except (ValueError, KeyError):
                # Mantener trabajos con fecha inválida (probablemente recientes)
                cleaned_jobs[job_id] = job_data
        
        # Guardar solo los trabajos limpios
        self._save_active_jobs(cleaned_jobs)
        
        return len(active_jobs) - len(cleaned_jobs)
    
    def get_session_summary(self) -> Dict:
        """Obtiene un resumen de la sesión actual"""
        active_jobs = self._load_active_jobs()
        
        summary = {
            'total_jobs': len(active_jobs),
            'running_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'oldest_job': None,
            'newest_job': None
        }
        
        if not active_jobs:
            return summary
        
        job_times = []
        for job in active_jobs.values():
            status = job.get('status', 'unknown')
            if status in ['created', 'running', 'processing', 'pending']:
                summary['running_jobs'] += 1
            elif status == 'completed':
                summary['completed_jobs'] += 1
            elif status in ['error', 'failed']:
                summary['failed_jobs'] += 1
            
            try:
                created_time = datetime.fromisoformat(job['created_at'])
                job_times.append(created_time)
            except (ValueError, KeyError):
                pass
        
        if job_times:
            summary['oldest_job'] = min(job_times).isoformat()
            summary['newest_job'] = max(job_times).isoformat()
        
        return summary
    
    def clear_all_session(self) -> Dict:
        """Limpia completamente toda la sesión - todos los trabajos e imágenes"""
        try:
            # Obtener conteo actual antes de limpiar
            active_jobs = self._load_active_jobs()
            job_count = len(active_jobs)
            
            # Limpiar archivo de trabajos activos
            self._save_active_jobs({})
            
            # Limpiar completamente el directorio de sesión
            if os.path.exists(self.session_dir):
                shutil.rmtree(self.session_dir)
                os.makedirs(self.session_dir, exist_ok=True)
            
            return {
                "success": True,
                "message": f"Sesión limpiada completamente. Se eliminaron {job_count} trabajos.",
                "jobs_cleared": job_count,
                "session_reset": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error limpiando sesión: {str(e)}",
                "jobs_cleared": 0,
                "session_reset": False
            }

# Instancia global
session_manager = SessionJobManager()
