import os
import shutil
import uuid
import datetime
from io import BytesIO
from PIL import Image
from werkzeug.utils import secure_filename
from io import BytesIO

def get_comfyui_output_dir():
    """Devuelve la ruta absoluta a la carpeta output de ComfyUI."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'output'))
    print(f"📁 [get_comfyui_output_dir] ComfyUI output dir: {base_dir}")
    
    # Verificar si el directorio existe, crearlo si no
    if not os.path.exists(base_dir):
        print(f"📁 [get_comfyui_output_dir] Creando directorio de output que no existía: {base_dir}")
        try:
            os.makedirs(base_dir, exist_ok=True)
            print(f"✅ [get_comfyui_output_dir] Directorio de output creado exitosamente")
        except Exception as e:
            print(f"❌ [get_comfyui_output_dir] ERROR creando directorio de output: {str(e)}")
            # No propagar el error, intentar seguir con el directorio
    else:
        print(f"✅ [get_comfyui_output_dir] Directorio de output ya existe")
        
    # Verificar permisos de escritura
    try:
        test_file = os.path.join(base_dir, "__test_write__.tmp")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print(f"✅ [get_comfyui_output_dir] Verificación de permisos: escritura OK")
    except Exception as e:
        print(f"⚠️ [get_comfyui_output_dir] ADVERTENCIA: No se puede escribir en directorio de output: {str(e)}")
        
    return base_dir

def get_comfyui_input_dir():
    """Devuelve la ruta absoluta a la carpeta input de ComfyUI."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'input'))
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def find_image_in_outputs(filename, base_name=None, subfolder=None, output_root=None):
    """
    Busca una imagen en el directorio de salida de ComfyUI.
    Devuelve la ruta absoluta si la encuentra, o None si no existe.
    
    La búsqueda se realiza en:
    1. ComfyUI/output/base_name/ (carpeta específica por nombre base)
    2. ComfyUI/output/subfolder/ (carpeta específica por nombre de workflow)
    3. ComfyUI/output/ (directorio raíz)
    """
    if output_root is None:
        output_root = get_comfyui_output_dir()
    
    print(f"🔍 Buscando imagen '{filename}' con base_name='{base_name}', subfolder='{subfolder}'")
    print(f"📁 Directorio de búsqueda: {output_root}")
        
    possible_paths = []
    
    # 1. ComfyUI/output/base_name/filename (prioridad más alta)
    if base_name:
        comfy_base_dir = os.path.join(output_root, base_name)
        comfy_base_path = os.path.join(comfy_base_dir, filename)
        possible_paths.append(comfy_base_path)
        print(f"🔎 Comprobando en {base_name}/: {comfy_base_path} (existe: {os.path.exists(comfy_base_path)})")
    
    # 2. ComfyUI/output/subfolder/filename
    if subfolder and subfolder != base_name:
        subfolder_path = os.path.join(output_root, subfolder, filename)
        possible_paths.append(subfolder_path)
        print(f"🔎 Comprobando en {subfolder}/: {subfolder_path} (existe: {os.path.exists(subfolder_path)})")
    
    # 3. ComfyUI/output/filename
    root_path = os.path.join(output_root, filename)
    possible_paths.append(root_path)
    print(f"🔎 Comprobando en raíz: {root_path} (existe: {os.path.exists(root_path)})")
    
    # Buscar la primera que exista
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Imagen encontrada en: {path}")
            return path
    
    # Si no se encuentra directamente, hacer una búsqueda simple recursiva solo en el output_root
    print(f"🔍 Realizando búsqueda recursiva en {output_root}")
    for root, dirs, files in os.walk(output_root):
        if filename in files:
            path = os.path.join(root, filename)
            print(f"✅ Imagen encontrada en búsqueda recursiva: {path}")
            return path
    
    print(f"⚠️ No se encontró la imagen: {filename}")
    return None

