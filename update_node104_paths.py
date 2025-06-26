import os
import json

WORKFLOWS_DIR = 'workflows'
IMAGES_DIR = 'imagenes_nodo_104'


def update_node104_image_path(workflow_path):
    with open(workflow_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    node_104 = data.get('104')
    if not node_104 or node_104.get('class_type') != 'LoadImage':
        return False
    workflow_base = os.path.splitext(os.path.basename(workflow_path))[0]
    # Buscar la extensión de la imagen copiada
    for ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
        image_path = os.path.join(IMAGES_DIR, f'{workflow_base}{ext}')
        if os.path.exists(image_path):
            new_image_relpath = os.path.join(IMAGES_DIR, f'{workflow_base}{ext}')
            node_104['inputs']['image'] = new_image_relpath
            with open(workflow_path, 'w', encoding='utf-8') as fw:
                json.dump(data, fw, indent=2, ensure_ascii=False)
            print(f"Actualizado nodo 104 en {workflow_path} -> {new_image_relpath}")
            return True
    print(f"No se encontró imagen copiada para workflow {workflow_path}")
    return False

def main():
    for root, _, files in os.walk(WORKFLOWS_DIR):
        for file in files:
            if file.endswith('.json'):
                workflow_path = os.path.join(root, file)
                update_node104_image_path(workflow_path)

if __name__ == '__main__':
    main()
