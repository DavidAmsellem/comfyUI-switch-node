from style_presets import get_available_styles

def get_perspective_style_for_style(style_id):
    mapping = {
        'default': 'realistic', 'casa_ciudad': 'realistic', 'casa_campo': 'subtle',
        'casa_playa': 'subtle', 'casa_montana': 'dramatic', 'casa_moderna': 'realistic',
        'minimalist': 'subtle', 'luxury': 'dramatic', 'industrial': 'realistic',
        'warm_cozy': 'subtle', 'futuristic': 'realistic', 'artistic_bohemian': 'dramatic'
    }
    return mapping.get(style_id, 'realistic')

def get_wall_color_for_style(style_id):
    mapping = {
        'default': 240, 'casa_ciudad': 235, 'casa_campo': 245, 'casa_playa': 250,
        'casa_montana': 230, 'casa_moderna': 240, 'minimalist': 252, 'luxury': 235,
        'industrial': 220, 'warm_cozy': 242, 'futuristic': 245, 'artistic_bohemian': 238
    }
    return mapping.get(style_id, 240)

def get_depth_intensity_for_style(style_id):
    mapping = {
        'default': 0.7, 'casa_ciudad': 0.6, 'casa_campo': 0.8, 'casa_playa': 0.5,
        'casa_montana': 0.9, 'casa_moderna': 0.6, 'minimalist': 0.4, 'luxury': 0.9,
        'industrial': 0.8, 'warm_cozy': 0.7, 'futuristic': 0.5, 'artistic_bohemian': 0.8
    }
    return mapping.get(style_id, 0.8)