def find_image_by_pattern(base_filename, output_root=None):
    """
    Busca imágenes que coincidan con un patrón de nombre base.
    Por ejemplo, para 'cuadro_' encontrará 'cuadro_001.png', etc.
    
    Solo busca en el directorio output de ComfyUI y sus subcarpetas.
    """
    print(f"🔍 [find_image_by_pattern] Buscando imágenes que coincidan con patrón: {base_filename}")
    
    # Lista de directorios donde buscar
    search_dirs = []
    
    # ComfyUI output (único directorio de búsqueda)
    if output_root is None:
        output_root = get_comfyui_output_dir()
    search_dirs.append(output_root)
        
    print(f"📁 [find_image_by_pattern] Buscando solo en el directorio output de ComfyUI:")
    for i, d in enumerate(search_dirs):
        print(f"   {i+1}. {d}")
        
    matches = []
    try:
        # Buscar en cada directorio
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                print(f"   - Omitiendo directorio que no existe: {search_dir}")
                continue
                
            print(f"   - Buscando en: {search_dir}")
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file.lower().startswith(base_filename.lower()) or base_filename.lower() in file.lower():
                        full_path = os.path.join(root, file)
                        matches.append(full_path)
                        print(f"     ✅ Coincidencia encontrada: {full_path}")
        
        if not matches:
            print(f"❌ [find_image_by_pattern] No se encontraron coincidencias para patrón: {base_filename}")
            return None
            
        # Si hay múltiples coincidencias, devolver la primera
        if len(matches) > 1:
            print(f"ℹ️ [find_image_by_pattern] Múltiples coincidencias encontradas ({len(matches)}), usando la primera")
            
        # Verificar que el archivo es una imagen válida
        try:
            with Image.open(matches[0]) as img:
                print(f"✅ [find_image_by_pattern] Imagen seleccionada: {matches[0]}")
                print(f"   Dimensiones: {img.size[0]}x{img.size[1]}, Modo: {img.mode}")
        except Exception as e:
            print(f"⚠️ [find_image_by_pattern] El archivo encontrado no es una imagen válida: {str(e)}")
            
        return matches[0]
        
    except Exception as e:
        print(f"❌ [find_image_by_pattern] Error al buscar archivos: {str(e)}")
        return None

def save_image_to_outputs(img_bytes, filename, base_name=None, use_comfyui_output=True):
    """
    Guarda la imagen solo en la carpeta de salida de ComfyUI.
    
    Args:
        img_bytes: Los bytes de la imagen a guardar
        filename: Nombre del archivo
        base_name: Nombre base para la carpeta
        use_comfyui_output: Ignorado, siempre se usa la carpeta output de ComfyUI
    """
    # Usamos siempre la carpeta de salida de ComfyUI
    comfy_output = get_comfyui_output_dir()
    
    # Aseguramos que el nombre base sea válido
    if not base_name:
        base_name = "default"
    
    # Crear una única carpeta en ComfyUI/output
    output_dir = os.path.join(comfy_output, base_name)
    output_path = os.path.join(output_dir, filename)
    
    print(f"💾 [save_image_to_outputs] Guardando imagen en carpeta ComfyUI: {output_path}")
    
    # Asegurarse que la carpeta existe
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Intentar abrir la imagen para verificar validez
        img = None
        try:
            img = Image.open(BytesIO(img_bytes))
            print(f"📊 [save_image_to_outputs] Imagen válida: {img.size[0]}x{img.size[1]}, modo={img.mode}")
            
            # Guardar como PNG usando PIL para asegurar formato correcto
            img.save(output_path, format='PNG')
        except Exception as img_e:
            print(f"⚠️ [save_image_to_outputs] Error al procesar imagen con PIL: {str(img_e)}")
            print(f"   Guardando bytes directamente...")
            # Fallback: guardar bytes directamente
            with open(output_path, 'wb') as f:
                f.write(img_bytes)
                
        print(f"✅ [save_image_to_outputs] Imagen guardada en: {output_path}")
        print(f"   Tamaño del archivo: {len(img_bytes)/1024:.2f} KB")
        
        # Verificar que realmente se haya creado el archivo
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / 1024  # KB
            print(f"   Verificación: archivo existe, tamaño={file_size:.2f} KB")
            
            # Intentar abrir para verificar que es una imagen válida
            try:
                with Image.open(output_path) as check_img:
                    print(f"   Verificación: imagen válida, dimensiones={check_img.size}")
            except Exception as e:
                print(f"⚠️ [save_image_to_outputs] ADVERTENCIA: Archivo guardado no es imagen válida: {str(e)}")
        else:
            print(f"⚠️ [save_image_to_outputs] ALERTA: Archivo guardado pero no se encontró en disco: {output_path}")
            
    except Exception as e:
        print(f"❌ [save_image_to_outputs] ERROR guardando en {output_path}: {str(e)}")
        raise
    
    return output_path

