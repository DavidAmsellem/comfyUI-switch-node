import uuid
from config import WORKFLOW_CONFIG

def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in WORKFLOW_CONFIG['allowed_extensions']

def generate_unique_filename(original_filename):
    if '.' in original_filename:
        name, ext = original_filename.rsplit('.', 1)
        return f"{uuid.uuid4().hex}.{ext.lower()}"
    return f"{uuid.uuid4().hex}.png"