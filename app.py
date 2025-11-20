#!/usr/bin/env python3
from flask import Flask, send_file, jsonify, send_from_directory
from flask_cors import CORS
import os
from config import BASE_DIR
from routes.general_routes import general_bp
from routes.job_routes import job_bp
from routes.batch_routes import batch_bp
from routes.session_routes import session_bp

app = Flask(__name__)
CORS(app)

# Registrar rutas (Blueprints)
app.register_blueprint(general_bp)
app.register_blueprint(job_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(session_bp)

@app.route('/')
def serve_client():
    # Intenta servir primero el cliente corregido
    path = os.path.join(BASE_DIR, 'web_client_fixed.html')
    if os.path.exists(path): return send_file(path)
    return send_file(os.path.join(BASE_DIR, 'web_client.html'))

@app.route('/web_client_fixed.html')
def serve_fixed():
    path = os.path.join(BASE_DIR, 'web_client_fixed.html')
    if os.path.exists(path): return send_file(path)
    return jsonify({"error": "No encontrado"}), 404

# --- RUTA PARA EL SCRIPT JS ---
@app.route('/js/<path:filename>')
def serve_js_modules(filename):
    # Esto busca los archivos dentro de la carpeta 'js' que está en BASE_DIR
    js_folder = os.path.join(BASE_DIR, 'js')
    
    # Verifica si el archivo existe antes de enviarlo (opcional, send_from_directory maneja 404s)
    if not os.path.exists(os.path.join(js_folder, filename)):
        return jsonify({"error": f"Archivo JS {filename} no encontrado"}), 404
        
    return send_from_directory(js_folder, filename)

# --- NUEVA RUTA PARA EL CSS (ESTO FALTABA) ---
@app.route('/styles.css')
def serve_css():
    path = os.path.join(BASE_DIR, 'styles.css')
    if os.path.exists(path): return send_file(path)
    return jsonify({"error": "styles.css no encontrado"}), 404

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        print("🚀 Iniciando ComfyUI API REST Modularizada...")
    
    app.run(host='0.0.0.0', port=5000, debug=True)