def copy_to_portable(abs_image_path, filename, base_name=None):
    """
    Copia una imagen a múltiples ubicaciones para asegurar que sea accesible.
    
    Args:
        abs_image_path: Ruta absoluta de la imagen a copiar
        filename: Nombre del archivo en el destino
        base_name: Nombre de la subcarpeta donde guardar (si es None, se guarda en outputs/)
        
    Returns:
        Ruta donde se copió la imagen (versión portable)
    """
    print(f"\n================ COPIANDO IMAGEN A UBICACIONES PORTABLES ================")
    print(f"🔄 [copy_to_portable] Copiando imagen:")
    print(f"   - Origen: {abs_image_path}")
    print(f"   - Nombre destino: {filename}")
    print(f"   - Base name: {base_name}")
    
    # Lista de directorios donde copiar
    dest_dirs = []
    
    # 1. Carpeta portable local
    if base_name:
        local_dir = os.path.join('outputs', base_name)
    else:
        local_dir = 'outputs'
    try:
        os.makedirs(local_dir, exist_ok=True)
        dest_dirs.append(local_dir)
        print(f"📁 [copy_to_portable] Carpeta portable: {local_dir}")
    except Exception as e:
        print(f"⚠️ [copy_to_portable] Error creando carpeta portable: {str(e)}")
        
    # 2. Carpeta en ComfyUI output
    comfy_output = get_comfyui_output_dir()
    if base_name:
        comfy_dir = os.path.join(comfy_output, base_name)
    else:
        comfy_dir = comfy_output
    try:
        os.makedirs(comfy_dir, exist_ok=True)
        dest_dirs.append(comfy_dir)
        print(f"📁 [copy_to_portable] Carpeta en ComfyUI: {comfy_dir}")
    except Exception as e:
        print(f"⚠️ [copy_to_portable] Error creando carpeta en ComfyUI: {str(e)}")
    
    # Copiar a todas las ubicaciones
    successful_copies = []
    for dest_dir in dest_dirs:
        dest_path = os.path.join(dest_dir, filename)
        try:
            # Copiar el archivo (reemplazar si existe)
            print(f"📦 [copy_to_portable] Copiando a: {dest_path}")
            shutil.copy2(abs_image_path, dest_path)
            
            # Verificar que la copia se realizó correctamente
            if os.path.exists(dest_path):
                file_size = os.path.getsize(dest_path) / 1024  # KB
                print(f"✅ [copy_to_portable] Archivo copiado correctamente, tamaño={file_size:.2f} KB")
                successful_copies.append(dest_path)
            else:
                print(f"⚠️ [copy_to_portable] ALERTA: El archivo no existe después de copiar: {dest_path}")
        except Exception as e:
            print(f"❌ [copy_to_portable] Error copiando archivo a {dest_path}: {str(e)}")
    
    # Devolver la primera ruta portable (local) o None si no se pudo copiar
    portable_path = os.path.join(local_dir, filename)
    print(f"🔄 [copy_to_portable] Copia completada. Ruta portable: {portable_path}")
    print(f"================== FIN COPIADO IMAGEN ==================\n")
    return portable_path

def save_image_to_comfyui(file):
    """Guarda la imagen en el directorio de ComfyUI/input y devuelve el nombre de archivo único."""
    if not file or file.filename == '':
        raise ValueError("No se proporcionó ningún archivo")
    
    # Generar nombre único
    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    comfyui_input_dir = get_comfyui_input_dir()
    comfyui_path = os.path.join(comfyui_input_dir, unique_filename)
    file.save(comfyui_path)
    
    return unique_filename

def save_image_to_comfyui_with_path(image_file, relative_path):
    """Guarda la imagen en la ruta relativa a ComfyUI/input."""
    comfyui_input_dir = get_comfyui_input_dir()
    full_path = os.path.join(comfyui_input_dir, *relative_path.replace('\\', '/').split('/'))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    image_file.save(full_path)
    return full_path

def upscale_image(input_path, output_path=None, scale=2):
    """Upscalea una imagen y la guarda en output_path."""
    try:
        img = Image.open(input_path)
        new_size = (img.width * scale, img.height * scale)
        print(f"🔍 [upscale_image] Redimensionando imagen de {img.width}x{img.height} a {new_size[0]}x{new_size[1]}")
        upscaled = img.resize(new_size, Image.LANCZOS)
        
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_upscaled{ext}"
        
        # Asegurar que el directorio de salida existe
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
        upscaled.save(output_path, format='PNG')
        print(f"✅ [upscale_image] Imagen guardada en: {output_path}")
        
        # Verificar que la imagen se guardó correctamente
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / 1024  # KB
            print(f"   - Verificación: archivo existe, tamaño={file_size:.2f} KB")
        else:
            print(f"⚠️ [upscale_image] ADVERTENCIA: La imagen upscaleada no existe en disco: {output_path}")
            
        return output_path
    except Exception as e:
        print(f"❌ [upscale_image] ERROR al upscalear imagen: {str(e)}")
        raise

def secure_image_path(filename, base_name=None):
    """Asegura que un nombre de archivo y base_name son seguros para rutas."""
    safe_filename = secure_filename(filename)
    safe_base_name = secure_filename(base_name) if base_name else None
    return safe_filename, safe_base_name

