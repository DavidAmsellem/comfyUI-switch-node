#!/usr/bin/env python3
"""
Configuración de estilos predefinidos para workflows
"""

# Estilos predefinidos que se pueden aplicar al nodo de Style (6)
STYLE_PRESETS = {
    "default": {
        "name": "🎨 Por defecto",
        "description": "Sin estilo adicional, usa el prompt original",
        "style_prompt": "",
        "display_order": 1
    },
    "colorful": {
        "name": "🌈 Colorido",
        "description": "Colores vibrantes y saturados",
        "style_prompt": "vibrant colors, colorful, bright vivid palette, saturated colors, bold rainbow colors, vivid tones, rich brilliant colors, dynamic color scheme, intense hues, chromatic brilliance",
        "display_order": 2
    },
    "warm": {
        "name": "🔥 Cálido",
        "description": "Tonos cálidos y acogedores",
        "style_prompt": "warm golden lighting, cozy atmosphere, golden hour ambiance, amber warm tones, warm inviting colors, soft warm light, honey-colored illumination, sunset glow, comfortable warmth",
        "display_order": 3
    },
    "cool": {
        "name": "❄️ Fresco",
        "description": "Tonos fríos y modernos",
        "style_prompt": "cool blue lighting, modern crisp atmosphere, ice blue tones, cool refreshing colors, crystalline light, contemporary cool feel, arctic freshness, steel blue ambiance",
        "display_order": 4
    },
    "luxury": {
        "name": "✨ Lujoso",
        "description": "Estilo elegante y premium",
        "style_prompt": "luxury design, elegant premium materials, sophisticated high-end finish, refined luxurious details, upscale exclusive design, opulent rich textures, sumptuous elegant style, lavish premium quality",
        "display_order": 5
    },
    "minimalist": {
        "name": "⚪ Minimalista",
        "description": "Estilo limpio y simple",
        "style_prompt": "minimalist design, clean simple lines, uncluttered space, pure white elements, geometric simplicity, zen aesthetic, serene minimalism, stark clean beauty, essential forms only",
        "display_order": 6
    },
    "industrial": {
        "name": "🏭 Industrial",
        "description": "Estilo industrial y urbano",
        "style_prompt": "industrial style, exposed materials, concrete textures, metal accents, urban aesthetic, raw materials",
        "display_order": 7
    },
    "natural": {
        "name": "🌿 Natural",
        "description": "Estilo orgánico y natural",
        "style_prompt": "natural materials, organic textures, earthy tones, wood accents, stone elements, biophilic design",
        "display_order": 8
    },
    "vintage": {
        "name": "🕰️ Vintage",
        "description": "Estilo retro y clásico",
        "style_prompt": "vintage style, retro aesthetic, classic design, aged materials, nostalgic atmosphere, timeless elegance",
        "display_order": 9
    },
    "futuristic": {
        "name": "🚀 Futurista",
        "description": "Estilo moderno y tecnológico",
        "style_prompt": "futuristic design, high-tech, sleek surfaces, LED lighting, modern technology, sci-fi aesthetic",
        "display_order": 10
    },
    "artistic": {
        "name": "🎭 Artístico",
        "description": "Estilo creativo y expresivo",
        "style_prompt": "artistic flair, creative design, unique textures, expressive colors, artistic composition, gallery-worthy",
        "display_order": 11
    },
    "scandinavian": {
        "name": "🇸🇪 Escandinavo",
        "description": "Estilo nórdico funcional",
        "style_prompt": "scandinavian design, nordic style, functional beauty, light wood, hygge atmosphere, cozy minimalism",
        "display_order": 12
    },
    "dramatic": {
        "name": "🎭 Dramático",
        "description": "Iluminación dramática y contrastes fuertes",
        "style_prompt": "dramatic lighting, high contrast, bold shadows, theatrical illumination, striking dramatic effect, intense chiaroscuro, powerful visual impact, moody atmospheric lighting",
        "display_order": 13
    },
    "cinematic": {
        "name": "🎬 Cinematográfico",
        "description": "Estilo de película con iluminación profesional",
        "style_prompt": "cinematic lighting, film-like quality, professional cinematography, movie scene lighting, cinematic composition, hollywood style, film grain texture, cinematic color grading",
        "display_order": 14
    },
    "neon": {
        "name": "⚡ Neón",
        "description": "Iluminación neón vibrante y futurista",
        "style_prompt": "neon lighting, glowing neon colors, cyberpunk vibes, electric blue and pink, fluorescent illumination, retro-futuristic neon, vibrant glowing accents, neon sign aesthetic",
        "display_order": 15
    },
    "botanical": {
        "name": "🌿 Botánico",
        "description": "Abundante vegetación y elementos naturales",
        "style_prompt": "lush botanical elements, abundant plants, green foliage everywhere, tropical paradise, jungle-like vegetation, living wall plants, botanical garden style, nature-filled space",
        "display_order": 16
    },
    "extreme_colorful": {
        "name": "🌈💥 Súper Colorido",
        "description": "Colores extremadamente vibrantes e intensos",
        "style_prompt": "(((vibrant explosive colors))), (((rainbow spectrum everywhere))), (((neon bright saturated hues))), psychedelic color palette, intense chromatic saturation, electric vivid tones, fluorescent color explosion, kaleidoscope effect",
        "display_order": 17
    },
    "dark_moody": {
        "name": "🖤 Oscuro y Atmosférico",
        "description": "Ambiente oscuro y misterioso con iluminación dramática",
        "style_prompt": "(((dark moody atmosphere))), (((dramatic shadows))), (((mysterious lighting))), noir aesthetic, deep contrasts, gothic ambiance, chiaroscuro lighting, brooding darkness",
        "display_order": 18
    },
    "hyperrealistic": {
        "name": "📸 Hiperrealista",
        "description": "Detalles extremadamente realistas y definidos",
        "style_prompt": "(((hyperrealistic details))), (((photorealistic quality))), (((ultra-detailed textures))), 8K resolution, professional photography, sharp focus, realistic materials, lifelike rendering",
        "display_order": 19
    },
    "test_main_force": {
        "name": "🧪 TEST: Forzar Main Prompt",
        "description": "Estilo de prueba que fuerza aplicación al nodo Main Prompt en lugar del Style",
        "style_prompt": "(((TESTING MAIN PROMPT OVERRIDE))), (((forced main node application))), experimental style test, main prompt injection test, override style node behavior",
        "display_order": 20,
        "force_main_prompt": True,
        "force_target_node": "main_prompt"
    }
}

