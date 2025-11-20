from flask import Blueprint, jsonify, send_file
from job_persistence import session_manager
import os
from werkzeug.utils import secure_filename

session_bp = Blueprint('session_routes', __name__)

@session_bp.route('/session/jobs', methods=['GET'])
def get_jobs():
    return jsonify({"success": True, "jobs": session_manager.get_all_active_jobs()})

@session_bp.route('/session/jobs/<jid>', methods=['GET'])
def get_job(jid):
    j = session_manager.get_job(jid)
    if j: return jsonify({"success": True, "job": j})
    return jsonify({"error": "404"}), 404

@session_bp.route('/session/images/<jid>/<fname>', methods=['GET'])
def get_sess_img(jid, fname):
    path = os.path.join(session_manager.session_dir, secure_filename(jid), secure_filename(fname))
    if os.path.exists(path): return send_file(path)
    return jsonify({"error": "404"}), 404

@session_bp.route('/session/clear', methods=['POST'])
def clear():
    return jsonify(session_manager.clear_all_session())