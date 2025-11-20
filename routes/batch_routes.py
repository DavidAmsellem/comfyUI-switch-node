from flask import Blueprint, request, jsonify
from services.batch_service import ACTIVE_BATCHES, BATCH_LOCK, enforce_batch_throttle, process_all_workflows_simultaneously_with_tracking, cancel_batch_job
from services.workflow_service import get_available_workflows, filter_workflows_for_batch
from job_persistence import session_manager
import json, threading, time, uuid
from io import BytesIO

batch_bp = Blueprint('batch_routes', __name__)

@batch_bp.route('/process-batch', methods=['POST'])
def process_batch():
    try:
        if 'image' not in request.files: return jsonify({"error": "Falta imagen"}), 400
        img = request.files['image']
        
        conf = {}
        if 'batch_config' in request.form:
            conf = json.loads(request.form['batch_config'])
        
        # Inyectamos el nombre original para las carpetas
        conf['original_filename'] = img.filename 

        avail = get_available_workflows()
        filtered = filter_workflows_for_batch(conf, avail)
        
        if not filtered: return jsonify({"error": "No hay workflows coincidentes"}), 400

        jid = session_manager.create_job(job_type='batch', batch_config=conf)
        bid = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
        
        with BATCH_LOCK:
            ACTIVE_BATCHES[bid] = {
                "batch_id": bid, 
                "session_job_id": jid, 
                "status": "starting",
                "completed_workflows": 0, 
                "total_workflows": len(filtered),
                "failed": 0, 
                "successful": 0, 
                "results": [],
                "is_cancelled": False
            }
        
        session_manager.update_job(jid, batch_tracking_id=bid, total_workflows=len(filtered))

        enforce_batch_throttle(len(filtered))
        img_data = BytesIO(img.read())
        
        def run():
            process_all_workflows_simultaneously_with_tracking(img_data, filtered, conf, bid, jid)
        
        threading.Thread(target=run, daemon=True).start()
        
        return jsonify({
            "success": True, 
            "batch_id": bid, 
            "session_job_id": jid,
            "total_workflows": len(filtered) 
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@batch_bp.route('/batch-status/<bid>', methods=['GET'])
def status(bid):
    with BATCH_LOCK:
        if bid in ACTIVE_BATCHES: return jsonify(ACTIVE_BATCHES[bid])
    return jsonify({"error": "Not found"}), 404

@batch_bp.route('/cancel-batch/<bid>', methods=['POST'])
def cancel_route(bid):
    success, msg = cancel_batch_job(bid)
    if success:
        return jsonify({"success": True, "message": msg})
    else:
        return jsonify({"error": msg}), 404