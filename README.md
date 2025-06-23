# API REST para ComfyUI

API REST que permite enviar una imagen para ser procesada en un flujo automático de ComfyUI para generar imágenes combinadas.

## Características

- Envío de imágenes mediante HTTP POST
- Procesamiento automático usando workflows predefinidos de ComfyUI
- Descarga de imágenes procesadas
- Monitoreo del estado de salud del servicio
- Información detallada del workflow

## Instalación

1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Configurar variables de entorno (opcional):**
```bash
cp .env.example .env
# Editar .env según tus necesidades
```

3. **Asegurarse de que ComfyUI esté ejecutándose:**
```bash
# ComfyUI debe estar corriendo en localhost:8188 por defecto
# O configurar COMFYUI_HOST y COMFYUI_PORT en .env
```

## Uso

### Iniciar el servidor

```bash
python app.py
```

El servidor se iniciará en `http://localhost:5000` por defecto.

### Endpoints disponibles

#### 1. Verificación de salud
```http
GET /health
```

**Respuesta:**
```json
{
  "status": "ok",
  "comfyui_connection": "ok",
  "version": "1.0.0"
}
```

#### 2. Procesar imagen (Principal)
```http
POST /process-image
```

**Parámetros:**
- `image` (archivo): Imagen a procesar (formatos: PNG, JPG, JPEG, GIF, BMP, WEBP)

**🔒 RESTRICCIÓN DE SEGURIDAD:** Por motivos de seguridad, esta API SOLO puede modificar el nodo LoadImage ID 97 que está conectado al SimpleFrameGenerator. No se permite especificar otros nodos.

**Ejemplo usando curl:**
```bash
curl -X POST \
  -F "image=@mi_imagen.jpg" \
  http://localhost:5000/process-image
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "prompt_id": "12345-abcde-67890",
  "output_images": [
    {
      "filename": "ComfyUI_00001_.png",
      "subfolder": "",
      "type": "output"
    }
  ],
  "message": "Imagen procesada exitosamente"
}
```

#### 3. Descargar imagen generada
```http
GET /get-image/<filename>?subfolder=<subfolder>&type=<type>
```

**Parámetros de consulta:**
- `subfolder`: Subcarpeta donde está la imagen
- `type`: Tipo de imagen (generalmente "output")

**Ejemplo:**
```bash
curl -o imagen_generada.png \
  "http://localhost:5000/get-image/ComfyUI_00001_.png?subfolder=&type=output"
```

#### 4. Información del workflow
```http
GET /workflow-info
```

**Respuesta:**
```json
{
  "workflow_file": "workflow_cuadro_bedroomV15x202.json",
  "total_nodes": 369,
  "load_image_nodes": [
    {
      "id": 123,
      "pos": [100, 200],
      "current_image": "default_image.png"
    }
  ],
  "last_node_id": 369,
  "last_link_id": 544
}
```

## Ejemplo de uso completo

### 1. Usando curl

```bash
# 1. Verificar que el servicio esté funcionando
curl http://localhost:5000/health

# 2. Enviar imagen para procesar
curl -X POST \
  -F "image=@mi_imagen.jpg" \
  http://localhost:5000/process-image

# 3. Descargar imagen procesada (usar filename de la respuesta anterior)
curl -o resultado.png \
  "http://localhost:5000/get-image/ComfyUI_00001_.png?subfolder=&type=output"
```

### 2. Usando Python requests

```python
import requests

# Enviar imagen
with open('mi_imagen.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post('http://localhost:5000/process-image', files=files)

if response.status_code == 200:
    result = response.json()
    print(f"Procesamiento exitoso: {result['prompt_id']}")
    
    # Descargar imagen procesada
    if result['output_images']:
        img_info = result['output_images'][0]
        img_response = requests.get(
            f"http://localhost:5000/get-image/{img_info['filename']}",
            params={
                'subfolder': img_info['subfolder'],
                'type': img_info['type']
            }
        )
        
        with open('imagen_procesada.png', 'wb') as f:
            f.write(img_response.content)
        print("Imagen descargada como 'imagen_procesada.png'")
```

### 3. Usando JavaScript (Frontend)

```javascript
// Función para procesar imagen
async function processImage(imageFile) {
    const formData = new FormData();
    formData.append('image', imageFile);
    
    try {
        const response = await fetch('http://localhost:5000/process-image', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('Imagen procesada:', result.prompt_id);
            
            // Descargar imagen procesada
            if (result.output_images.length > 0) {
                const imgInfo = result.output_images[0];
                const imgUrl = `http://localhost:5000/get-image/${imgInfo.filename}?subfolder=${imgInfo.subfolder}&type=${imgInfo.type}`;
                
                // Crear enlace de descarga
                const a = document.createElement('a');
                a.href = imgUrl;
                a.download = imgInfo.filename;
                a.click();
            }
        } else {
            console.error('Error:', result.error);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Usar con un input file
document.getElementById('fileInput').addEventListener('change', (e) => {
    if (e.target.files[0]) {
        processImage(e.target.files[0]);
    }
});
```

## Configuración

### Variables de entorno

- `API_PORT`: Puerto del servidor API (por defecto: 5000)
- `DEBUG`: Modo debug (por defecto: False)
- `COMFYUI_HOST`: Host de ComfyUI (por defecto: localhost)
- `COMFYUI_PORT`: Puerto de ComfyUI (por defecto: 8188)

### Archivos importantes

- `workflow_cuadro_bedroomV15x202.json`: Workflow de ComfyUI que define el procesamiento
- `temp_uploads/`: Directorio temporal para imágenes subidas
- `outputs/`: Directorio para imágenes procesadas

## Manejo de errores

La API devuelve códigos de estado HTTP apropiados:

- `200`: Éxito
- `400`: Error en la petición (archivo inválido, parámetros faltantes, etc.)
- `404`: Recurso no encontrado
- `500`: Error interno del servidor

Todos los errores incluyen un mensaje descriptivo en JSON:

```json
{
  "error": "Descripción del error"
}
```

## Limitaciones

- Tamaño máximo de archivo: 16MB (configurable)
- Formatos soportados: PNG, JPG, JPEG, GIF, BMP, WEBP
- Requiere ComfyUI ejecutándose y accesible
- El workflow debe contener al menos un nodo LoadImage

## Solución de problemas

### ComfyUI no se conecta
- Verificar que ComfyUI esté ejecutándose
- Verificar host y puerto en configuración
- Verificar firewall/permisos de red

### Error al procesar imagen
- Verificar formato de imagen soportado
- Verificar tamaño de archivo
- Revisar logs del servidor para detalles

### Timeout en procesamiento
- Imágenes muy grandes pueden tardar más
- Verificar recursos del sistema (CPU/GPU/RAM)
- Aumentar timeout si es necesario
