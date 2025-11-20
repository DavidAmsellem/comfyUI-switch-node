import os
import json
import shutil
import uuid
from datetime import datetime
from config import BASE_DIR

# Carpeta física
SESSION_DIR = os.path.join(BASE_DIR, 'session_data')
os.makedirs(SESSION_DIR, exist_ok=True)

class SessionManager:
    def __init__(self):
        self.session_dir = SESSION_DIR

    def create_job(self, job_type, **kwargs):
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "type": job_type,
            "status": "processing", # Directamente processing
            "current_operation": "Procesando...",
            "created_at": datetime.now().isoformat(),
            "results": [],
            **kwargs
        }
        
        job_dir = os.path.join(self.session_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        self._save_json(job_id, job)
        return job_id

    def update_job(self, job_id, **kwargs):
        # Leemos, actualizamos y guardamos
        job = self.get_job(job_id)
        if job:
            job.update(kwargs)
            self._save_json(job_id, job)

    def get_job(self, job_id):
        path = os.path.join(self.session_dir, job_id, 'job.json')
        if os.path.exists(path):
            try:
                with open(path, 'r') as f: return json.load(f)
            except: return None # Si falla leyendo (bloqueo), devuelve None y el front reintenta
        return None

    def save_job_image(self, job_id, image_data, filename):
        job_dir = os.path.join(self.session_dir, job_id)
        if not os.path.exists(job_dir): os.makedirs(job_dir, exist_ok=True)
        
        path = os.path.join(job_dir, filename)
        with open(path, 'wb') as f: f.write(image_data)
        return f"/session/images/{job_id}/{filename}"

    def _save_json(self, job_id, data):
        path = os.path.join(self.session_dir, job_id, 'job.json')
        try:
            with open(path, 'w') as f: json.dump(data, f, indent=2)
        except: pass 

    def get_all_active_jobs(self):
        jobs = {}
        if os.path.exists(self.session_dir):
            for jid in os.listdir(self.session_dir):
                j = self.get_job(jid)
                if j: jobs[jid] = j
        return dict(sorted(jobs.items(), key=lambda x: x[1].get('created_at', ''), reverse=True))

    def cleanup_old_jobs(self, hours=24):
        # Limpieza básica
        return 0 
        
    def clear_all_session(self):
        if os.path.exists(self.session_dir):
            shutil.rmtree(self.session_dir)
            os.makedirs(self.session_dir, exist_ok=True)
        return {"success": True}

session_manager = SessionManager()