#!/usr/bin/env python3
"""
Script de prueba para la API REST de ComfyUI.
Incluye ejemplos de uso de todos los endpoints.
"""

import requests
import json
import time
import os
from io import BytesIO
from PIL import Image

# Configuración
API_BASE_URL = "http://localhost:5000"

def test_health():
    """Probar endpoint de salud."""
    print("🔍 Probando endpoint de salud...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_workflow_info():
    """Probar endpoint de información del workflow."""
    print("\n📋 Probando información del workflow...")
    try:
        response = requests.get(f"{API_BASE_URL}/workflow-info")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Workflow file: {data['workflow_file']}")
            print(f"Total nodes: {data['total_nodes']}")
            print(f"LoadImage nodes: {len(data['load_image_nodes'])}")
            for node in data['load_image_nodes']:
                print(f"  - Node ID {node['id']}: {node['current_image']}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_test_image():
    """Crear una imagen de prueba."""
    print("\n🎨 Creando imagen de prueba...")
    
    # Crear una imagen simple de prueba
    img = Image.new('RGB', (512, 512), color='red')
    
    # Añadir un rectángulo azul
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 400, 400], fill='blue')
    
    # Guardar como bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    print("✅ Imagen de prueba creada (512x512, roja con rectángulo azul)")
    return img_bytes

def test_process_image():
    """Probar procesamiento de imagen."""
    print("\n🖼️  Probando procesamiento de imagen...")
    
    # Crear imagen de prueba
    test_img = create_test_image()
    
    try:
        files = {'image': ('test_image.png', test_img, 'image/png')}
        
        print("📤 Enviando imagen a procesar...")
        response = requests.post(f"{API_BASE_URL}/process-image", files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Procesamiento exitoso!")
            print(f"Prompt ID: {data['prompt_id']}")
            print(f"Imágenes generadas: {len(data['output_images'])}")
            
            for i, img_info in enumerate(data['output_images']):
                print(f"  Imagen {i+1}:")
                print(f"    Filename: {img_info['filename']}")
                print(f"    Subfolder: '{img_info['subfolder']}'")
                print(f"    Type: {img_info['type']}")
            
            return data['output_images']
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_download_image(image_info):
    """Probar descarga de imagen."""
    print(f"\n⬇️  Probando descarga de imagen: {image_info['filename']}")
    
    try:
        params = {
            'subfolder': image_info['subfolder'],
            'type': image_info['type']
        }
        
        response = requests.get(
            f"{API_BASE_URL}/get-image/{image_info['filename']}", 
            params=params
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            # Guardar imagen
            output_filename = f"downloaded_{image_info['filename']}"
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Imagen descargada como: {output_filename}")
            print(f"Tamaño: {len(response.content)} bytes")
            
            # Verificar que es una imagen válida
            try:
                with Image.open(output_filename) as img:
                    print(f"Dimensiones: {img.size}")
                    print(f"Formato: {img.format}")
            except Exception as e:
                print(f"⚠️  Warning: No se pudo abrir como imagen: {e}")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_with_real_image(image_path):
    """Probar con una imagen real del usuario."""
    if not os.path.exists(image_path):
        print(f"❌ Archivo no encontrado: {image_path}")
        return None
    
    print(f"\n🖼️  Probando con imagen real: {image_path}")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(f"{API_BASE_URL}/process-image", files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Procesamiento exitoso!")
            print(f"Prompt ID: {data['prompt_id']}")
            return data['output_images']
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Función principal para ejecutar todas las pruebas."""
    print("🚀 Iniciando pruebas de la API REST para ComfyUI")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health():
        print("❌ API no disponible. Verificar que el servidor esté ejecutándose.")
        return
    
    # Test 2: Workflow info
    test_workflow_info()
    
    # Test 3: Process image (con imagen de prueba)
    output_images = test_process_image()
    
    # Test 4: Download images
    if output_images:
        for img_info in output_images:
            test_download_image(img_info)
    
    # Test 5: Con imagen real (si se proporciona)
    real_image_path = input("\n🔄 ¿Quieres probar con una imagen real? Ingresa la ruta (o Enter para omitir): ").strip()
    if real_image_path:
        real_output_images = test_with_real_image(real_image_path)
        if real_output_images:
            for img_info in real_output_images:
                test_download_image(img_info)
    
    print("\n✅ Pruebas completadas!")
    print("📁 Revisa los archivos descargados en el directorio actual.")

if __name__ == "__main__":
    main()