def get_image_from_output(image_info, base_name=None):
    """
    Busca y carga una imagen basada en su información.
    Devuelve los bytes de la imagen y la ruta donde se encontró.
    """
    print(f"\n================ BÚSQUEDA DE IMAGEN ================")
    
    if 'filename' not in image_info:
        print(f"⚠️ [get_image_from_output] Error: image_info no contiene 'filename': {image_info}")
        return None, None
    
    # Extraer output_root de image_info si está presente
    output_root = image_info.get('output_root', None)
    filename = image_info['filename']
    subfolder = image_info.get('subfolder', '')
    
    print(f"🔍 [get_image_from_output] Buscando imagen: {filename}")
    print(f"   Parámetros de búsqueda:")
    print(f"   - Filename: {filename}")
    print(f"   - Base name: {base_name}")
    print(f"   - Subfolder: {subfolder}")
    print(f"   - Output root: {output_root}")
    
    # Comprobar si output_root existe
    if output_root and not os.path.exists(output_root):
        print(f"⚠️ [get_image_from_output] ADVERTENCIA: El directorio output_root no existe: {output_root}")
        print(f"   Intentando crear el directorio...")
        try:
            os.makedirs(output_root, exist_ok=True)
            print(f"✅ Directorio creado exitosamente")
        except Exception as e:
            print(f"❌ Error al crear directorio: {str(e)}")
    
    # Intentar encontrar la imagen
    print(f"🔍 [get_image_from_output] Buscando imagen usando find_image_in_outputs...")
    img_path = find_image_in_outputs(
        filename, 
        base_name=base_name, 
        subfolder=subfolder,
        output_root=output_root
    )
    
    # Si no se encuentra directamente, buscar por patrón
    if not img_path and '_' in filename:
        base_name_pattern = filename.split('_')[0]
        print(f"🔍 [get_image_from_output] Intentando buscar por patrón: {base_name_pattern}")
        alt_path = find_image_by_pattern(base_name_pattern, output_root=output_root)
        if alt_path:
            img_path = alt_path
            # Actualizar nombre si encontramos una alternativa
            image_info['original_filename'] = filename
            image_info['filename'] = os.path.basename(alt_path)
            print(f"✅ [get_image_from_output] Imagen alternativa encontrada: {img_path}")
            
            # Verificar que la imagen sea válida
            try:
                with Image.open(alt_path) as img:
                    print(f"   Verificación: imagen válida, dimensiones={img.size[0]}x{img.size[1]}, modo={img.mode}")
            except Exception as e:
                print(f"⚠️ [get_image_from_output] La imagen alternativa no es válida: {str(e)}")
    
    if img_path:
        print(f"📥 [get_image_from_output] Cargando imagen desde: {img_path}")
        try:
            # Verificar tamaño del archivo
            file_size = os.path.getsize(img_path) / 1024  # KB
            print(f"   Tamaño del archivo: {file_size:.2f} KB")
            
            # Cargar bytes de la imagen
            with open(img_path, 'rb') as f:
                img_bytes = f.read()
                
            print(f"✅ [get_image_from_output] Imagen cargada exitosamente: {len(img_bytes)/1024:.2f} KB")
            
            # Verificar que sea una imagen válida
            try:
                img = Image.open(BytesIO(img_bytes))
                print(f"   Verificación: imagen válida, dimensiones={img.size[0]}x{img.size[1]}, modo={img.mode}")
                
                # Asegurarse de que siempre guardamos una copia de la imagen en la carpeta correcta de output
                if base_name:
                    comfy_output = get_comfyui_output_dir()
                    output_dir = os.path.join(comfy_output, base_name)
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Solo copiar si la imagen no está ya en esta carpeta
                    if not img_path.startswith(output_dir):
                        dest_filename = os.path.basename(img_path)
                        dest_path = os.path.join(output_dir, dest_filename)
                        
                        if not os.path.exists(dest_path):
                            try:
                                img.save(dest_path, format='PNG')
                                print(f"✅ [get_image_from_output] Imagen copiada a carpeta output específica: {dest_path}")
                            except Exception as e:
                                print(f"⚠️ [get_image_from_output] Error al copiar imagen: {str(e)}")
            except Exception as e:
                print(f"⚠️ [get_image_from_output] Advertencia: Los bytes leídos no son una imagen válida: {str(e)}")
                
            print(f"================== FIN BÚSQUEDA ==================\n")
            return img_bytes, img_path
            
        except Exception as e:
            print(f"❌ [get_image_from_output] Error al cargar la imagen: {str(e)}")
    
    print(f"❌ [get_image_from_output] No se pudo encontrar la imagen: {filename}")
    print(f"================== FIN BÚSQUEDA ==================\n")
    return None, None

