"""
ComfyUI Custom Node: Dynamic Frame Generator - VERSIÓN MEJORADA CON PROFUNDIDAD
Genera marcos dinámicos con efecto de profundidad realista para simular cuadros colgados en la pared
"""

import torch
import numpy as np
from PIL import Image, ImageDraw
import cv2
import random

class DynamicFrameNodeImproved:
    """
    Nodo mejorado para crear marcos dinámicos con profundidad realista en ComfyUI
    """
    
    # Configuración simplificada de marcos
    FRAME_PRESETS = {
        "brown":  {"display": "Marrón (Madera)", "color": (139, 69, 19)},
        "white":  {"display": "Blanco (Clásico)", "color": (245, 245, 240)},
        "black":  {"display": "Negro (Moderno)", "color": (30, 30, 30)},
        "gold":   {"display": "Oro (Dorado)", "color": (212, 175, 55)}
    }

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "preset": ([k for k in DynamicFrameNodeImproved.FRAME_PRESETS.keys()], {
                    "display": [v["display"] for v in DynamicFrameNodeImproved.FRAME_PRESETS.values()]
                }),
                "frame_width": ("INT", {
                    "default": 50, 
                    "min": 0, 
                    "max": 200, 
                    "step": 5
                }),
                "depth_enabled": ("BOOLEAN", {
                    "default": True,
                    "label_on": "Con Profundidad",
                    "label_off": "Sin Profundidad"
                }),
                "depth_intensity": ("FLOAT", {
                    "default": 0.8, 
                    "min": 0.1, 
                    "max": 1.0, 
                    "step": 0.05,
                    "display": "Intensidad de Profundidad"
                }),
                "perspective_style": (["realistic", "subtle", "dramatic"], {
                    "default": "realistic"
                }),
                "wall_color": ("INT", {
                    "default": 240, 
                    "min": 200, 
                    "max": 255, 
                    "step": 5,
                    "display": "Color de Pared (Gris)"
                })
            },
            "optional": {
                "upscale_workflow": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Imagen Original para Upscale",
                    "label_off": "Solo Marco Normal"
                })
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("framed_image", "clean_image_for_upscale")
    FUNCTION = "apply_dynamic_frame"
    CATEGORY = "image/postprocessing"
    
    def apply_dynamic_frame(self, image, preset, frame_width, depth_enabled, depth_intensity, perspective_style, wall_color, upscale_workflow=False):
        """
        Aplica marco dinámico con efecto de profundidad realista
        """
        if upscale_workflow:
            # Procesar imagen con marco/profundidad para la salida principal
            img_np = self.tensor_to_numpy(image)
            result_img = self.process_frame_with_depth(img_np, preset, frame_width, depth_enabled, depth_intensity, perspective_style, wall_color)
            result_tensor = self.numpy_to_tensor(result_img)
            
            # Devolver imagen original sin procesar para upscale
            return (result_tensor, image)
        else:
            # Modo normal: procesar imagen
            img_np = self.tensor_to_numpy(image)
            result_img = self.process_frame_with_depth(img_np, preset, frame_width, depth_enabled, depth_intensity, perspective_style, wall_color)
            result_tensor = self.numpy_to_tensor(result_img)
            
            return (result_tensor, result_tensor)
    
    def process_frame_with_depth(self, img_np, preset, frame_width, depth_enabled, depth_intensity, perspective_style, wall_color):
        """
        Procesa la imagen aplicando marco y efecto de profundidad
        """
        # Aplicar marco si está configurado
        if frame_width > 0:
            framed_img = self.apply_frame(img_np, preset, frame_width)
        else:
            framed_img = img_np
        
        # Aplicar efecto de profundidad si está habilitado
        if depth_enabled:
            result_img = self.create_depth_effect_with_perspective(framed_img, depth_intensity, perspective_style, wall_color)
        else:
            result_img = framed_img
        
        return result_img
    
    def apply_frame(self, img, preset, frame_width):
        """
        Aplica el marco según el preset seleccionado - CORREGIDO para RGB
        """
        preset_cfg = self.FRAME_PRESETS[preset]
        color_rgb = preset_cfg["color"]  # Mantener RGB - NO convertir a BGR
        
        if preset == "brown":
            return self.create_wood_frame(img, frame_width, color_rgb)
        elif preset == "gold":
            return self.create_gold_frame(img, frame_width, color_rgb)
        else:
            return self.create_simple_frame(img, frame_width, color_rgb)
    
    def create_depth_effect_with_perspective(self, framed_img, depth_intensity, perspective_style, wall_color):
        """
        Crea efecto de profundidad 3D realista con transformación de perspectiva
        """
        height, width = framed_img.shape[:2]
        
        # Configuraciones según el estilo de perspectiva - REDUCIR EXPANSIÓN DE FONDO
        if perspective_style == "subtle":
            depth_expansion = int(40 * depth_intensity)  # Reducido de 80 a 40
            depth_3d = int(15 * depth_intensity)
            shadow_intensity = 0.6
            perspective_angle = 0.15
        elif perspective_style == "dramatic":
            depth_expansion = int(60 * depth_intensity)  # Reducido de 120 a 60
            depth_3d = int(30 * depth_intensity)
            shadow_intensity = 1.0
            perspective_angle = 0.35
        else:  # realistic
            depth_expansion = int(50 * depth_intensity)  # Reducido de 100 a 50
            depth_3d = int(20 * depth_intensity)
            shadow_intensity = 0.8
            perspective_angle = 0.25
        
        # Crear lienzo con expansión mínima - SOLO LO NECESARIO PARA EL EFECTO 3D
        canvas_height = height + depth_expansion
        canvas_width = width + depth_expansion
        wall_img = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * wall_color
        
        # Posicionar el cuadro más centrado - REDUCIR MÁRGENES
        frame_x = depth_expansion // 6  # Margen izquierdo mínimo
        frame_y = depth_expansion // 8  # Margen superior mínimo
        
        # 1. Crear transformación de perspectiva 3D para el cuadro principal
        transformed_frame = self.apply_3d_perspective_transform(framed_img, perspective_angle, depth_3d)
        
        # 2. Posicionar el cuadro transformado - MÉTODO SEGURO SIN ERRORES DE DIMENSIÓN
        tf_height, tf_width = transformed_frame.shape[:2]
        
        # Calcular región válida de copiado
        valid_height = min(tf_height, canvas_height - frame_y)
        valid_width = min(tf_width, canvas_width - frame_x)
        
        if valid_height > 0 and valid_width > 0:
            # Obtener la región de la imagen transformada que cabe en el canvas
            transformed_region = transformed_frame[:valid_height, :valid_width]
            
            # CORRECCIÓN: Crear máscara que preserve los negros originales
            # Solo excluir píxeles completamente negros que son resultado de interpolación de OpenCV
            # Pero permitir negros que forman parte de la imagen original
            
            # Obtener el color de borde para identificar píxeles de interpolación
            edge_color = self.get_average_edge_color(framed_img)
            
            # Crear máscara que excluya solo píxeles de interpolación (negros puros)
            # pero preserve negros que son parte de la imagen original
            mask = np.ones((valid_height, valid_width), dtype=bool)
            
            # Solo excluir píxeles que son exactamente [0,0,0] Y están en las esquinas/bordes
            # (resultado de la interpolación de perspectiva)
            for y in range(valid_height):
                for x in range(valid_width):
                    pixel = transformed_region[y, x]
                    # Excluir solo píxeles completamente negros en áreas de borde que claramente son interpolación
                    if np.array_equal(pixel, [0, 0, 0]):
                        # Si está en el borde y es negro puro, probablemente es interpolación
                        if y < 5 or x < 5 or y >= valid_height - 5 or x >= valid_width - 5:
                            mask[y, x] = False
            
            # Aplicar la transformación pixel por pixel de forma segura
            for y in range(valid_height):
                for x in range(valid_width):
                    if mask[y, x]:
                        wall_img[frame_y + y, frame_x + x] = transformed_region[y, x]
        
        # 3. Crear caras laterales 3D realistas
        self.create_3d_side_faces(wall_img, framed_img, frame_x, frame_y, width, height, 
                                depth_3d, perspective_angle, wall_color)
        
        # 4. Añadir sombras 3D realistas
        self.add_3d_realistic_shadows(wall_img, frame_x, frame_y, width, height, 
                                    depth_3d, shadow_intensity, perspective_style, wall_color)
        
        # 5. RECORTAR EL EXCESO DE FONDO - Mantener solo lo necesario
        final_img = self.crop_to_minimal_background(wall_img, frame_x, frame_y, width, height, depth_3d)
        
        return final_img
    
    def crop_to_minimal_background(self, wall_img, frame_x, frame_y, original_width, original_height, depth_3d):
        """
        Recorta la imagen para mantener solo el fondo mínimo necesario
        """
        canvas_height, canvas_width = wall_img.shape[:2]
        
        # Calcular márgenes mínimos necesarios
        # Izquierda: solo un pequeño margen (sin efecto 3D)
        left_margin = max(5, frame_x - 5)
        
        # Arriba: solo un pequeño margen (sin efecto 3D)
        top_margin = max(5, frame_y - 5)
        
        # Derecha: espacio para caras laterales 3D + sombras
        right_extension = int(depth_3d * 1.5)  # Espacio para lado 3D + sombras
        right_boundary = frame_x + original_width + right_extension
        
        # Abajo: espacio para cara inferior 3D + sombras
        bottom_extension = int(depth_3d * 1.2)  # Espacio para lado inferior + sombras
        bottom_boundary = frame_y + original_height + bottom_extension
        
        # Asegurar que no excedemos los límites del canvas
        left_crop = max(0, left_margin)
        top_crop = max(0, top_margin)
        right_crop = min(canvas_width, right_boundary)
        bottom_crop = min(canvas_height, bottom_boundary)
        
        # Recortar la imagen
        cropped_img = wall_img[top_crop:bottom_crop, left_crop:right_crop]
        
        return cropped_img
    
    def apply_3d_perspective_transform(self, img, perspective_angle, depth_3d):
        """
        Aplica transformación de perspectiva 3D realista al cuadro
        """
        height, width = img.shape[:2]
        
        # Validar dimensiones de entrada
        if height <= 0 or width <= 0:
            return img
        
        # Crear puntos de origen (rectángulo original)
        src_points = np.float32([
            [0, 0],                    # Esquina superior izquierda
            [width, 0],                # Esquina superior derecha
            [width, height],           # Esquina inferior derecha
            [0, height]                # Esquina inferior izquierda
        ])
        
        # Calcular desplazamiento 3D basado en el ángulo de perspectiva
        x_offset = max(1, int(depth_3d * perspective_angle))
        y_offset = max(1, int(depth_3d * perspective_angle * 0.6))
        
        # Crear puntos de destino (rectángulo con perspectiva 3D)
        dst_points = np.float32([
            [x_offset, y_offset],                      # Superior izquierda (desplazada)
            [width + x_offset, 0],                     # Superior derecha
            [width + x_offset * 2, height - y_offset], # Inferior derecha (más desplazada)
            [x_offset * 2, height]                     # Inferior izquierda (desplazada)
        ])
        
        # Calcular matriz de transformación de perspectiva
        perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Calcular dimensiones de la imagen transformada con margen de seguridad
        transformed_width = max(width + x_offset * 2 + 20, width)
        transformed_height = max(height + y_offset + 20, height)
        
        # Obtener color promedio del borde para usar como fondo en lugar de negro
        edge_color = self.get_average_edge_color(img)
        
        # Aplicar transformación de perspectiva con color de fondo apropiado
        try:
            transformed_img = cv2.warpPerspective(
                img, 
                perspective_matrix, 
                (transformed_width, transformed_height),
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=edge_color  # Usar color del borde en lugar de negro
            )
            
            # Verificar que la imagen transformada tiene las dimensiones esperadas
            actual_height, actual_width = transformed_img.shape[:2]
            if actual_height != transformed_height or actual_width != transformed_width:
                print(f"Warning: Dimensiones inesperadas - esperado: {transformed_height}x{transformed_width}, actual: {actual_height}x{actual_width}")
            
            return transformed_img
            
        except Exception as e:
            print(f"Error en transformación de perspectiva: {e}")
            return img  # Devolver imagen original en caso de error
    
    def get_average_edge_color(self, img):
        """
        Obtiene el color promedio de los bordes de la imagen para evitar líneas blancas
        """
        height, width = img.shape[:2]
        
        # Validar dimensiones
        if height <= 0 or width <= 0:
            return (128, 128, 128)  # Color gris por defecto
        
        # Tomar muestras de los bordes
        top_edge = img[0, :]  # Primera fila
        bottom_edge = img[height-1, :]  # Última fila
        left_edge = img[:, 0]  # Primera columna
        right_edge = img[:, width-1]  # Última columna
        
        # Combinar todas las muestras de borde
        edge_pixels = np.concatenate([
            top_edge.reshape(-1, 3),
            bottom_edge.reshape(-1, 3),
            left_edge.reshape(-1, 3),
            right_edge.reshape(-1, 3)
        ])
        
        # Calcular color promedio
        avg_color = np.mean(edge_pixels, axis=0)
        
        # Convertir a tuple de enteros para cv2
        return tuple(int(c) for c in avg_color)
    
    def create_3d_side_faces(self, wall_img, original_img, frame_x, frame_y, original_width, original_height, depth_3d, perspective_angle, wall_color):
        """
        Crea las caras laterales 3D del marco con iluminación realista
        """
        # Obtener color base del marco
        frame_color = self.get_frame_edge_color(original_img, original_width, original_height)
        
        # Crear cara lateral derecha con perspectiva 3D
        self.create_3d_right_face(wall_img, frame_color, frame_x, frame_y, 
                                 original_width, original_height, depth_3d, perspective_angle)
        
        # Crear cara inferior con perspectiva 3D
        self.create_3d_bottom_face(wall_img, frame_color, frame_x, frame_y, 
                                  original_width, original_height, depth_3d, perspective_angle)
        
        # Crear cara superior (visible desde abajo)
        self.create_3d_top_face(wall_img, frame_color, frame_x, frame_y, 
                               original_width, original_height, depth_3d, perspective_angle)
    
    def create_3d_right_face(self, wall_img, frame_color, frame_x, frame_y, width, height, depth_3d, perspective_angle):
        """
        Crea la cara lateral derecha con perspectiva 3D realista
        """
        x_offset = int(depth_3d * perspective_angle)
        y_offset = int(depth_3d * perspective_angle * 0.6)
        
        # Definir los puntos de la cara lateral derecha
        for y in range(height):
            progress = y / height
            
            # Calcular la posición en la imagen transformada
            current_y = frame_y + y + int(y_offset * (1 - progress))
            start_x = frame_x + width + int(x_offset * (1 + progress))
            end_x = start_x + int(depth_3d * (0.8 + 0.2 * progress))
            
            # Calcular iluminación (más oscura hacia la derecha y abajo)
            light_factor = 0.6 - (progress * 0.15)
            side_color = (frame_color * light_factor).astype(np.uint8)
            
            # Dibujar la cara lateral con gradiente
            for x in range(start_x, min(end_x, wall_img.shape[1])):
                if current_y < wall_img.shape[0] and x < wall_img.shape[1]:
                    # Gradiente de profundidad
                    depth_progress = (x - start_x) / max(1, end_x - start_x)
                    depth_fade = 1.0 - (depth_progress * 0.3)
                    final_color = (side_color * depth_fade).astype(np.uint8)
                    wall_img[current_y, x] = final_color
    
    def create_3d_bottom_face(self, wall_img, frame_color, frame_x, frame_y, width, height, depth_3d, perspective_angle):
        """
        Crea la cara inferior con perspectiva 3D realista
        """
        x_offset = int(depth_3d * perspective_angle)
        y_offset = int(depth_3d * perspective_angle * 0.6)
        
        # Definir los puntos de la cara inferior
        for x in range(width):
            progress = x / width
            
            # Calcular la posición en la imagen transformada
            current_x = frame_x + x + int(x_offset * (1 + progress))
            start_y = frame_y + height - int(y_offset * progress)
            end_y = start_y + int(depth_3d * (0.7 + 0.3 * progress))
            
            # Calcular iluminación (más oscura hacia abajo y hacia la derecha)
            light_factor = 0.5 - (progress * 0.1)
            bottom_color = (frame_color * light_factor).astype(np.uint8)
            
            # Dibujar la cara inferior con gradiente
            for y in range(start_y, min(end_y, wall_img.shape[0])):
                if y < wall_img.shape[0] and current_x < wall_img.shape[1]:
                    # Gradiente de profundidad
                    depth_progress = (y - start_y) / max(1, end_y - start_y)
                    depth_fade = 1.0 - (depth_progress * 0.4)
                    final_color = (bottom_color * depth_fade).astype(np.uint8)
                    wall_img[y, current_x] = final_color
    
    def create_3d_top_face(self, wall_img, frame_color, frame_x, frame_y, width, height, depth_3d, perspective_angle):
        """
        Crea la cara superior (visible desde perspectiva inferior)
        """
        x_offset = int(depth_3d * perspective_angle)
        y_offset = int(depth_3d * perspective_angle * 0.6)
        
        # La cara superior es menos visible, pero añade realismo
        for x in range(width):
            progress = x / width
            
            current_x = frame_x + x + int(x_offset * progress)
            start_y = frame_y + int(y_offset * (1 - progress))
            end_y = start_y + int(depth_3d * 0.3)  # Cara superior más estrecha
            
            # Iluminación más clara (recibe más luz desde arriba)
            light_factor = 0.9 - (progress * 0.1)
            top_color = (frame_color * light_factor).astype(np.uint8)
            
            # Dibujar la cara superior
            for y in range(start_y, min(end_y, wall_img.shape[0])):
                if y >= 0 and y < wall_img.shape[0] and current_x < wall_img.shape[1]:
                    depth_progress = (y - start_y) / max(1, end_y - start_y)
                    depth_fade = 1.0 - (depth_progress * 0.2)
                    final_color = (top_color * depth_fade).astype(np.uint8)
                    wall_img[y, current_x] = final_color
    
    def add_3d_realistic_shadows(self, wall_img, frame_x, frame_y, width, height, depth_3d, shadow_intensity, perspective_style, wall_color):
        """
        Añade sombras sutiles solo en la parte derecha y abajo del cuadro
        """
        # Solo sombra derecha y abajo - más sutil y realista
        self.add_simple_right_bottom_shadow(wall_img, frame_x, frame_y, width, height, depth_3d, shadow_intensity, wall_color)
    
    def add_simple_right_bottom_shadow(self, wall_img, frame_x, frame_y, width, height, depth_3d, shadow_intensity, wall_color):
        """
        Añade sombra sutil solo en la parte derecha y abajo del cuadro
        """
        # Configurar intensidad de sombra más sutil
        shadow_strength = 0.15 * shadow_intensity  # Mucho más sutil
        base_shadow_color = int(wall_color * (1 - shadow_strength))
        
        # Sombra lateral derecha (muy sutil)
        shadow_width_right = int(depth_3d * 0.8)  # Ancho de la sombra derecha
        
        for i in range(shadow_width_right):
            # Fade exponencial para sombra muy suave
            fade = np.exp(-3.0 * i / shadow_width_right) * shadow_strength
            
            shadow_x = frame_x + width + i
            if shadow_x < wall_img.shape[1]:
                # Sombra solo en la altura del cuadro, sin extender arriba
                for y in range(frame_y, min(frame_y + height, wall_img.shape[0])):
                    current_pixel = wall_img[y, shadow_x]
                    shadow_color = int(base_shadow_color + (wall_color - base_shadow_color) * (1 - fade))
                    wall_img[y, shadow_x] = np.clip(current_pixel * (1 - fade) + shadow_color * fade, 0, 255).astype(np.uint8)
        
        # Sombra inferior (muy sutil)
        shadow_height_bottom = int(depth_3d * 0.6)  # Altura de la sombra inferior
        
        for i in range(shadow_height_bottom):
            # Fade exponencial para sombra muy suave
            fade = np.exp(-3.0 * i / shadow_height_bottom) * shadow_strength
            
            shadow_y = frame_y + height + i
            if shadow_y < wall_img.shape[0]:
                # Sombra en el ancho del cuadro + un poco hacia la derecha
                shadow_start_x = frame_x
                shadow_end_x = frame_x + width + int(i * 0.3)  # Se extiende ligeramente hacia la derecha
                
                for x in range(shadow_start_x, min(shadow_end_x, wall_img.shape[1])):
                    # Gradiente horizontal: más intenso cerca del cuadro, más suave hacia los extremos
                    distance_from_center = abs(x - (frame_x + width/2)) / (width/2)
                    fade_horizontal = fade * (1 - distance_from_center * 0.4)
                    
                    if fade_horizontal > 0:
                        current_pixel = wall_img[shadow_y, x]
                        shadow_color = int(base_shadow_color + (wall_color - base_shadow_color) * (1 - fade_horizontal))
                        wall_img[shadow_y, x] = np.clip(current_pixel * (1 - fade_horizontal) + shadow_color * fade_horizontal, 0, 255).astype(np.uint8)
    
    def get_frame_edge_color(self, framed_img, frame_width, frame_height):
        """
        Obtiene el color promedio del borde del marco para las caras laterales
        """
        # Tomar una muestra del borde derecho del marco
        if frame_width > 10:
            edge_sample = framed_img[:, -10:]  # Últimas 10 columnas
        else:
            edge_sample = framed_img[:, -5:]   # Últimas 5 columnas
        
        # Calcular color promedio
        avg_color = np.mean(edge_sample, axis=(0, 1))
        
        # Oscurecer ligeramente para simular que es la cara lateral
        return avg_color * 0.8
    
    def create_simple_frame(self, img, frame_width, frame_color):
        """Crea marco simple, color sólido"""
        height, width = img.shape[:2]
        new_width = width + (frame_width * 2)
        new_height = height + (frame_width * 2)
        framed = np.full((new_height, new_width, 3), frame_color, dtype=np.uint8)
        framed[frame_width:frame_width+height, frame_width:frame_width+width] = img
        return framed

    def create_wood_frame(self, img, frame_width, frame_color):
        """Crea marco con apariencia de madera"""
        height, width = img.shape[:2]
        new_width = width + (frame_width * 2)
        new_height = height + (frame_width * 2)
        framed = np.full((new_height, new_width, 3), frame_color, dtype=np.uint8)
        
        # Añadir veteado de madera
        for i in range(0, new_height, 3):
            noise = np.random.randint(-15, 15)
            vein_color_array = np.clip(np.array(frame_color) + noise, 0, 255)
            vein_color = tuple(int(c) for c in vein_color_array)
            cv2.line(framed, (0, i), (new_width, i), vein_color, 1)
        
        framed[frame_width:frame_width+height, frame_width:frame_width+width] = img
        return framed

    def create_gold_frame(self, img, frame_width, frame_color):
        """Crea marco con reflejos dorados"""
        height, width = img.shape[:2]
        new_width = width + (frame_width * 2)
        new_height = height + (frame_width * 2)
        framed = np.full((new_height, new_width, 3), frame_color, dtype=np.uint8)
        
        # Añadir reflejos dorados
        for i in range(0, frame_width, 6):
            intensity = int(30 * np.sin(i * 0.25))
            highlight_array = np.clip(np.array(frame_color) + intensity, 0, 255)
            highlight = tuple(int(c) for c in highlight_array)
            cv2.rectangle(framed, (i, i), (new_width-i, new_height-i), highlight, 2)
        
        framed[frame_width:frame_width+height, frame_width:frame_width+width] = img
        return framed
    
    def tensor_to_numpy(self, tensor):
        """Convierte tensor de ComfyUI a numpy array - CORREGIDO para mantener colores originales"""
        img = tensor[0].cpu().numpy()
        img = (img * 255).astype(np.uint8)
        # NO convertir a BGR - mantener RGB ya que OpenCV puede trabajar con ambos
        return img
    
    def numpy_to_tensor(self, img):
        """Convierte numpy array a tensor de ComfyUI - CORREGIDO para mantener colores originales"""
        # Asegurar que la imagen esté en formato RGB (no convertir de BGR)
        img = img.astype(np.float32) / 255.0
        img = torch.from_numpy(img).unsqueeze(0)
        return img

# Registrar el nodo
NODE_CLASS_MAPPINGS = {
    "DynamicFrameNode": DynamicFrameNodeImproved  # Mantener el nombre original para compatibilidad
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DynamicFrameNode": "Dynamic Frame Generator (Improved Depth)"
}
