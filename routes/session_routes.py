from flask import Blueprint, jsonify, send_file, request
from job_persistence import individual_session_manager
from batch_persistence import batch_session_manager
import os
from werkzeug.utils import secure_filename

session_bp = Blueprint('session_routes', __name__)

@session_bp.route('/session/jobs', methods=['GET'])
def get_jobs():
    """Devuelve TODOS los jobs (individuales + batch)"""
    individual_jobs = individual_session_manager.get_all_active_jobs()
    batch_jobs = batch_session_manager.get_all_active_jobs()
    
    all_jobs = individual_jobs + batch_jobs
    # Ordenar por fecha de creación (más recientes primero)
    all_jobs.sort(key=lambda x: x.get('created_at', 0), reverse=True)
    
    return jsonify({
        "success": True, 
        "jobs": all_jobs
    })

@session_bp.route('/session/jobs/<jid>', methods=['GET'])
def get_job(jid):
    # Limpiar ID si viene con prefijo
    clean_id = jid.replace('restored_', '')
    
    from utils.logger import log_info
    log_info(f"🔍 [GET_JOB] Consultando estado del job: {clean_id[:8]}")
    
    # Intentar primero en individual, luego en batch
    j = individual_session_manager.get_job(clean_id)
    if not j:
        j = batch_session_manager.get_job(clean_id)
    
    if j: 
        log_info(f"📋 [GET_JOB] Job {clean_id[:8]} encontrado - Status: {j.get('status')} - Results: {len(j.get('results', []))}")
        return jsonify(j)
    
    log_info(f"❌ [GET_JOB] Job {clean_id[:8]} no encontrado")
    return jsonify({"error": "Job not found"}), 404

@session_bp.route('/session/images/<jid>/<fname>', methods=['GET'])
def get_sess_img(jid, fname):
    clean_id = jid.replace('restored_', '')
    
    # Intentar en directorio de individual primero
    path_individual = os.path.join(individual_session_manager.session_dir, secure_filename(clean_id), secure_filename(fname))
    if os.path.exists(path_individual): 
        return send_file(path_individual)
    
    # Si no está, intentar en batch
    path_batch = os.path.join(batch_session_manager.session_dir, secure_filename(clean_id), secure_filename(fname))
    if os.path.exists(path_batch): 
        return send_file(path_batch)
    
    return jsonify({"error": "Image not found"}), 404

# --- ESTA ES LA RUTA QUE FALTABA (ERROR 404) ---
@session_bp.route('/session/cleanup', methods=['POST'])
def cleanup():
    data = request.json or {}
    hours = data.get('hours', 24)
    
    # Limpiar ambos sistemas
    count_individual = individual_session_manager.cleanup_old_jobs(hours)
    count_batch = batch_session_manager.cleanup_old_jobs(hours)
    
    return jsonify({
        "success": True, 
        "cleaned_count": count_individual + count_batch,
        "individual_cleaned": count_individual,
        "batch_cleaned": count_batch
    })

@session_bp.route('/session/clear', methods=['POST'])
def clear():
    # Limpiar ambos sistemas
    individual_session_manager.clear_all_session()
    batch_session_manager.clear_all_session()
    return jsonify({"success": True})