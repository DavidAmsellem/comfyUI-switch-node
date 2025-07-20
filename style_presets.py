#!/usr/bin/env python3
"""
Configuración de estilos predefinidos para workflows
"""

# Estilos predefinidos organizados: primero los normales (menos creativos), luego los creativos
STYLE_PRESETS = {
    "default": {
        "name": "🎨 Por defecto",
        "description": "Sin estilo adicional, usa el prompt original del workflow",
        "style_prompt": "",
        "negative_prompt": "",
        "display_order": 1,
        "force_text2img": False,
        "category": "normal"
    },

    # === ESTILOS NORMALES (Menos creativos - Más fieles a la imagen original) ===
    
    "casa_ciudad": {
        "name": "🏙️ Casa de Ciudad",
        "description": "Estilo urbano moderno típico de casas en la ciudad con paredes contemporáneas y mobiliario metropolitano (estilo normal - menos creativo)",
        "style_prompt": "modern urban house interior, contemporary city home walls, clean painted walls, urban apartment style, metropolitan home atmosphere, city living room walls, modern residential walls, urban home decor, contemporary house interior, sleek city apartment walls, modern sectional sofas, glass coffee tables, urban dining sets, contemporary bar stools, city loft furniture, metropolitan lighting fixtures, urban area rugs, modern bookshelf units, contemporary wall sconces, sleek entertainment centers, photorealistic, residential photography",
        "negative_prompt": "rustic walls, country house style, rural home elements, wooden cabin walls, farmhouse style, beach house elements, countryside decor, rural atmosphere, vintage country walls, barn style walls, rustic furniture, farmhouse tables, country chairs, rural decorations, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 2,
        "denoise_override": 0.65,
        "force_text2img": True,
        "category": "normal",
        "controlnet_config": {
            "canny_strength": 0.30,
            "depth_strength": 0.40,
            "conditioning_scale": 1.6
        }
    },

    "casa_campo": {
        "name": "🌾 Casa de Campo",
        "description": "Estilo rústico y acogedor típico de casas rurales con paredes de materiales naturales y mobiliario campestre (estilo normal - menos creativo)",
        "style_prompt": "rustic country house interior, rural farmhouse walls, natural stone walls, wooden wall paneling, countryside home atmosphere, rural house walls, farmhouse style walls, country home decor, rustic residential walls, natural materials walls, warm country lighting, farmhouse dining tables, rustic wooden chairs, country kitchen cabinets, vintage farmhouse sinks, pastoral sofas, rustic coffee tables, country style armchairs, barn door furniture, rural area rugs, farmhouse pendant lights, country decorative baskets, wooden beam furniture, photorealistic, rural home photography",
        "negative_prompt": "modern city walls, urban apartment style, metropolitan decor, sleek modern walls, contemporary city elements, glass walls, steel materials, industrial city style, urban lighting, modern apartment walls, modern furniture, contemporary sofas, glass tables, urban decor, city lighting, metropolitan accessories, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 3,
        "denoise_override": 0.65,
        "force_text2img": True,
        "category": "normal",
        "controlnet_config": {
            "canny_strength": 0.25,
            "depth_strength": 0.45,
            "conditioning_scale": 1.6
        }
    },

    "casa_playa": {
        "name": "🏖️ Casa de Playa",
        "description": "Estilo costero relajado típico de casas junto al mar con paredes de colores claros (estilo normal - menos creativo)",
        "style_prompt": "coastal beach house interior, seaside home walls, light blue wall colors, beach house atmosphere, ocean view home walls, coastal residential walls, nautical home decor, beachy wall finishes, seaside cottage walls, marine inspired walls, natural beach lighting, photorealistic, coastal home photography",
        "negative_prompt": "dark wall colors, urban city style, industrial walls, heavy materials, metropolitan decor, concrete walls, steel elements, landlocked home style, mountain house elements, desert home style, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 4,
        "denoise_override": 0.65,
        "force_text2img": True,
        "category": "normal",
        "controlnet_config": {
            "canny_strength": 0.30,
            "depth_strength": 0.40,
            "conditioning_scale": 1.6
        }
    },

    "casa_montana": {
        "name": "🏔️ Casa de Montaña",
        "description": "Estilo alpino acogedor típico de casas en la montaña con paredes de madera y piedra (estilo normal - menos creativo)",
        "style_prompt": "mountain house interior, alpine cabin walls, natural wood walls, stone fireplace walls, cozy mountain home atmosphere, rustic log cabin walls, mountain lodge style walls, wooden beam walls, natural mountain materials, warm cabin lighting, solid wood dining tables, leather mountain chairs, stone fireplace furniture, alpine lodge sofas, mountain cabin coffee tables, log furniture pieces, leather armchairs, wooden storage chests, mountain wool rugs, rustic lantern lighting, alpine decorative items, natural wood shelving, photorealistic, mountain home photography",
        "negative_prompt": "urban city walls, modern apartment style, beach house elements, tropical decor, desert style, industrial materials, sleek modern walls, metropolitan atmosphere, glass walls, steel elements, modern furniture, contemporary sofas, glass tables, urban decor, city lighting, metropolitan accessories, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 5,
        "denoise_override": 0.65,
        "force_text2img": True,
        "category": "normal",
        "controlnet_config": {
            "canny_strength": 0.28,
            "depth_strength": 0.42,
            "conditioning_scale": 1.6
        }
    },

    "casa_moderna": {
        "name": "🏠 Casa Moderna",
        "description": "Estilo contemporáneo limpio típico de casas modernas con paredes minimalistas (estilo normal - menos creativo)",
        "style_prompt": "modern contemporary house interior, sleek modern walls, minimalist wall design, clean geometric walls, contemporary home atmosphere, modern residential walls, glass wall panels, open plan walls, modern architectural walls, natural modern lighting, minimalist dining tables, contemporary chairs, modern sectional sofas, glass coffee tables, sleek entertainment centers, modern bookshelves, contemporary lighting fixtures, geometric area rugs, modern accent chairs, clean line furniture, minimalist storage units, contemporary floor lamps, photorealistic, contemporary home photography",
        "negative_prompt": "vintage walls, rustic elements, ornate decorations, classical style, antique furniture, traditional patterns, country house style, farmhouse elements, baroque style, cluttered walls, rustic furniture, country decor, traditional accessories, vintage lighting, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 6,
        "denoise_override": 0.65,
        "force_text2img": True,
        "category": "normal",
        "controlnet_config": {
            "canny_strength": 0.32,
            "depth_strength": 0.38,
            "conditioning_scale": 1.6
        }
    },

    # === ESTILOS CREATIVOS (Más creativos - Transformaciones dramáticas) ===
    
    "minimalist": {
        "name": "⚪ Minimalista",
        "description": "Estilo minimalista moderno con líneas limpias y paredes despejadas (estilo creativo - más transformativo)",
        "style_prompt": "minimalist modern interior, clean white painted walls, smooth wall texture, geometric simple furniture, natural lighting, uncluttered space, zen atmosphere, pure lines, nordic influences, plain solid colored background walls, photorealistic, architectural photography",
        "negative_prompt": "cluttered walls, ornate wall decorations, busy wall patterns, textured walls, wallpaper, wall art, excessive furniture, dark wall colors, vintage wall elements, baroque wall style, multiple wall objects, crowded wall space, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall textures, brick walls, concrete walls, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 7,
        "denoise_override": 0.85,
        "force_text2img": True,
        "category": "creative",
        "controlnet_config": {
            "canny_strength": 0.35,
            "depth_strength": 0.40,
            "conditioning_scale": 2.0
        }
    },

    "luxury": {
        "name": "✨ Lujoso",
        "description": "Estilo de lujo premium con paredes elegantes y materiales de alta gama (estilo creativo - más transformativo)",
        "style_prompt": "luxury premium interior, elegant marble wall panels, sophisticated wall finishes, gold accent walls, velvet wall textures, silk wall coverings, high-end wall materials, opulent wall design, refined wall surfaces, premium wall treatments, crystal wall elements, photorealistic, professional interior photography",
        "negative_prompt": "cheap wall materials, plastic wall panels, basic painted walls, fluorescent lighting, cluttered wall space, industrial wall elements, rough wall textures, budget wall design, casual wall style, basic wall finishes, plain white walls, bare walls, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 8,
        "denoise_override": 0.85,
        "force_text2img": True,
        "category": "creative",
        "controlnet_config": {
            "canny_strength": 0.30,
            "depth_strength": 0.45,
            "conditioning_scale": 2.0
        }
    },

    "industrial": {
        "name": "🏭 Industrial",
        "description": "Estilo industrial urbano con paredes de materiales crudos y acabados metálicos (estilo creativo - más transformativo)",
        "style_prompt": "industrial loft interior, exposed concrete walls, raw brick wall texture, steel beam walls, metal wall fixtures, weathered wall surfaces, factory aesthetic walls, urban wall atmosphere, Edison bulb wall lighting, industrial wall materials, unfinished wall concrete, photorealistic, architectural photography",
        "negative_prompt": "ornate wall decorations, soft wall fabrics, pastel wall colors, delicate wall materials, classical wall elements, fancy wall furniture, decorative wall moldings, elegant wall finishes, luxury wall textures, painted smooth walls, wallpaper, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 9,
        "denoise_override": 0.85,
        "force_text2img": True,
        "category": "creative",
        "controlnet_config": {
            "canny_strength": 0.40,
            "depth_strength": 0.35,
            "conditioning_scale": 2.0
        }
    },

    "warm_cozy": {
        "name": "🔥 Cálido y Acogedor",
        "description": "Estilo cálido y acogedor con paredes en tonos tierra y materiales naturales (estilo creativo - más transformativo)",
        "style_prompt": "warm cozy interior, natural wood wall paneling, warm earth tone wall colors, textured wall surfaces, rustic wall elements, inviting wall atmosphere, amber wall lighting, wood wall textures, comfortable wall finishes, natural wall materials, fireplace wall accent, soft warm wall tones, photorealistic, interior photography",
        "negative_prompt": "cold wall colors, steel wall materials, harsh wall lighting, clinical wall atmosphere, stark white wall surfaces, modern minimalist walls, glass wall panels, fluorescent wall lights, sterile wall environment, concrete walls, industrial wall finishes, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 10,
        "denoise_override": 0.85,
        "force_text2img": True,
        "category": "creative",
        "controlnet_config": {
            "canny_strength": 0.25,
            "depth_strength": 0.40,
            "conditioning_scale": 1.8
        }
    },

    "futuristic": {
        "name": "🚀 Futurista",
        "description": "Estilo futurista high-tech con paredes tecnológicas avanzadas y materiales innovadores (estilo creativo - más transformativo)",
        "style_prompt": "futuristic sci-fi interior, sleek metallic wall surfaces, LED wall lighting panels, holographic wall elements, chrome wall finishes, glass wall panels, high-tech wall atmosphere, digital wall displays, cyberpunk wall influences, advanced wall materials, glowing wall accents, seamless wall design, photorealistic, modern architecture",
        "negative_prompt": "vintage wall elements, natural wood walls, rustic wall materials, traditional wall furniture, antique wall decorations, warm wall colors, organic wall textures, classical wall design, aged wall surfaces, brick walls, concrete walls, wallpaper, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 11,
        "denoise_override": 0.85,
        "force_text2img": True,
        "category": "creative",
        "controlnet_config": {
            "canny_strength": 0.45,
            "depth_strength": 0.35,
            "conditioning_scale": 2.0
        }
    },

    "artistic_bohemian": {
        "name": "🎭 Artístico Bohemio",
        "description": "Estilo artístico bohemio con paredes coloridas y elementos creativos (estilo creativo - más transformativo)",
        "style_prompt": "artistic bohemian interior, vibrant colored walls, eclectic wall textures, creative wall surfaces, artistic wall elements, colorful wall fabrics, unique wall lighting, expressive wall atmosphere, gallery wall vibe, creative wall chaos, textured wall finishes, bold wall colors, photorealistic, interior design photography",
        "negative_prompt": "minimalist wall design, corporate wall style, sterile wall environment, monochrome wall colors, uniform wall surfaces, stark wall lighting, conservative wall design, bland wall surfaces, business wall atmosphere, plain white walls, smooth painted walls, artwork on walls, paintings, prints, frames on walls, wall mounted decorations, wall artifacts, strange wall patterns, weird wall textures, wall defects, wall distortions, unnatural wall appearance, wall anomalies, bizarre wall elements, wall glitches, irregular wall surfaces, wall noise, corrupted wall textures",
        "display_order": 12,
        "denoise_override": 0.85,
        "force_text2img": True,
        "category": "creative",
        "controlnet_config": {
            "canny_strength": 0.20,
            "depth_strength": 0.45,
            "conditioning_scale": 1.9
        }
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
            "display_order": style_data["display_order"],
            "category": style_data.get("category", "normal")
        }
        
        # Incluir información de denoise si está disponible
        if "denoise_override" in style_data:
            style_info["denoise_override"] = style_data["denoise_override"]
            style_info["creativity_level"] = "high" if style_data["denoise_override"] >= 0.85 else "medium"
        
        styles.append(style_info)
    
    # Ordenar por display_order
    styles.sort(key=lambda x: x["display_order"])
    return styles

def get_available_styles_by_category():
    """
    Retorna estilos organizados por categoría para el dropdown
    """
    styles = get_available_styles()
    
    categorized_styles = {
        "normal": [],
        "creative": []
    }
    
    for style in styles:
        category = style.get("category", "normal")
        if category in categorized_styles:
            categorized_styles[category].append(style)
    
    return {
        "normal": {
            "label": "🏠 Estilos Normales (Menos creativos - Más fieles a la imagen)",
            "styles": categorized_styles["normal"]
        },
        "creative": {
            "label": "🎨 Estilos Creativos (Más creativos - Transformaciones dramáticas)",
            "styles": categorized_styles["creative"]
        }
    }

def get_style_prompt(style_id):
    """
    Obtiene el prompt de estilo para un ID dado
    """
    if style_id in STYLE_PRESETS:
        return STYLE_PRESETS[style_id]["style_prompt"]
    return ""

def get_style_negative_prompt(style_id):
    """
    Obtiene el prompt negativo de estilo para un ID dado
    """
    if style_id in STYLE_PRESETS:
        return STYLE_PRESETS[style_id].get("negative_prompt", "")
    return ""

def style_forces_text2img(style_id):
    """
    Verifica si un estilo fuerza el modo text2img
    """
    if style_id in STYLE_PRESETS:
        return STYLE_PRESETS[style_id].get("force_text2img", False)
    return False

def get_style_controlnet_config(style_id):
    """
    Obtiene la configuración de ControlNet para un estilo específico
    """
    if style_id in STYLE_PRESETS:
        return STYLE_PRESETS[style_id].get("controlnet_config", {})
    return {}

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
    Aplica un estilo al workflow modificando los nodos correspondientes (positivo y negativo)
    
    Args:
        workflow: El workflow JSON
        style_id: ID del estilo a aplicar
        custom_node_id: ID del nodo específico donde aplicar el estilo (opcional)
    """
    if style_id not in STYLE_PRESETS or style_id == "default":
        return workflow
    
    style_data = STYLE_PRESETS[style_id]
    style_prompt = style_data.get("style_prompt", "")
    negative_prompt = style_data.get("negative_prompt", "")
    
    if not style_prompt:
        return workflow
    
    # Detectar tipo de workflow
    workflow_type = detect_workflow_type(workflow)
    
    print(f"🎨 Aplicando estilo '{style_id}' con TEXT2IMG forzado")
    print(f"📝 Prompt positivo: {style_prompt[:100]}...")
    if negative_prompt:
        print(f"❌ Prompt negativo: {negative_prompt[:100]}...")
    
    # 1. Aplicar el prompt positivo del estilo
    force_main_prompt = style_data.get("force_main_prompt", False)
    
    if custom_node_id and custom_node_id in workflow:
        workflow = apply_style_to_specific_node(workflow, style_prompt, custom_node_id)
        print(f"🎯 Estilo aplicado a nodo específico seleccionado: {custom_node_id}")
    elif force_main_prompt:
        # FORZAR aplicación al nodo Main Prompt (nodo 3 en workflows Searge)
        force_node_id = "3"  # Main Prompt en workflows Searge
        if force_node_id in workflow:
            workflow = apply_style_to_specific_node(workflow, style_prompt, force_node_id)
            print(f"🔧 *** FORZANDO *** aplicación al Main Prompt {force_node_id}")
        else:
            print(f"❌ ERROR: No se encontró nodo Main Prompt {force_node_id}")
    else:
        # Usar la detección automática para nodo Style
        node_config = get_node_config(workflow_type)
        
        if workflow_type == "searge" and node_config["style_node_id"]:
            style_node_id = node_config["style_node_id"]
            if style_node_id in workflow:
                workflow = apply_style_to_specific_node(workflow, style_prompt, style_node_id)
                print(f"✅ Estilo aplicado al nodo Style: {style_node_id}")
        elif workflow_type == "basic":
            main_node_id = node_config["main_prompt_node_id"]
            if main_node_id in workflow:
                workflow = apply_style_to_specific_node(workflow, style_prompt, main_node_id)
                print(f"✅ Estilo aplicado al Main Prompt básico: {main_node_id}")
    
    # 2. Aplicar el prompt negativo si existe
    if negative_prompt:
        workflow = apply_negative_style_to_workflow(workflow, negative_prompt, workflow_type)
    
    # 3. Ajustar parámetros de conditioning para mayor impacto visual
    if style_id != "default":
        workflow = adjust_conditioning_parameters_for_style(workflow, style_id, workflow_type)
    
    # 4. Aplicar denoise_override si el estilo lo especifica
    if "denoise_override" in style_data:
        workflow = apply_denoise_override(workflow, style_data["denoise_override"], workflow_type)
    
    # 5. Aplicar configuraciones de ControlNet mejoradas
    if "controlnet_config" in style_data:
        workflow = apply_controlnet_optimizations(workflow, style_data["controlnet_config"], workflow_type)
    
    return workflow

def apply_negative_style_to_workflow(workflow, negative_prompt, workflow_type):
    """
    Aplica el prompt negativo del estilo a los nodos correspondientes
    """
    node_config = get_node_config(workflow_type)
    
    if workflow_type == "searge":
        # En workflows Searge, buscar nodos de prompt negativo
        for node_id, node_data in workflow.items():
            if (isinstance(node_data, dict) and 
                node_data.get('class_type') == 'SeargeTextInputV2'):
                
                meta_title = node_data.get("_meta", {}).get("title", "")
                
                # Aplicar a nodos de prompt negativo
                if "Negative Prompt" in meta_title or "negative" in meta_title.lower():
                    current_negative = node_data.get("inputs", {}).get("prompt", "")
                    if current_negative.strip():
                        # Añadir al negative prompt existente
                        workflow[node_id]["inputs"]["prompt"] = f"{current_negative.strip()}, {negative_prompt}"
                    else:
                        workflow[node_id]["inputs"]["prompt"] = negative_prompt
                    print(f"❌ Prompt negativo aplicado al nodo {node_id}")
                    break
    
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
        },
        "minimalist": {
            # Configuración optimizada para estilo minimalista
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.4
        },
        "luxury": {
            # Configuración optimizada para estilo lujoso
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.5
        },
        "industrial": {
            # Configuración optimizada para estilo industrial
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.6
        },
        "warm_cozy": {
            # Configuración optimizada para estilo cálido
            "positive_conditioning_scale": 1.8,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.3
        },
        "futuristic": {
            # Configuración optimizada para estilo futurista
            "positive_conditioning_scale": 2.0,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.7
        },
        "artistic_bohemian": {
            # Configuración optimizada para estilo artístico bohemio
            "positive_conditioning_scale": 1.9,
            "base_conditioning_scale": 2.0,
            "target_conditioning_scale": 2.0,
            "precondition_strength": 0.5
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

def apply_controlnet_optimizations(workflow, controlnet_config, workflow_type):
    """
    Aplica configuraciones optimizadas de ControlNet basadas en el estilo
    
    Args:
        workflow: El workflow JSON
        controlnet_config: Configuración específica del ControlNet para el estilo
        workflow_type: Tipo de workflow (searge, basic)
    """
    if workflow_type != "searge":
        print("⚠️ Optimizaciones de ControlNet solo soportadas para workflows Searge")
        return workflow
    
    # IDs de nodos ControlNet según el análisis del workflow
    canny_node_id = "677"  # ControlNetApplyAdvanced para Canny
    depth_node_id = "676"  # ControlNetApplyAdvanced para Depth
    
    # Aplicar configuración de Canny ControlNet
    canny_strength = controlnet_config.get("canny_strength", 0.35)
    if canny_node_id in workflow:
        old_canny = workflow[canny_node_id]["inputs"].get("strength", "N/A")
        workflow[canny_node_id]["inputs"]["strength"] = canny_strength
        print(f"🎯 ControlNet Canny strength: {old_canny} → {canny_strength}")
    else:
        print(f"⚠️ Nodo ControlNet Canny {canny_node_id} no encontrado")
    
    # Aplicar configuración de Depth ControlNet
    depth_strength = controlnet_config.get("depth_strength", 0.40)
    if depth_node_id in workflow:
        old_depth = workflow[depth_node_id]["inputs"].get("strength", "N/A")
        workflow[depth_node_id]["inputs"]["strength"] = depth_strength
        print(f"🎯 ControlNet Depth strength: {old_depth} → {depth_strength}")
    else:
        print(f"⚠️ Nodo ControlNet Depth {depth_node_id} no encontrado")
    
    # Mejorar configuración de conditioning general para ControlNet
    conditioning_scale = controlnet_config.get("conditioning_scale", 2.0)
    
    # Buscar nodos de conditioning y optimizarlos
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and "inputs" in node_data:
            class_type = node_data.get("class_type", "")
            
            # Optimizar negative conditioning que estaba muy bajo
            if class_type == "SeargeConditioningParameters":
                # Mejorar negative conditioning que estaba en 0.8 (muy bajo)
                old_negative = workflow[node_id]["inputs"].get("negative_conditioning_scale", "N/A")
                workflow[node_id]["inputs"]["negative_conditioning_scale"] = 1.5  # Mejorado de 0.8
                print(f"🔧 Negative conditioning mejorado: {old_negative} → 1.5")
                
                # Asegurar positive conditioning en el máximo
                old_positive = workflow[node_id]["inputs"].get("positive_conditioning_scale", "N/A")
                workflow[node_id]["inputs"]["positive_conditioning_scale"] = conditioning_scale
                print(f"🔧 Positive conditioning optimizado: {old_positive} → {conditioning_scale}")
    
    print(f"✅ Configuraciones de ControlNet aplicadas para mejor control de paredes")
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
