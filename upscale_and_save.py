import os
from PIL import Image
import sys

def upscale_and_save(input_path, output_path, scale=2):
    img = Image.open(input_path)
    new_size = (img.width * scale, img.height * scale)
    upscaled = img.resize(new_size, Image.LANCZOS)
    upscaled.save(output_path, format='PNG')
    print(f"Upscaled {input_path} -> {output_path} ({new_size[0]}x{new_size[1]})")

def process_folder(folder_path, scale=2):
    original_path = os.path.join(folder_path, 'original.png')
    upscaled_path = os.path.join(folder_path, 'original_upscaled.png')
    if os.path.exists(original_path):
        upscale_and_save(original_path, upscaled_path, scale=scale)
    else:
        print(f"No se encontró {original_path}")

def main():
    outputs_dir = 'outputs'
    scale = 2
    if len(sys.argv) > 1:
        try:
            scale = int(sys.argv[1])
        except Exception:
            pass
    for folder in os.listdir(outputs_dir):
        folder_path = os.path.join(outputs_dir, folder)
        if os.path.isdir(folder_path):
            process_folder(folder_path, scale=scale)

if __name__ == '__main__':
    main()
