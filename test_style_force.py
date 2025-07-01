#!/usr/bin/env python3
"""
Script de prueba para verificar que el estilo test_main_force funciona correctamente
"""

import json
import sys
import os

# Añadir el directorio actual al path para importar style_presets
sys.path.insert(0, os.path.dirname(__file__))

import style_presets

def test_main_force_style():
    """
    Prueba el estilo test_main_force para verificar que fuerza la aplicación al Main Prompt
    """
    
    # Cargar el workflow de ejemplo
    workflow_path = "workflows/bathroom/H80x60/cuadro-bathroom-open-H60x802.json"
    
    if not os.path.exists(workflow_path):
        print(f"❌ No se encontró el archivo de workflow: {workflow_path}")
        return False
    
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    print("=== ESTADO INICIAL ===")
    print(f"Main Prompt (nodo 3): '{workflow['3']['inputs']['prompt']}'")
    print(f"Style (nodo 6): '{workflow['6']['inputs']['prompt']}'")
    print()
    
    # Aplicar el estilo test_main_force
    print("=== APLICANDO ESTILO test_main_force ===")
    modified_workflow = style_presets.apply_style_to_workflow(
        workflow, 
        "test_main_force"
    )
    
    print()
    print("=== ESTADO DESPUÉS DE APLICAR ESTILO ===")
    print(f"Main Prompt (nodo 3): '{modified_workflow['3']['inputs']['prompt']}'")
    print(f"Style (nodo 6): '{modified_workflow['6']['inputs']['prompt']}'")
    print()
    
    # Verificar que el estilo se aplicó al Main Prompt
    main_prompt_content = modified_workflow['3']['inputs']['prompt']
    style_prompt_content = modified_workflow['6']['inputs']['prompt']
    
    test_keywords = ["TESTING MAIN PROMPT OVERRIDE", "forced main node application"]
    
    success = True
    
    # Verificar que el Main Prompt contiene las palabras clave del test
    for keyword in test_keywords:
        if keyword not in main_prompt_content:
            print(f"❌ FALLO: Palabra clave '{keyword}' no encontrada en Main Prompt")
            success = False
        else:
            print(f"✅ ÉXITO: Palabra clave '{keyword}' encontrada en Main Prompt")
    
    # Verificar que el Style NO contiene las palabras clave (porque se forzó al Main)
    for keyword in test_keywords:
        if keyword in style_prompt_content:
            print(f"❌ FALLO: Palabra clave '{keyword}' encontrada incorrectamente en Style")
            success = False
        else:
            print(f"✅ ÉXITO: Palabra clave '{keyword}' NO está en Style (correcto)")
    
    print()
    if success:
        print("🎉 *** PRUEBA EXITOSA *** El estilo test_main_force funciona correctamente")
        print("🔧 El estilo se aplicó al Main Prompt en lugar del Style como se esperaba")
    else:
        print("💥 *** PRUEBA FALLIDA *** El estilo test_main_force no funciona correctamente")
    
    return success

if __name__ == "__main__":
    test_main_force_style()
