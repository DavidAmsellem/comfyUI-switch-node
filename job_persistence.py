import json
import os
import time
import uuid
from config import BASE_DIR, OUR_OUTPUT_DIR

# Directorio donde se guardan los JSON de estado
JOBS_DIR = os.path.join(BASE_DIR, 'jobs_data')
os.makedirs(JOBS_DIR, exist_ok=True)

class SessionManager:
    def __init__(self):
        self.session_dir = OUR_OUTPUT_DIR # Para referencia externa si hace falta

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
            data.update(kwargs)
            data['updated_at'] = time.time()
            # Si se pasan resultados, asegurar que se anexan o sobrescriben según lógica
            if 'results' in kwargs and kwargs['results']:
                # En batch, a veces queremos acumular, pero por simplicidad aquí actualizamos
                data['results'] = kwargs['results']
            
            self._save_job(job_id, data)
            return True
        return False

    def get_job(self, job_id):
        path = os.path.join(JOBS_DIR, f"{job_id}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None

    def get_all_active_jobs(self, limit=50):
        """Recupera los últimos trabajos para el historial de sesión"""
        jobs = []
        try:
            files = sorted(
                [os.path.join(JOBS_DIR, f) for f in os.listdir(JOBS_DIR) if f.endswith('.json')],
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
        # Nota: job_id se usa para referencia, pero guardamos en carpeta plana por nombre base
        # (La lógica de carpetas ya la maneja file_service, aquí solo ayudamos a persistir la URL)
        # En tu file_service ya guardas el archivo físico. 
        # Aquí solo devolvemos la ruta web estandarizada.
        return f"/get-image/{filename.split('_')[0]}/{filename}" 
        # Nota: Ajusta esta ruta según tu estructura de carpetas de salida real si usas subcarpetas.
        # Para simplificar con tu file_service actual:
        return f"/outputs/{filename}" # Placeholder, el file_service maneja la ruta real.

    def cleanup_old_jobs(self, hours=24):
        count = 0
        now = time.time()
        cutoff = now - (hours * 3600)
        for f in os.listdir(JOBS_DIR):
            if f.endswith('.json'):
                path = os.path.join(JOBS_DIR, f)
                if os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                        count += 1
                    except: pass
        return count

    def clear_all_session(self):
        # Borra todos los json
        for f in os.listdir(JOBS_DIR):
            if f.endswith('.json'):
                try: os.remove(os.path.join(JOBS_DIR, f))
                except: pass
        return {"success": True}

    def _save_job(self, job_id, data):
        path = os.path.join(JOBS_DIR, f"{job_id}.json")
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

session_manager = SessionManager()