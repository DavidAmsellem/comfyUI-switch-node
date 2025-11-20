#!/usr/bin/env python3
from flask import Flask, send_file, jsonify
from flask_cors import CORS
import os
from config import BASE_DIR
from routes.general_routes import general_bp
from routes.job_routes import job_bp
from routes.batch_routes import batch_bp
from routes.session_routes import session_bp

app = Flask(__name__)
CORS(app)

# Registrar rutas
app.register_blueprint(general_bp)
app.register_blueprint(job_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(session_bp)

@app.route('/')
def serve_client():
    path = os.path.join(BASE_DIR, 'web_client_fixed.html')
    if os.path.exists(path): return send_file(path)
    return send_file(os.path.join(BASE_DIR, 'web_client.html'))

@app.route('/web_client_fixed.html')
def serve_fixed():
    path = os.path.join(BASE_DIR, 'web_client_fixed.html')
    if os.path.exists(path): return send_file(path)
    return jsonify({"error": "No encontrado"}), 404

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        print("🚀 Iniciando ComfyUI API REST Modularizada...")
    app.run(host='0.0.0.0', port=5000, debug=True)