# Configuración de nodos específicos para diferentes tipos de workflow
WORKFLOW_NODE_CONFIG = {
    # Configuración para workflows que usan Searge
    "searge": {
        "style_node_id": "6",  # Nodo de Style en workflows Searge
        "main_prompt_node_id": "3",
        "secondary_prompt_node_id": "5",
        "negative_prompt_node_id": "7",
        "negative_secondary_node_id": "8",
        "prompt_adapter_node_id": "622",  # Nodo que conecta todos los prompts
        "conditioning_params_node_id": "614"  # Nodo SeargeConditioningParameters
    },
    # Configuración para workflows básicos de ComfyUI
    "basic": {
        "style_node_id": None,  # No hay nodo de style separado
        "main_prompt_node_id": "6",  # CLIPTextEncode típico
        "secondary_prompt_node_id": None,
        "negative_prompt_node_id": "7",
        "negative_secondary_node_id": None,
        "conditioning_params_node_id": None
    }
}

def get_available_styles():
    """
    Retorna lista de estilos disponibles ordenados por display_order
    """
    styles = []
    for style_id, style_data in STYLE_PRESETS.items():
        styles.append({
            "id": style_id,
            "name": style_data["name"],
            "description": style_data["description"],
            "display_order": style_data["display_order"]
        })
    
    # Ordenar por display_order
    styles.sort(key=lambda x: x["display_order"])
    return styles

def get_style_prompt(style_id):
    """
    Obtiene el prompt de estilo para un ID dado
    """
    if style_id in STYLE_PRESETS:
        return STYLE_PRESETS[style_id]["style_prompt"]
    return ""

def detect_workflow_type(workflow):
    """
    Detecta el tipo de workflow basado en los nodos presentes
    """
    if "622" in workflow and workflow["622"].get("class_type") == "SeargePromptAdapterV2":
        return "searge"
    return "basic"

def get_node_config(workflow_type):
    """
    Obtiene la configuración de nodos para un tipo de workflow
    """
    return WORKFLOW_NODE_CONFIG.get(workflow_type, WORKFLOW_NODE_CONFIG["basic"])