def prepare_output_dir(file, use_comfyui_output=True, original_filename=None):
    """
    Crea UN ÚNICO directorio de salida en ComfyUI/output para guardar las imágenes.
    Devuelve la ruta del directorio, ruta de la imagen original y el nombre base.
    
    Args:
        file: El archivo de imagen subido
        use_comfyui_output: Se ignora, siempre se usa ComfyUI output
        original_filename: Nombre de archivo original (para crear subcarpeta específica)
    """
    print(f"\n================ PREPARANDO DIRECTORIO DE SALIDA ================")
    
    # Usar original_filename si está disponible, de lo contrario usar filename del archivo
    base_filename = original_filename if original_filename else file.filename.rsplit('.', 1)[0]
    # Aseguramos que el nombre base no incluya la extensión del archivo
    if '.' in base_filename:
        base_filename = base_filename.rsplit('.', 1)[0]
    
    # Usar solo el nombre del archivo limpio y seguro
    base_name = secure_filename(base_filename)
    print(f"📂 [prepare_output_dir] Nombre base: {base_name}")
    
    # Obtener el directorio de salida de ComfyUI
    comfy_output = get_comfyui_output_dir()
    
    # Crear SOLO UN directorio en el output de ComfyUI
    output_dir = os.path.join(comfy_output, base_name)
    print(f"📂 [prepare_output_dir] Directorio de salida: {output_dir}")
    
    # Crear el directorio
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"✅ [prepare_output_dir] Directorio creado: {output_dir}")
    except Exception as e:
        print(f"❌ [prepare_output_dir] Error creando directorio {output_dir}: {str(e)}")
    
    # Guardar imagen original como PNG
    original_filename = "original.png"
    original_path = os.path.join(output_dir, original_filename)
    print(f"💾 [prepare_output_dir] Guardando imagen original: {original_path}")
    
    try:
        # Convertir y guardar como PNG
        img = Image.open(file.stream)
        print(f"📊 [prepare_output_dir] Imagen cargada: {img.size[0]}x{img.size[1]}, modo={img.mode}")
        img.save(original_path, format='PNG')
        print(f"✅ [prepare_output_dir] Imagen original guardada como PNG")
        
        # Verificar que el archivo se guardó correctamente
        if os.path.exists(original_path):
            file_size = os.path.getsize(original_path) / 1024  # KB
            print(f"   - Verificación: archivo existe, tamaño={file_size:.2f} KB")
        else:
            print(f"⚠️ [prepare_output_dir] ALERTA: El archivo no existe en disco después de guardar")
    except Exception as e:
        print(f"❌ [prepare_output_dir] Error guardando imagen original: {str(e)}")
        raise
        
    file.stream.seek(0)  # Reset el stream para uso posterior
    
    print(f"================== FIN PREPARACIÓN DIRECTORIO ==================\n")
    # Devolvemos la información del directorio
    return output_dir, original_path, base_name

def save_original_to_comfyui_input(file, base_name, comfyui_input_folder=None):
    """
    Guarda la imagen original como PNG en la carpeta de input de ComfyUI.
    Devuelve el path relativo para el workflow.
    """
    if comfyui_input_folder is None:
        comfyui_input_folder = get_comfyui_input_dir()
        
    # Ya no creamos subcarpeta, guardamos directamente en input
    input_path = os.path.join(comfyui_input_folder, f"{base_name}.png")
    
    print(f"📁 [save_original_to_comfyui_input] Guardando imagen original en: {input_path}")
    
    # Guardar original en input de ComfyUI
    try:
        image = Image.open(file.stream)
        print(f"📊 [save_original_to_comfyui_input] Imagen cargada: {image.size[0]}x{image.size[1]}, modo={image.mode}")
        image.save(input_path, format='PNG')
        
        # Verificar que se guardó correctamente
        if os.path.exists(input_path):
            file_size = os.path.getsize(input_path) / 1024  # KB
            print(f"✅ [save_original_to_comfyui_input] Imagen guardada correctamente, tamaño={file_size:.2f} KB")
        else:
            print(f"⚠️ [save_original_to_comfyui_input] ALERTA: La imagen no existe en disco: {input_path}")
    except Exception as e:
        print(f"❌ [save_original_to_comfyui_input] ERROR guardando imagen: {str(e)}")
        raise
        
    file.stream.seek(0)  # Reset el stream para uso posterior
    
    # El workflow debe recibir la ruta relativa desde la carpeta input
    return os.path.basename(input_path)

