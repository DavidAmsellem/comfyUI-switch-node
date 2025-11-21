import json
import os
import time
import uuid
from config import BASE_DIR, OUR_OUTPUT_DIR

# Directorio donde se guardan los JSON de estado PARA TRABAJOS INDIVIDUALES
INDIVIDUAL_JOBS_DIR = os.path.join(BASE_DIR, 'individual_jobs_data')
os.makedirs(INDIVIDUAL_JOBS_DIR, exist_ok=True)

class IndividualSessionManager:
    """
    Gestor de persistencia específico para trabajos individuales
    Maneja un solo workflow por job
    """
    def __init__(self):
        self.session_dir = OUR_OUTPUT_DIR

    def create_job(self, job_type='individual', **kwargs):
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "type": job_type,
            "status": "pending",
            "created_at": time.time(),
            "updated_at": time.time(),
            **kwargs
        }
        self._save_job(job_id, job_data)
        return job_id

    def update_job(self, job_id, **kwargs):
        data = self.get_job(job_id)
        if data:
            # Actualización simple como batch - sin logs excesivos ni lógica compleja
            data.update(kwargs)
            data['updated_at'] = time.time()
            
            # Manejar resultados de forma simple
            if 'results' in kwargs and kwargs['results']:
                data['results'] = kwargs['results']
            
            self._save_job(job_id, data)
            return True
        return False

    def get_job(self, job_id):
        path = os.path.join(INDIVIDUAL_JOBS_DIR, f"{job_id}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None

    def get_all_active_jobs(self, limit=50):
        """Recupera los últimos trabajos individuales para el historial"""
        jobs = []
        try:
            files = sorted(
                [os.path.join(INDIVIDUAL_JOBS_DIR, f) for f in os.listdir(INDIVIDUAL_JOBS_DIR) if f.endswith('.json')],
                key=os.path.getmtime,
                reverse=True
            )
            for f in files[:limit]:
                try:
                    with open(f, 'r') as handle:
                        jobs.append(json.load(handle))
                except: pass
        except Exception:
            pass
        return jobs

    def save_job_image(self, job_id, image_bytes, filename):
        """Guarda la imagen física y devuelve la URL relativa"""
        # Extraer el base_name del filename (ej: bedroom_V60x80_xxx -> bedroom)
        # Si el filename no tiene guión bajo, usar una carpeta por defecto
        if '_' in filename:
            base_name = filename.split('_')[0]
        else:
            base_name = 'misc'  # carpeta por defecto
            
        # Retornar URL compatible con el endpoint /get-image/<base_name>/<filename>
        return f"/get-image/{base_name}/{filename}"

    def cleanup_old_jobs(self, hours=24):
        count = 0
        now = time.time()
        cutoff = now - (hours * 3600)
        for f in os.listdir(INDIVIDUAL_JOBS_DIR):
            if f.endswith('.json'):
                path = os.path.join(INDIVIDUAL_JOBS_DIR, f)
                if os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                        count += 1
                    except: pass
        return count

    def clear_all_session(self):
        # Borra todos los json de jobs individuales
        for f in os.listdir(INDIVIDUAL_JOBS_DIR):
            if f.endswith('.json'):
                try: os.remove(os.path.join(INDIVIDUAL_JOBS_DIR, f))
                except: pass
        return {"success": True}

    def _save_job(self, job_id, data):
        path = os.path.join(INDIVIDUAL_JOBS_DIR, f"{job_id}.json")
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

individual_session_manager = IndividualSessionManager()

# Mantener compatibilidad con app_new.py (archivo antiguo)
session_manager = individual_session_manager