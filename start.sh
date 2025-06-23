#!/bin/bash

# Script de inicio para la API REST de ComfyUI

set -e

echo "🚀 Iniciando API REST para ComfyUI"
echo "=================================="

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado"
    exit 1
fi

# Verificar si pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 no está instalado"
    exit 1
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

# Verificar que existe el archivo de workflow
if [ ! -f "workflow_cuadro_bedroomV15x202.json" ]; then
    echo "❌ Error: No se encontró el archivo workflow_cuadro_bedroomV15x202.json"
    echo "   Asegúrate de que el archivo esté en el directorio actual."
    exit 1
fi

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p temp_uploads
mkdir -p outputs

# Verificar conexión con ComfyUI
echo "🔍 Verificando conexión con ComfyUI..."
COMFYUI_HOST=${COMFYUI_HOST:-localhost}
COMFYUI_PORT=${COMFYUI_PORT:-8188}

if ! curl -s "http://${COMFYUI_HOST}:${COMFYUI_PORT}/system_stats" > /dev/null; then
    echo "⚠️  Advertencia: No se pudo conectar con ComfyUI en ${COMFYUI_HOST}:${COMFYUI_PORT}"
    echo "   Asegúrate de que ComfyUI esté ejecutándose antes de procesar imágenes."
    echo ""
fi

# Configurar variables de entorno si existe .env
if [ -f ".env" ]; then
    echo "🔧 Cargando configuración desde .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Obtener puerto de la API
API_PORT=${API_PORT:-5000}

echo ""
echo "✅ Configuración completada!"
echo ""
echo "📡 La API se iniciará en: http://localhost:${API_PORT}"
echo ""
echo "📋 Endpoints disponibles:"
echo "   GET  /health           - Verificar estado del servicio"
echo "   POST /process-image    - Procesar imagen"
echo "   GET  /get-image/<name> - Descargar imagen procesada"
echo "   GET  /workflow-info    - Información del workflow"
echo ""
echo "🔧 Para probar la API, ejecuta: python test_api.py"
echo ""
echo "🚀 Iniciando servidor..."
echo ""

# Iniciar la aplicación
python app.py