def save_generated_image(image_bytes, output_dir, filename, force_base_name=None, use_comfyui_output=True):
    """
    Guarda una imagen generada en múltiples ubicaciones para asegurar que se pueda encontrar después.
    El nombre de archivo se fuerza a .png.
    
    Args:
        image_bytes: Los bytes de la imagen a guardar
        output_dir: Directorio de salida principal
        filename: Nombre del archivo
        force_base_name: Si se proporciona, se usa como nombre base para las subcarpetas
        use_comfyui_output: Si es True, también guarda en la carpeta de salida de ComfyUI
    """
    print(f"\n================ GUARDANDO IMAGEN GENERADA ================")
    print(f"📁 [save_generated_image] Guardando imagen: {filename}")
    
    # Crear lista de directorios donde guardar
    save_dirs = []
    
    # 1. Directorio proporcionado (principal)
    if os.path.exists(output_dir) or True:  # Intentar crear si no existe
        try:
            os.makedirs(output_dir, exist_ok=True)
            save_dirs.append(output_dir)
            print(f"📂 [save_generated_image] Carpeta primaria: {output_dir}")
        except Exception as e:
            print(f"⚠️ [save_generated_image] Error creando carpeta primaria: {str(e)}")
    
    # 2. Directorio de ComfyUI output (siempre)
    comfy_output = get_comfyui_output_dir()
    if not output_dir.startswith(comfy_output):
        dir_basename = os.path.basename(output_dir)
        comfy_output_dir = os.path.join(comfy_output, dir_basename)
        try:
            os.makedirs(comfy_output_dir, exist_ok=True)
            save_dirs.append(comfy_output_dir)
            print(f"📂 [save_generated_image] Carpeta en ComfyUI output: {comfy_output_dir}")
        except Exception as e:
            print(f"⚠️ [save_generated_image] Error creando carpeta en ComfyUI output: {str(e)}")
    
    # 3. Añadir también carpeta portable "outputs" local
    portable_dir = os.path.join('outputs', os.path.basename(output_dir))
    try:
        os.makedirs(portable_dir, exist_ok=True)
        save_dirs.append(portable_dir)
        print(f"📂 [save_generated_image] Carpeta portable: {portable_dir}")
    except Exception as e:
        print(f"⚠️ [save_generated_image] Error creando carpeta portable: {str(e)}")
    
    # Forzar extensión .png
    base_name = os.path.splitext(filename)[0]
    filename_png = base_name + '.png'
    
    # Lista de rutas donde se guardará la imagen
    saved_paths = []
    
    # Guardar la imagen en cada directorio
    for save_dir in save_dirs:
        save_path = os.path.join(save_dir, filename_png)
        print(f"💾 [save_generated_image] Guardando imagen en: {save_path}")
        
        try:
            # Abrir la imagen desde bytes
            img = Image.open(BytesIO(image_bytes))
            # Guardar como PNG
            img.save(save_path, format='PNG')
            print(f"✅ [save_generated_image] Imagen guardada exitosamente")
            
            # Verificar que la imagen se guardó correctamente
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path) / 1024  # KB
                print(f"   Verificación: archivo existe, tamaño={file_size:.2f} KB, dimensiones={img.size}")
                saved_paths.append(save_path)
            else:
                print(f"⚠️ [save_generated_image] ALERTA: El archivo generado no existe en disco: {save_path}")
        except Exception as e:
            print(f"❌ [save_generated_image] ERROR guardando imagen en {save_path}: {str(e)}")
    
    # Si no se pudo guardar en ninguna ubicación, buscar archivos recientes en el output
    if not saved_paths:
        print(f"⚠️ [save_generated_image] No se pudo guardar la imagen. Buscando archivos recientes en output...")
        
        # Buscar archivos recientes en el directorio de output
        output_dir = get_comfyui_output_dir()
        if os.path.exists(output_dir):
            print(f"🔍 [save_generated_image] Buscando archivos recientes en {output_dir}...")
            recent_files = []
            try:
                # Recopilar archivos de imagen en el output recursivamente
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            file_path = os.path.join(root, file)
                            try:
                                mtime = os.path.getmtime(file_path)
                                recent_files.append((mtime, file_path))
                            except:
                                pass
                
                # Si se encontraron archivos, ordenar por tiempo y usar el más reciente
                if recent_files:
                    recent_files.sort(reverse=True)  # Ordenar por más reciente primero
                    most_recent_file = recent_files[0][1]
                    print(f"✅ [save_generated_image] Encontrado archivo más reciente en output: {most_recent_file}")
                    
                    # Copiar el archivo más reciente a nuestras carpetas específicas si es necesario
                    for save_dir in save_dirs:
                        # No copiar si ya está en la misma carpeta
                        if os.path.dirname(most_recent_file) == save_dir:
                            print(f"✅ [save_generated_image] La imagen ya está en la carpeta deseada: {save_dir}")
                            saved_paths.append(most_recent_file)
                            continue
                            
                        save_path = os.path.join(save_dir, filename_png)
                        try:
                            shutil.copy2(most_recent_file, save_path)
                            print(f"✅ [save_generated_image] Archivo copiado a: {save_path}")
                            saved_paths.append(save_path)
                        except Exception as e:
                            print(f"⚠️ [save_generated_image] Error al copiar a {save_path}: {str(e)}")
            except Exception as e:
                print(f"⚠️ [save_generated_image] Error al buscar archivos recientes: {str(e)}")
        
        # Si después de buscar seguimos sin paths, reportar error
        if not saved_paths:
            print(f"❌ [save_generated_image] ERROR: No se pudo guardar ni encontrar la imagen en ninguna ubicación")
            print(f"================== FIN GUARDADO IMAGEN ==================\n")
            return None
        
    # Devolver la primera ruta donde se guardó exitosamente
    print(f"✅ [save_generated_image] Imagen guardada en {len(saved_paths)} ubicaciones")
    print(f"   Ubicación principal: {saved_paths[0]}")
    print(f"================== FIN GUARDADO IMAGEN ==================\n")
    return saved_paths[0]
    
    print(f"💾 [save_generated_image] Guardando imagen en carpeta de ComfyUI: {path}")
    
    # Verificar si el directorio existe, crearlo si no
    os.makedirs(output_dir, exist_ok=True)
    
    # Guardar la imagen en output_dir
    try:
        img = Image.open(BytesIO(image_bytes))
        img.save(path, format='PNG')
        print(f"✅ [save_generated_image] Imagen guardada exitosamente: {path}")
        print(f"   Tamaño de imagen: {img.size[0]}x{img.size[1]}, modo: {img.mode}")
        
        # Verificar que se guardó correctamente
        if os.path.exists(path):
            file_size = os.path.getsize(path) / 1024  # KB
            print(f"   - Verificación: archivo guardado existe, tamaño={file_size:.2f} KB")
        else:
            print(f"⚠️ [save_generated_image] ALERTA: El archivo generado no existe en disco: {path}")
    except Exception as e:
        print(f"❌ [save_generated_image] ERROR guardando imagen en {path}: {str(e)}")
        raise
    
    # Devolver el path donde se guardó la imagen
    return path