def apply_style_to_workflow(workflow, style_id, custom_node_id=None):
    """
    Aplica un estilo al workflow modificando el nodo correspondiente y ajustando parámetros
    
    Args:
        workflow: El workflow JSON
        style_id: ID del estilo a aplicar
        custom_node_id: ID del nodo específico donde aplicar el estilo (opcional)
    """
    if style_id not in STYLE_PRESETS or style_id == "default":
        return workflow
    
    style_prompt = get_style_prompt(style_id)
    if not style_prompt:
        return workflow
    
    # Detectar tipo de workflow
    workflow_type = detect_workflow_type(workflow)
    
    # 1. Aplicar el prompt del estilo al nodo correspondiente
    style_data = STYLE_PRESETS.get(style_id, {})
    force_main_prompt = style_data.get("force_main_prompt", False)
    
    if custom_node_id and custom_node_id in workflow:
        workflow = apply_style_to_specific_node(workflow, style_prompt, custom_node_id)
        print(f"🎯 Estilo aplicado a nodo específico seleccionado: {custom_node_id}")
    elif force_main_prompt:
        # FORZAR aplicación al nodo Main Prompt (nodo 3 en workflows Searge)
        # Esto es específico para el estilo de prueba test_main_force
        force_node_id = "3"  # Main Prompt en workflows Searge
        if force_node_id in workflow:
            workflow = apply_style_to_specific_node(workflow, style_prompt, force_node_id)
            print(f"🔧 *** FORZANDO *** aplicación al Main Prompt {force_node_id} (estilo: {style_id})")
            print(f"🔧 Prompt original: {workflow[force_node_id]['inputs'].get('prompt', '')[:50]}...")
            print(f"🔧 Nuevo prompt con estilo: {workflow[force_node_id]['inputs'].get('prompt', '')[-100:]}")
        else:
            print(f"❌ ERROR: No se encontró nodo Main Prompt {force_node_id} para forzar aplicación")
    else:
        # Usar la detección automática
        node_config = get_node_config(workflow_type)
        
        # Aplicar estilo según el tipo de workflow
        if workflow_type == "searge" and node_config["style_node_id"]:
            style_node_id = node_config["style_node_id"]
            if style_node_id in workflow:
                workflow = apply_style_to_specific_node(workflow, style_prompt, style_node_id)
                print(f"✅ Estilo aplicado al nodo Style automático: {style_node_id}")
        elif workflow_type == "basic":
            # Para workflows básicos, añadir al prompt principal
            main_node_id = node_config["main_prompt_node_id"]
            if main_node_id in workflow:
                workflow = apply_style_to_specific_node(workflow, style_prompt, main_node_id)
                print(f"✅ Estilo aplicado al Main Prompt básico: {main_node_id}")
    
    # 2. Ajustar parámetros de conditioning para mayor impacto visual
    if style_id != "default":
        workflow = adjust_conditioning_parameters_for_style(workflow, style_id, workflow_type)
    
    return workflow

