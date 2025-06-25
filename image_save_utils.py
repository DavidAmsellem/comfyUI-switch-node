import os
from werkzeug.utils import secure_filename
from PIL import Image
import io

def prepare_output_dir(file):
    """
    Crea una carpeta en outputs/ con el nombre base del archivo subido (sin extensión)
    y guarda la imagen original ahí como PNG. Devuelve el path de la carpeta y el path de la imagen original.
    """
    original_filename = secure_filename(file.filename)
    base_name = os.path.splitext(original_filename)[0]
    output_dir = os.path.join('outputs', base_name)
    os.makedirs(output_dir, exist_ok=True)
    original_path = os.path.join(output_dir, 'original.png')
    # Convertir a PNG usando PIL
    image = Image.open(file.stream)
    image.save(original_path, format='PNG')
    file.stream.seek(0)  # Reset stream por si se necesita después
    return output_dir, original_path, base_name

def save_generated_image(image_bytes, output_dir, filename):
    """
    Guarda una imagen generada (en bytes o formato PIL) en la carpeta de salida especificada como PNG.
    El nombre de archivo se fuerza a .png.
    """
    # Forzar extensión .png
    base_name = os.path.splitext(filename)[0]
    path = os.path.join(output_dir, base_name + '.png')
    image = Image.open(io.BytesIO(image_bytes))
    image.save(path, format='PNG')
    return path

def save_original_to_comfyui_input(file, base_name, comfyui_input_folder):
    """
    Guarda la imagen original como PNG en la carpeta de input de ComfyUI, en una subcarpeta con el nombre base.
    Devuelve el path relativo para el workflow.
    """
    input_subfolder = os.path.join(comfyui_input_folder, base_name)
    os.makedirs(input_subfolder, exist_ok=True)
    input_path = os.path.join(input_subfolder, 'original.png')
    image = Image.open(file.stream)
    image.save(input_path, format='PNG')
    file.stream.seek(0)
    # El workflow debe recibir la ruta relativa desde la carpeta input
    return os.path.join(base_name, 'original.png')
