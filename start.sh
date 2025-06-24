#!/bin/bash

# Script mejorado de inicio/reinicio para la API REST de ComfyUI
set -e

# Detener procesos Flask previos
if pgrep -f "flask run|app_simple.py" > /dev/null; then
    echo "🛑 Deteniendo instancias previas de Flask..."
    pkill -f "flask run"
    pkill -f "app_simple.py"
    sleep 2
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install -r requirements.txt

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p temp_uploads
mkdir -p outputs

# Cargar variables de entorno si existe .env
if [ -f ".env" ]; then
    echo "🔧 Cargando configuración desde .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

API_PORT=${API_PORT:-5000}

# Mostrar información
clear
cat <<EOF
🚀 Iniciando API REST para ComfyUI
==================================
📡 La API se iniciará en: http://localhost:${API_PORT}

Endpoints principales:
  GET  /health
  POST /process-image
  GET  /get-image/<name>
  GET  /workflow-groups

EOF

# Lanzar la app principal (app_simple.py)
echo "🔄 Lanzando servidor..."
exec python app_simple.py