def apply_style_to_specific_node(workflow, style_prompt, node_id):
    """
    Aplica un estilo a un nodo específico del workflow
    """
    if node_id not in workflow:
        return workflow
    
    node = workflow[node_id]
    
    # Asegurar que hay inputs
    if "inputs" not in node:
        node["inputs"] = {}
    
    # Determinar el campo donde aplicar el estilo basándose en el tipo de nodo
    if node.get("class_type") == "SeargeTextInputV2":
        # Para nodos Searge, dependiendo del tipo:
        meta_title = node.get("_meta", {}).get("title", "")
        
        if "Style" in meta_title:
            # Nodo de Style - reemplazar completamente
            workflow[node_id]["inputs"]["prompt"] = style_prompt
            print(f"✅ Estilo aplicado al nodo Style {node_id}: {style_prompt}")
        elif "Main Prompt" in meta_title:
            # Nodo Main Prompt - añadir al final (IMPORTANTE: este es para test_main_force)
            current_prompt = node["inputs"].get("prompt", "")
            if current_prompt.strip():
                # Añadir el estilo al final con separación clara
                workflow[node_id]["inputs"]["prompt"] = f"{current_prompt.strip()}, {style_prompt}"
                print(f"🔧 *** MAIN PROMPT MODIFICADO *** {node_id}: '{current_prompt.strip()}' + ', {style_prompt}'")
            else:
                workflow[node_id]["inputs"]["prompt"] = style_prompt
                print(f"🔧 *** MAIN PROMPT CREADO *** {node_id}: {style_prompt}")
        else:
            # Otros nodos Searge - añadir al final
            current_prompt = node["inputs"].get("prompt", "")
            if current_prompt.strip():
                # Añadir el estilo al final con separación clara
                workflow[node_id]["inputs"]["prompt"] = f"{current_prompt.strip()}, {style_prompt}"
            else:
                workflow[node_id]["inputs"]["prompt"] = style_prompt
            print(f"✅ Estilo añadido al nodo {meta_title} {node_id}")
        
    elif node.get("class_type") == "SeargePromptAdapterV2":
        # Para el adaptador de prompts, no modificamos directamente
        print(f"⚠️ No se modifica directamente SeargePromptAdapterV2 {node_id}")
        return workflow
    elif node.get("class_type") == "CLIPTextEncode":
        # Nodo CLIPTextEncode típico
        current_prompt = node["inputs"].get("text", "")
        if current_prompt.strip() and style_prompt:
            workflow[node_id]["inputs"]["text"] = f"{current_prompt.strip()}, {style_prompt}"
        elif style_prompt:
            workflow[node_id]["inputs"]["text"] = style_prompt
        print(f"✅ Estilo aplicado al nodo CLIPTextEncode {node_id}")
    elif "prompt" in node["inputs"]:
        # Otro tipo de nodo con campo "prompt"
        current_prompt = node["inputs"].get("prompt", "")
        if current_prompt.strip() and style_prompt:
            workflow[node_id]["inputs"]["prompt"] = f"{current_prompt.strip()}, {style_prompt}"
        elif style_prompt:
            workflow[node_id]["inputs"]["prompt"] = style_prompt
        print(f"✅ Estilo aplicado al nodo con campo prompt {node_id}")
    elif "text" in node["inputs"]:
        # Nodo con campo "text"
        current_prompt = node["inputs"].get("text", "")
        if current_prompt.strip() and style_prompt:
            workflow[node_id]["inputs"]["text"] = f"{current_prompt.strip()}, {style_prompt}"
        elif style_prompt:
            workflow[node_id]["inputs"]["text"] = style_prompt
        print(f"✅ Estilo aplicado al nodo con campo text {node_id}")
    else:
        # Si no encontramos un campo apropiado, intentar con "prompt" por defecto
        workflow[node_id]["inputs"]["prompt"] = style_prompt
        print(f"✅ Estilo aplicado al nodo {node_id} usando campo prompt por defecto")
    
    return workflow

def get_workflow_nodes_for_style(workflow):
    """
    Obtiene una lista de nodos candidatos para aplicar estilos
    Retorna una lista de diccionarios con información de cada nodo
    """
    candidate_nodes = []
    
    for node_id, node_data in workflow.items():
        if not isinstance(node_data, dict) or "class_type" not in node_data:
            continue
        
        class_type = node_data.get("class_type", "")
        inputs = node_data.get("inputs", {})
        meta_title = node_data.get("_meta", {}).get("title", "")
        
        # Identificar nodos que pueden recibir texto/prompts
        node_info = None
        
        if class_type == "SeargeTextInputV2":
            # Determinar el tipo de nodo Searge por su título
            if "Style" in meta_title:
                node_info = {
                    "id": node_id,
                    "name": f"🎨 Searge Style ({node_id})",
                    "type": "Searge Text Input (Style)",
                    "description": f"{meta_title} - Nodo específico para estilos en workflows Searge",
                    "current_value": inputs.get("prompt", ""),
                    "recommended": True
                }
            elif "Main Prompt" in meta_title:
                node_info = {
                    "id": node_id,
                    "name": f"📝 Main Prompt ({node_id})",
                    "type": "Searge Text Input (Main)",
                    "description": f"{meta_title} - Prompt principal del workflow Searge",
                    "current_value": inputs.get("prompt", "")[:100] + "..." if len(inputs.get("prompt", "")) > 100 else inputs.get("prompt", ""),
                    "recommended": False
                }
            elif "Secondary Prompt" in meta_title:
                node_info = {
                    "id": node_id,
                    "name": f"📄 Secondary Prompt ({node_id})",
                    "type": "Searge Text Input (Secondary)",
                    "description": f"{meta_title} - Prompt secundario del workflow Searge",
                    "current_value": inputs.get("prompt", "")[:100] + "..." if len(inputs.get("prompt", "")) > 100 else inputs.get("prompt", ""),
                    "recommended": False
                }
            elif "Negative" not in meta_title:
                # Otros nodos de texto positivo
                node_info = {
                    "id": node_id,
                    "name": f"📝 {meta_title} ({node_id})",
                    "type": "Searge Text Input",
                    "description": f"{meta_title} - Nodo de entrada de texto Searge",
                    "current_value": inputs.get("prompt", "")[:100] + "..." if len(inputs.get("prompt", "")) > 100 else inputs.get("prompt", ""),
                    "recommended": False
                }
        elif class_type == "CLIPTextEncode" and "text" in inputs:
            prompt_content = inputs.get("text", "")
            # Determinar si es positivo o negativo por el contenido
            is_negative = any(neg_word in prompt_content.lower() for neg_word in 
                            ["bad", "ugly", "blurry", "distorted", "worst", "low quality", "deformed"])
            
            if not is_negative:  # Solo incluir prompts positivos
                node_info = {
                    "id": node_id,
                    "name": f"🔤 Prompt Positivo ({node_id})",
                    "type": "CLIP Text Encode",
                    "description": "Nodo de codificación de texto CLIP para prompts positivos",
                    "current_value": prompt_content[:100] + "..." if len(prompt_content) > 100 else prompt_content,
                    "recommended": False
                }
        elif "prompt" in inputs and "Negative" not in meta_title:
            node_info = {
                "id": node_id,
                "name": f"📝 {meta_title if meta_title else f'Nodo Prompt ({node_id})'}",
                "type": class_type,
                "description": f"Nodo de tipo {class_type} con campo prompt",
                "current_value": inputs.get("prompt", "")[:100] + "..." if len(inputs.get("prompt", "")) > 100 else inputs.get("prompt", ""),
                "recommended": False
            }
        
        if node_info:
            candidate_nodes.append(node_info)
    
    # Ordenar: primero los recomendados, luego por tipo, luego por ID
    candidate_nodes.sort(key=lambda x: (not x["recommended"], x["type"], x["id"]))
    
    return candidate_nodes

