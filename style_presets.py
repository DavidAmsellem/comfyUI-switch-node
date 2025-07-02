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
        "description": "Colores vibrantes y saturados con creatividad aumentada",
        "style_prompt": "vibrant explosive colors, rainbow spectrum interior design, neon bright saturated surfaces, bold chromatic furniture, vivid colorful walls and floors, intense color palette, electric bright materials, fluorescent colored elements, psychedelic interior atmosphere, empty clean back wall for artwork display, creative colorful transformation",
        "display_order": 2,
        "denoise_override": 0.85
    },
    "warm": {
        "name": "🔥 Cálido",
        "description": "Transformación cálida y acogedora con materiales dorados",
        "style_prompt": "warm golden interior transformation, cozy luxurious atmosphere, amber honey-colored materials, golden hour sunlight flooding room, warm wood textures, brass and copper accents, soft warm lighting fixtures, comfortable inviting furniture, sunset glow illumination, rich warm color palette, empty clean back wall ready for artwork, creative warm redesign",
        "display_order": 3,
        "denoise_override": 0.85
    },
    "cool": {
        "name": "❄️ Fresco",
        "description": "Transformación moderna con tonos fríos y cristalinos",
        "style_prompt": "cool modern interior transformation, crisp blue and silver materials, ice crystal lighting effects, contemporary steel and glass elements, arctic fresh atmosphere, cool mint and blue color scheme, crystalline surfaces, modern minimalist furniture, fresh clean air feeling, empty pristine back wall for display, creative cool redesign",
        "display_order": 4,
        "denoise_override": 0.85
    },
    "luxury": {
        "name": "✨ Lujoso",
        "description": "Transformación premium con materiales de alta gama",
        "style_prompt": "luxury interior transformation, premium marble and gold materials, crystal chandeliers and elegant lighting, sophisticated high-end furniture, opulent rich textures and fabrics, sumptuous velvet and silk elements, exclusive designer finishes, lavish premium quality surfaces, refined luxurious atmosphere, empty elegant back wall for premium artwork display, creative luxury redesign",
        "display_order": 5,
        "denoise_override": 0.85
    },
    "minimalist": {
        "name": "⚪ Minimalista",
        "description": "Transformación minimalista zen con líneas puras",
        "style_prompt": "minimalist interior transformation, pure white and neutral surfaces, clean geometric lines, uncluttered zen space, essential furniture only, serene minimalist atmosphere, natural light flooding, simple elegant forms, stark clean beauty, geometric simplicity, empty perfect back wall for single artwork focus, creative minimalist redesign",
        "display_order": 6,
        "denoise_override": 0.85
    },
    "industrial": {
        "name": "🏭 Industrial",
        "description": "Transformación industrial urbana con materiales crudos",
        "style_prompt": "industrial interior transformation, exposed concrete and steel materials, raw urban aesthetic, metal pipe fixtures, brick and concrete textures, industrial lighting fixtures, weathered metal surfaces, urban loft atmosphere, rustic industrial furniture, factory-inspired design, empty raw back wall for industrial art display, creative industrial redesign",
        "display_order": 7,
        "denoise_override": 0.85
    },
    "natural": {
        "name": "🌿 Natural",
        "description": "Transformación orgánica con abundantes elementos naturales",
        "style_prompt": "natural organic interior transformation, abundant wood and stone materials, living plant elements throughout, earthy natural color palette, organic flowing textures, biophilic design integration, natural fiber furniture, bamboo and rattan accents, nature-inspired lighting, fresh green atmosphere, empty natural back wall for nature artwork display, creative organic redesign",
        "display_order": 8,
        "denoise_override": 0.85
    },
    "vintage": {
        "name": "🕰️ Vintage",
        "description": "Transformación vintage con elementos retro auténticos",
        "style_prompt": "vintage interior transformation, authentic retro materials and furniture, aged leather and worn wood surfaces, classic vintage color palette, nostalgic atmosphere with period details, antique fixtures and lighting, timeless elegant design, weathered vintage textures, old-world charm and character, empty classic back wall for vintage artwork display, creative retro redesign",
        "display_order": 9,
        "denoise_override": 0.85
    },
    "futuristic": {
        "name": "🚀 Futurista",
        "description": "Transformación futurista high-tech con tecnología avanzada",
        "style_prompt": "futuristic interior transformation, high-tech surfaces and materials, holographic lighting effects, sleek metallic finishes, advanced technology integration, sci-fi aesthetic design, LED strip lighting everywhere, glass and chrome elements, cyberpunk atmosphere, digital displays, empty high-tech back wall for digital art display, creative futuristic redesign",
        "display_order": 10,
        "denoise_override": 0.85
    },
    "artistic": {
        "name": "🎭 Artístico",
        "description": "Transformación artística con elementos creativos y expresivos",
        "style_prompt": "artistic interior transformation, creative gallery-worthy design, unique sculptural furniture, expressive bold colors and textures, artistic composition and layout, creative lighting installations, avant-garde design elements, inspirational artistic atmosphere, innovative material combinations, empty artistic back wall perfect for featured artwork display, creative artistic redesign",
        "display_order": 11,
        "denoise_override": 0.85
    },
    "scandinavian": {
        "name": "🇸🇪 Escandinavo",
        "description": "Transformación escandinava con hygge y funcionalidad nórdica",
        "style_prompt": "scandinavian interior transformation, light natural wood throughout, cozy hygge atmosphere, functional nordic design, white and light color palette, natural textures and materials, minimalist functional furniture, soft natural lighting, clean scandinavian lines, comfortable hygge elements, empty clean back wall for nordic art display, creative scandinavian redesign",
        "display_order": 12,
        "denoise_override": 0.85
    },
    "dramatic": {
        "name": "🎭 Dramático",
        "description": "Transformación dramática con contrastes intensos y iluminación teatral",
        "style_prompt": "dramatic interior transformation, intense theatrical lighting, high contrast shadows and highlights, bold dramatic color combinations, striking visual impact design, moody atmospheric lighting effects, powerful chiaroscuro effects, dramatic architectural elements, intense emotional atmosphere, empty dramatic back wall for powerful artwork display, creative dramatic redesign",
        "display_order": 13,
        "denoise_override": 0.85
    },
    "cinematic": {
        "name": "🎬 Cinematográfico",
        "description": "Transformación cinematográfica con calidad de película profesional",
        "style_prompt": "cinematic interior transformation, professional movie-quality lighting, film-grade cinematography setup, hollywood-style design elements, cinematic color grading atmosphere, dramatic film lighting techniques, movie set quality materials, professional cinematographic composition, film grain texture aesthetic, empty cinematic back wall for featured display, creative cinematic redesign",
        "display_order": 14,
        "denoise_override": 0.85
    },
    "neon": {
        "name": "⚡ Neón",
        "description": "Transformación neón cyberpunk con luces vibrantes",
        "style_prompt": "neon cyberpunk interior transformation, glowing neon lighting everywhere, electric blue and hot pink accents, fluorescent tube lighting, retro-futuristic atmosphere, vibrant glowing surfaces, cyberpunk aesthetic design, neon sign elements, electric color scheme, dark background with bright accents, empty neon-lit back wall for digital artwork display, creative neon redesign",
        "display_order": 15,
        "denoise_override": 0.85
    },
    "botanical": {
        "name": "🌿 Botánico",
        "description": "Transformación botánica con abundante vegetación tropical",
        "style_prompt": "botanical interior transformation, lush tropical plants everywhere, jungle-like vegetation integration, living wall installations, abundant green foliage, tropical paradise atmosphere, natural botanical elements, biophilic design throughout, garden-like interior space, nature sanctuary feeling, empty botanical back wall for nature artwork display, creative botanical redesign",
        "display_order": 16,
        "denoise_override": 0.85
    },
    "extreme_colorful": {
        "name": "🌈💥 Súper Colorido",
        "description": "Transformación explosiva con colores extremadamente intensos",
        "style_prompt": "(((explosive colorful interior transformation))), (((rainbow spectrum surfaces everywhere))), (((neon psychedelic design elements))), kaleidoscope color palette, fluorescent bright materials, electric vivid textures, chromatic explosion atmosphere, intense saturation throughout, vibrant color combinations, empty colorful back wall for rainbow artwork display, creative explosive redesign",
        "display_order": 17,
        "denoise_override": 0.9
    },
    "dark_moody": {
        "name": "🖤 Oscuro y Atmosférico",
        "description": "Transformación oscura con atmósfera misteriosa y dramática",
        "style_prompt": "(((dark moody interior transformation))), (((gothic dramatic atmosphere))), (((mysterious shadow lighting))), noir aesthetic design, deep contrast materials, brooding darkness throughout, chiaroscuro lighting effects, dark sophisticated elements, mysterious ambiance, empty dark back wall for dramatic artwork display, creative dark redesign",
        "display_order": 18,
        "denoise_override": 0.85
    },
    "hyperrealistic": {
        "name": "📸 Hiperrealista",
        "description": "Transformación hiperrealista con detalles fotográficos perfectos",
        "style_prompt": "(((hyperrealistic interior transformation))), (((photographic quality materials))), (((ultra-detailed surface textures))), 8K resolution finish, professional photography lighting, sharp focus on every detail, realistic material properties, lifelike surface rendering, perfect photorealistic quality, empty photorealistic back wall for detailed artwork display, creative hyperrealistic redesign",
        "display_order": 19,
        "denoise_override": 0.75
    },
    "test_main_force": {
        "name": "🧪 TEST: Forzar Main Prompt",
        "description": "Estilo de prueba que fuerza aplicación al nodo Main Prompt",
        "style_prompt": "(((TESTING MAIN PROMPT OVERRIDE TRANSFORMATION))), (((experimental creative redesign))), forced main node application test, override style node behavior, main prompt injection test, creative testing transformation, empty testing back wall for experimental display",
        "display_order": 20,
        "force_main_prompt": True,
        "force_target_node": "main_prompt",
        "denoise_override": 0.9
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
        style_info = {
            "id": style_id,
            "name": style_data["name"],
            "description": style_data["description"],
            "display_order": style_data["display_order"]
        }
        
        # Incluir información de denoise si está disponible
        if "denoise_override" in style_data:
            style_info["denoise_override"] = style_data["denoise_override"]
            style_info["creativity_level"] = "high" if style_data["denoise_override"] >= 0.85 else "medium"
        
        styles.append(style_info)
    
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
            print(f"🔧 *** FORZANDO *** aplicación al Main Prompt {force_node_id} (estilo: {force_node_id})")
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
    
    # 3. Aplicar denoise_override si el estilo lo especifica
    if style_id in STYLE_PRESETS and "denoise_override" in STYLE_PRESETS[style_id]:
        workflow = apply_denoise_override(workflow, STYLE_PRESETS[style_id]["denoise_override"], workflow_type)
    
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

def apply_denoise_override(workflow, denoise_value, workflow_type):
    """
    Aplica un valor de denoise específico al workflow para permitir más creatividad
    
    Args:
        workflow: El workflow JSON
        denoise_value: Valor de denoise a aplicar (ej: 0.85)
        workflow_type: Tipo de workflow (searge, basic)
    """
    if workflow_type != "searge":
        print(f"⚠️ Denoise override solo soportado para workflows Searge")
        return workflow
    
    # En workflows Searge, el denoise está en el nodo SeargeImage2ImageAndInpainting (613)
    denoise_node_id = "613"
    
    if denoise_node_id not in workflow:
        print(f"⚠️ Nodo de denoise {denoise_node_id} no encontrado en el workflow")
        return workflow
    
    # Aplicar el nuevo valor de denoise
    old_denoise = workflow[denoise_node_id]["inputs"].get("denoise", "N/A")
    workflow[denoise_node_id]["inputs"]["denoise"] = denoise_value
    
    print(f"🎨 Denoise ajustado para mayor creatividad: {old_denoise} → {denoise_value}")
    print(f"   ✨ Esto permitirá transformaciones más dramáticas manteniendo la estructura")
    
    return workflow

def determine_real_workflow_mode(workflow, style_id):
    """
    Determina el modo real que usará el workflow con un estilo específico
    SIMPLIFICADO: Ahora todos los estilos usan img2img
    """
    return {
        "real_mode": "img2img",
        "confidence": "high",
        "mode_source": "simplified_system",
        "description": "Preserva composición aplicando transformaciones creativas con denoise alto"
    }