def find_and_save_composite_image(outputs, output_dir, base_name):
    """
    Find the image output from the ImageCompositeMasked node and save it in the output directory.
    
    Args:
        outputs: The ComfyUI output dictionary
        output_dir: The directory where all images should be saved
        base_name: The base name for the file
        
    Returns:
        Path to the saved composite image or None if not found
    """
    print(f"\n================ BUSCANDO IMAGEN COMPUESTA ================")
    print(f"🔍 [find_and_save_composite_image] Buscando imagen de nodo ImageCompositeMasked...")
    
    composite_image_path = None
    
    # Paso 1: Identificar todos los nodos ImageCompositeMasked
    composite_nodes = []
    for node_id, node_data in outputs.items():
        class_type = node_data.get('class_type', '') or node_data.get('type', '')
        if class_type == 'ImageCompositeMasked':
            composite_nodes.append(node_id)
            print(f"🔍 [find_and_save_composite_image] Encontrado nodo ImageCompositeMasked: {node_id}")
    
    # Si no hay nodos ImageCompositeMasked, no podemos continuar
    if not composite_nodes:
        print(f"⚠️ [find_and_save_composite_image] No se encontraron nodos ImageCompositeMasked en la salida")
        print(f"================== FIN BÚSQUEDA IMAGEN COMPUESTA ==================\n")
        return None
    
    # Paso 2: Buscar nodos SaveImage que estén conectados a nodos ImageCompositeMasked
    for node_id, node_data in outputs.items():
        class_type = node_data.get('class_type', '') or node_data.get('type', '')
        if class_type == 'SaveImage':
            # Revisar si la entrada de este SaveImage viene de un nodo ImageCompositeMasked
            if 'inputs' in node_data and 'images' in node_data['inputs']:
                try:
                    # La entrada podría ser un array [node_id, output_index]
                    source_info = node_data['inputs']['images']
                    if isinstance(source_info, list) and len(source_info) > 0:
                        source_node_id = str(source_info[0])  # Convertir a string por si acaso
                        
                        # Verificar si el nodo fuente es un ImageCompositeMasked
                        if source_node_id in composite_nodes:
                            print(f"✅ [find_and_save_composite_image] Encontrado SaveImage (nodo {node_id}) conectado a ImageCompositeMasked (nodo {source_node_id})")
                            
                            # Si este nodo SaveImage tiene imágenes en la salida, procesarlas
                            if 'images' in node_data:
                                for image_info in node_data['images']:
                                    if 'filename' in image_info:
                                        filename = image_info['filename']
                                        subfolder = image_info.get('subfolder', '')
                                        
                                        print(f"🔍 [find_and_save_composite_image] Encontrada imagen: {filename} en subfolder: {subfolder}")
                                        
                                        # Buscar la imagen
                                        img_data = {
                                            'filename': filename,
                                            'subfolder': subfolder,
                                            'output_root': get_comfyui_output_dir()
                                        }
                                        
                                        img_bytes, img_path = get_image_from_output(img_data, base_name=base_name)
                                        
                                        if img_bytes:
                                            # Guardar con un nombre específico para la imagen compuesta
                                            composite_filename = "composite_masked.png"
                                            composite_image_path = os.path.join(output_dir, composite_filename)
                                            
                                            # Guardar la imagen
                                            try:
                                                img = Image.open(BytesIO(img_bytes))
                                                img.save(composite_image_path, format='PNG')
                                                print(f"✅ [find_and_save_composite_image] Imagen compuesta guardada en: {composite_image_path}")
                                                print(f"   Tamaño: {img.size[0]}x{img.size[1]}, modo: {img.mode}")
                                                
                                                # Verificar que la imagen se guardó correctamente
                                                if os.path.exists(composite_image_path):
                                                    file_size = os.path.getsize(composite_image_path) / 1024  # KB
                                                    print(f"   Verificación: imagen guardada existe, tamaño={file_size:.2f} KB")
                                                else:
                                                    print(f"⚠️ [find_and_save_composite_image] ADVERTENCIA: La imagen no existe en disco después de guardar")
                                                
                                                print(f"================== FIN BÚSQUEDA IMAGEN COMPUESTA ==================\n")
                                                return composite_image_path
                                                
                                            except Exception as e:
                                                print(f"❌ [find_and_save_composite_image] Error al guardar imagen compuesta: {str(e)}")
                except Exception as e:
                    print(f"⚠️ [find_and_save_composite_image] Error al procesar nodo SaveImage {node_id}: {str(e)}")
    
    # Paso 3: Como último recurso, buscar nodos con imágenes en la salida que puedan ser imágenes compuestas
    # (En este caso, tendríamos que adivinar cuál es la imagen compuesta)
    for node_id in composite_nodes:
        if node_id in outputs and 'images' in outputs[node_id]:
            print(f"🔍 [find_and_save_composite_image] Nodo ImageCompositeMasked {node_id} tiene imágenes en su salida")
            
            for image_info in outputs[node_id]['images']:
                if 'filename' in image_info:
                    filename = image_info['filename']
                    subfolder = image_info.get('subfolder', '')
                    
                    # Buscar la imagen
                    img_data = {
                        'filename': filename,
                        'subfolder': subfolder,
                        'output_root': get_comfyui_output_dir()
                    }
                    
                    img_bytes, img_path = get_image_from_output(img_data, base_name=base_name)
                    
                    if img_bytes:
                        # Guardar con un nombre específico para la imagen compuesta
                        composite_filename = "composite_masked.png"
                        composite_image_path = os.path.join(output_dir, composite_filename)
                        
                        # Guardar la imagen
                        try:
                            img = Image.open(BytesIO(img_bytes))
                            img.save(composite_image_path, format='PNG')
                            print(f"✅ [find_and_save_composite_image] Imagen compuesta guardada desde nodo directo: {composite_image_path}")
                            print(f"   Tamaño: {img.size[0]}x{img.size[1]}, modo: {img.mode}")
                            
                            print(f"================== FIN BÚSQUEDA IMAGEN COMPUESTA ==================\n")
                            return composite_image_path
                            
                        except Exception as e:
                            print(f"❌ [find_and_save_composite_image] Error al guardar imagen compuesta desde nodo directo: {str(e)}")
    
    # Como último recurso, buscar en la carpeta output los archivos más recientes
    print(f"🔍 [find_and_save_composite_image] No se encontró la imagen compuesta. Buscando archivos recientes en output...")
    output_dir_root = get_comfyui_output_dir()
    
    if os.path.exists(output_dir_root):
        # Buscar archivos recientes en output
        recent_files = []
        try:
            for root, dirs, files in os.walk(output_dir_root):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        file_path = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(file_path)
                            recent_files.append((mtime, file_path))
                        except:
                            pass
            
            # Ordenar por tiempo de modificación (más reciente primero)
            recent_files.sort(reverse=True)
            
            # Tomar los 3 archivos más recientes y verificar si son válidos
            for _, file_path in recent_files[:3]:
                try:
                    with Image.open(file_path) as test_img:
                        print(f"🔍 [find_and_save_composite_image] Analizando imagen reciente: {file_path}")
                        print(f"   Dimensiones: {test_img.size}, Modo: {test_img.mode}")
                        
                        # Guardar como imagen compuesta
                        composite_filename = "composite_masked.png"
                        composite_image_path = os.path.join(output_dir, composite_filename)
                        
                        # Copiar el archivo
                        shutil.copy2(file_path, composite_image_path)
                        print(f"✅ [find_and_save_composite_image] Imagen más reciente copiada como compuesta: {composite_image_path}")
                        
                        print(f"================== FIN BÚSQUEDA IMAGEN COMPUESTA ==================\n")
                        return composite_image_path
                except Exception as e:
                    print(f"⚠️ [find_and_save_composite_image] Error al procesar imagen reciente: {str(e)}")
        except Exception as e:
            print(f"⚠️ [find_and_save_composite_image] Error al buscar archivos recientes en output: {str(e)}")
    
    # Si llegamos aquí, no se encontró ninguna imagen del nodo ImageCompositeMasked
    print(f"⚠️ [find_and_save_composite_image] No se pudo encontrar ninguna imagen del nodo ImageCompositeMasked en output")
    print(f"================== FIN BÚSQUEDA IMAGEN COMPUESTA ==================\n")
    return None