def adjust_conditioning_parameters_for_style(workflow, style_id, workflow_type):
    """
    Ajusta los parámetros de conditioning para mejorar el impacto visual de los estilos
    """
    if workflow_type != "searge":
        return workflow
    
    node_config = get_node_config(workflow_type)
    conditioning_node_id = node_config.get("conditioning_params_node_id")
    
    if not conditioning_node_id or conditioning_node_id not in workflow:
        print(f"⚠️ Nodo de conditioning parameters {conditioning_node_id} no encontrado")
        return workflow
    
    # Configuraciones de conditioning optimizadas para estilos
    style_conditioning_configs = {
        "default": {
            # Valores originales conservadores
            "positive_conditioning_scale": 1.5,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.1
        },
        "dramatic": {
            # Valores altos para estilos dramáticos (dentro de límites)
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.5
        },
        "cinematic": {
            # Valores altos para estilo cinematográfico
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.4
        },
        "neon": {
            # Valores máximos para efectos neón
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.6
        },
        "colorful": {
            # Valores altos para colores vibrantes
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.4
        },
        "artistic": {
            # Valores altos para efectos artísticos
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.45
        },
        "extreme_colorful": {
            # Valores máximos para colores súper vibrantes
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.7
        },
        "dark_moody": {
            # Valores altos para ambiente dramático oscuro
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.6
        },
        "hyperrealistic": {
            # Valores moderados-altos para hiperrealismo
            "positive_conditioning_scale": 1.9,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.4
        },
        "test_main_force": {
            # Configuración de prueba para estilo que fuerza Main Prompt
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.8  # Valor alto para hacer visible el efecto
        }
    }
    
    # Configuración por defecto para estilos no específicos (más fuerte que original)
    default_enhanced_config = {
        "positive_conditioning_scale": 1.8,
        "base_conditioning_scale": 2.0,
        "target_conditioning_scale": 2.0,
        "precondition_strength": 0.3
    }
    
    # Seleccionar configuración apropiada
    if style_id in style_conditioning_configs:
        config = style_conditioning_configs[style_id]
        print(f"🎯 Usando configuración específica para estilo: {style_id}")
    else:
        config = default_enhanced_config
        print(f"🔧 Usando configuración mejorada por defecto para estilo: {style_id}")
    
    # Aplicar la configuración
    conditioning_node = workflow[conditioning_node_id]
    if "inputs" not in conditioning_node:
        conditioning_node["inputs"] = {}
    
    # Actualizar los valores
    old_values = {}
    for param, new_value in config.items():
        old_values[param] = conditioning_node["inputs"].get(param, "N/A")
        conditioning_node["inputs"][param] = new_value
    
    # Log de los cambios
    print(f"✅ Parámetros de conditioning ajustados para estilo '{style_id}':")
    for param, new_value in config.items():
        old_value = old_values[param]
        print(f"   - {param}: {old_value} → {new_value}")
    
    return workflow
