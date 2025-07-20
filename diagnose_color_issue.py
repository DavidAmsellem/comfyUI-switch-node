#!/usr/bin/env python3
"""
Script para diagnosticar el problema de colores en el nodo DynamicFrameNode
"""

import numpy as np

def diagnose_color_issue():
    """Diagnostica el problema de colores en OpenCV"""
    
    print("🔍 Diagnosticando problema de colores en DynamicFrameNode...")
    
    # Simular el problema según el error
    frame_color = (139, 69, 19)  # Color marrón RGB
    
    print(f"📊 Análisis del color marrón:")
    print(f"   RGB original: {frame_color}")
    print(f"   Tipo: {type(frame_color)}")
    print(f"   Valores individuales: R={frame_color[0]}, G={frame_color[1]}, B={frame_color[2]}")
    
    # Verificar conversión a BGR (como OpenCV requiere)
    color_bgr = (frame_color[2], frame_color[1], frame_color[0])  # RGB -> BGR
    print(f"   BGR para OpenCV: {color_bgr}")
    
    # Simular la lógica problemática del nodo
    print(f"\n🔧 Simulando lógica del nodo create_wood_frame:")
    
    # Esto es lo que probablemente está causando el error
    noise = np.random.randint(-18, 18)
    print(f"   Ruido generado: {noise}")
    
    # Aquí está el problema: np.clip puede devolver arrays numpy en lugar de tuplas
    vein_color_array = np.clip(np.array(color_bgr) + noise, 0, 255)
    print(f"   vein_color como array numpy: {vein_color_array}")
    print(f"   Tipo: {type(vein_color_array)}")
    print(f"   Dtype: {vein_color_array.dtype}")
    
    # OpenCV espera una tupla de enteros, no un array numpy
    # Solución: convertir a tupla de enteros
    vein_color_fixed = tuple(int(x) for x in vein_color_array)
    print(f"   vein_color corregido: {vein_color_fixed}")
    print(f"   Tipo corregido: {type(vein_color_fixed)}")
    
    print(f"\n🚨 PROBLEMA IDENTIFICADO:")
    print(f"   - np.clip() devuelve un array numpy")
    print(f"   - OpenCV cv2.line() espera una tupla de enteros")
    print(f"   - Conversión necesaria: tuple(int(x) for x in array)")
    
    # Verificar otros colores
    print(f"\n🎨 Verificando otros colores de marco:")
    
    colors = {
        'black': (30, 30, 30),
        'white': (245, 245, 240),
        'brown': (139, 69, 19),
        'gold': (212, 175, 55)
    }
    
    for color_name, rgb in colors.items():
        bgr = (rgb[2], rgb[1], rgb[0])
        test_noise = np.random.randint(-18, 18)
        vein_array = np.clip(np.array(bgr) + test_noise, 0, 255)
        vein_fixed = tuple(int(x) for x in vein_array)
        
        print(f"   {color_name}: RGB{rgb} -> BGR{bgr} -> fijo{vein_fixed}")

def suggest_fix():
    """Sugiere la solución para el nodo"""
    
    print(f"\n💡 SOLUCIÓN SUGERIDA:")
    print(f"   El nodo DynamicFrameNode necesita ser corregido:")
    print(f"   ")
    print(f"   CAMBIAR:")
    print(f"   vein_color = tuple(np.clip(np.array(frame_color) + noise, 0, 255))")
    print(f"   ")
    print(f"   POR:")
    print(f"   vein_color = tuple(int(x) for x in np.clip(np.array(frame_color) + noise, 0, 255))")
    print(f"   ")
    print(f"   Esto asegura que OpenCV reciba tuplas de enteros en lugar de arrays numpy.")

if __name__ == "__main__":
    diagnose_color_issue()
    suggest_fix()
