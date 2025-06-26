import os
import json
import shutil
from PIL import Image

WORKFLOWS_DIR = 'workflows'
OUTPUT_DIR = 'imagenes_nodo_104'
USER_IMAGES_DIR = os.path.expanduser('~/Imágenes')  # Carpeta de imágenes del usuario
os.makedirs(OUTPUT_DIR, exist_ok=True)

IMAGE_SEARCH_DIRS = [
    '.',  # actual y subcarpetas
    USER_IMAGES_DIR
]

def find_image(image_name):
    for search_dir in IMAGE_SEARCH_DIRS:
        for root, _, files in os.walk(search_dir):
            if image_name in files:
                return os.path.join(root, image_name)
    return None

def save_node104_image(workflow_path):
    with open(workflow_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    node_104 = data.get('104')
    if not node_104 or node_104.get('class_type') != 'LoadImage':
        return False
    image_name = node_104['inputs'].get('image')
    if not image_name:
        return False
    image_path = find_image(image_name)
    if image_path:
        workflow_base = os.path.splitext(os.path.basename(workflow_path))[0]
        ext = os.path.splitext(image_name)[1]
        dest_path = os.path.join(OUTPUT_DIR, f'{workflow_base}{ext}')
        shutil.copy2(image_path, dest_path)
        print(f"Guardada: {dest_path}")
        return True
    print(f"Imagen {image_name} no encontrada para workflow {workflow_path}")
    return False

def main():
    for root, _, files in os.walk(WORKFLOWS_DIR):
        for file in files:
            if file.endswith('.json'):
                workflow_path = os.path.join(root, file)
                save_node104_image(workflow_path)

if __name__ == '__main__':
    main()
