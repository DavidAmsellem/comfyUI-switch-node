#!/usr/bin/env python3
"""
Script para verificar que los valores de configuración del DynamicFrameNode están dentro de los límites permitidos
"""

def verify_frame_node_values():
    """Verifica que los valores estén dentro de los límites del nodo"""
    
    print("🔍 Verificando valores de configuración del DynamicFrameNode...")
    
    # Valores actuales configurados
    current_config = {
        'frame_width': 20,
        'shadow_enabled': False,
        'shadow_opacity': 0.1,
        'wall_color': 220,
        'shadow_size': 5,
        'shadow_color': 0,
        'shadow_angle': 270,
        'shadow_blur': 1,
        'shadow_offset_x': 0,
        'shadow_offset_y': 0
    }
    
    # Límites conocidos del nodo (según el error de ComfyUI)
    limits = {
        'shadow_blur': {'min': 1, 'max': 10},
        'shadow_size': {'min': 5, 'max': 50},
        'shadow_opacity': {'min': 0.1, 'max': 0.9},
        'frame_width': {'min': 0, 'max': 200},
        'wall_color': {'min': 180, 'max': 250},
        'shadow_angle': {'min': 0, 'max': 360},
        'shadow_offset_x': {'min': -50, 'max': 50},
        'shadow_offset_y': {'min': 0, 'max': 50}
    }
    
    print("📊 Verificando valores contra límites conocidos:")
    
    all_valid = True
    
    for param, value in current_config.items():
        if param in limits:
            limit = limits[param]
            min_val = limit['min']
            max_val = limit['max']
            
            if min_val <= value <= max_val:
                print(f"✅ {param}: {value} (válido: {min_val}-{max_val})")
            else:
                print(f"❌ {param}: {value} (INVÁLIDO: debe estar entre {min_val}-{max_val})")
                all_valid = False
        else:
            print(f"ℹ️  {param}: {value} (sin límites conocidos)")
    
    print(f"\n{'✅ Todos los valores son válidos' if all_valid else '❌ Algunos valores necesitan ajuste'}")
    
    if all_valid:
        print("\n🎉 Configuración correcta para desactivar sombra:")
        print("   - shadow_enabled: False (la sombra no se mostrará)")
        print("   - shadow_size: 5 (valor mínimo permitido)")
        print("   - shadow_opacity: 0.1 (valor mínimo permitido)")
        print("   - shadow_blur: 1 (valor mínimo permitido)")
        print("   - Aunque los valores de sombra son mínimos, NO se mostrarán porque shadow_enabled=False")
    
    return all_valid

if __name__ == "__main__":
    verify_frame_node_values()
