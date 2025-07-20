"""
ComfyUI API REST - Nodos personalizados
"""

from .dynamic_frame_node_improved import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Registrar todos los nodos
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
