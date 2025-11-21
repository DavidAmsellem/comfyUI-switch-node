from flask import Blueprint, jsonify, send_file, request
from job_persistence import session_manager
import os
from werkzeug.utils import secure_filename

session_bp = Blueprint('session_routes', __name__)

@session_bp.route('/session/jobs', methods=['GET'])
def get_jobs():
    return jsonify({
        "success": True, 
        "jobs": session_manager.get_all_active_jobs()
    })

@session_bp.route('/session/jobs/<jid>', methods=['GET'])
def get_job(jid):
    # Limpiar ID si viene con prefijo
    clean_id = jid.replace('restored_', '')
    
    from utils.logger import log_info
    log_info(f"🔍 [GET_JOB] Consultando estado del job: {clean_id[:8]}")
    
    j = session_manager.get_job(clean_id)
    
    if j: 
        log_info(f"📋 [GET_JOB] Job {clean_id[:8]} encontrado - Status: {j.get('status')} - Results: {len(j.get('results', []))}")
        return jsonify(j)
    
    log_info(f"❌ [GET_JOB] Job {clean_id[:8]} no encontrado")
    return jsonify({"error": "Job not found"}), 404

@session_bp.route('/session/images/<jid>/<fname>', methods=['GET'])
def get_sess_img(jid, fname):
    clean_id = jid.replace('restored_', '')
    path = os.path.join(session_manager.session_dir, secure_filename(clean_id), secure_filename(fname))
    if os.path.exists(path): 
        return send_file(path)
    return jsonify({"error": "Image not found"}), 404

# --- ESTA ES LA RUTA QUE FALTABA (ERROR 404) ---
@session_bp.route('/session/cleanup', methods=['POST'])
def cleanup():
    data = request.json or {}
    hours = data.get('hours', 24)
    count = session_manager.cleanup_old_jobs(hours)
    return jsonify({"success": True, "cleaned_count": count})

@session_bp.route('/session/clear', methods=['POST'])
def clear():
    return jsonify(session_manager.clear_all_session())