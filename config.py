import os

# Configuración de Host
COMFYUI_HOST = os.getenv('COMFYUI_HOST', 'localhost')
COMFYUI_PORT = os.getenv('COMFYUI_PORT', '8188')
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

# Directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMFYUI_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
COMFYUI_INPUT_DIR = os.path.join(COMFYUI_ROOT, 'input')
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_ROOT, 'output')
WORKFLOWS_DIR = os.path.join(BASE_DIR, 'workflows')
TEMP_UPLOADS_DIR = os.path.join(BASE_DIR, 'temp_uploads')
OUR_OUTPUT_DIR = os.path.join(os.path.dirname(COMFYUI_ROOT), 'output')

for directory in [COMFYUI_INPUT_DIR, COMFYUI_OUTPUT_DIR, TEMP_UPLOADS_DIR, OUR_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

WORKFLOW_CONFIG = {
    'load_image_node_id': '699',
    'save_image_node_id': '704',
    'frame_node_id': '692',
    'allowed_extensions': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
    'frame_colors': ['none', 'black', 'white', 'brown', 'gold'],
    'frame_node_defaults': {
        'frame_width': 50,
        'depth_enabled': True,
        'depth_intensity': 0.8,
        'perspective_style': 'realistic',
        'wall_color': 240,
        'upscale_workflow': False
    }
}