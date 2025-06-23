# Guía de Instalación y Configuración

## Requisitos Previos

1. **ComfyUI instalado y funcionando**
   - ComfyUI debe estar ejecutándose en `localhost:8188` (puerto por defecto)
   - Verificar que ComfyUI responde en: http://localhost:8188

2. **Python 3.7 o superior**
   ```bash
   python3 --version
   ```

3. **pip (gestor de paquetes de Python)**
   ```bash
   pip3 --version
   ```

## Instalación Rápida

### Opción 1: Script automático (Recomendado)
```bash
chmod +x start.sh
./start.sh
```

### Opción 2: Instalación manual

1. **Crear entorno virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # En Linux/Mac
   # o
   venv\Scripts\activate     # En Windows
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Crear directorios necesarios:**
   ```bash
   mkdir -p temp_uploads outputs
   ```

4. **Configurar variables de entorno (opcional):**
   ```bash
   cp .env.example .env
   # Editar .env según tus necesidades
   ```

5. **Iniciar la API:**
   ```bash
   python app.py
   ```

## Verificación de la Instalación

1. **Probar la API con el script de prueba:**
   ```bash
   python test_api.py
   ```

2. **Probar con curl:**
   ```bash
   curl http://localhost:5000/health
   ```

3. **Abrir el cliente web:**
   Abrir `web_client.html` en un navegador web

## Estructura de Archivos

```
comfyUI-apirest/
├── app.py                              # Servidor principal de la API
├── requirements.txt                    # Dependencias de Python
├── start.sh                           # Script de inicio automático
├── test_api.py                        # Script de pruebas
├── web_client.html                    # Cliente web para pruebas
├── workflow_cuadro_bedroomV15x202.json # Workflow de ComfyUI
├── .env.example                       # Ejemplo de configuración
├── .gitignore                         # Archivos a ignorar en git
├── README.md                          # Documentación completa
├── INSTALL.md                         # Esta guía
├── temp_uploads/                      # Directorio temporal (se crea automáticamente)
├── outputs/                           # Directorio de salida (se crea automáticamente)
└── venv/                             # Entorno virtual (se crea automáticamente)
```

## Configuración

### Variables de Entorno

Crear archivo `.env` basado en `.env.example`:

```bash
# Puerto de la API
API_PORT=5000

# Modo debug
DEBUG=False

# Configuración de ComfyUI
COMFYUI_HOST=localhost
COMFYUI_PORT=8188

# Límites de archivos
MAX_CONTENT_LENGTH=16777216  # 16MB
```

### Configuración de ComfyUI

1. **ComfyUI debe estar ejecutándose**
2. **El workflow debe estar en el mismo directorio que la API**
3. **El workflow debe contener al menos un nodo LoadImage**

## Resolución de Problemas

### Error: "ComfyUI no se conecta"
```bash
# Verificar que ComfyUI esté ejecutándose
curl http://localhost:8188/system_stats

# Si no responde, iniciar ComfyUI:
cd /ruta/a/ComfyUI
python main.py
```

### Error: "Workflow no encontrado"
```bash
# Verificar que el archivo existe
ls -la workflow_cuadro_bedroomV15x202.json

# Si no existe, copiar desde ComfyUI o crear uno nuevo
```

### Error: "Dependencias faltantes"
```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

### Error: "Puerto ocupado"
```bash
# Cambiar puerto en .env
echo "API_PORT=5001" >> .env

# O usar variable de entorno
API_PORT=5001 python app.py
```

### Error: "Permisos de archivos"
```bash
# Verificar permisos de directorios
chmod 755 temp_uploads outputs

# Verificar permisos del script
chmod +x start.sh
```

## Uso en Producción

### Configuración con systemd (Linux)

1. **Crear archivo de servicio:**
   ```bash
   sudo nano /etc/systemd/system/comfyui-api.service
   ```

2. **Contenido del servicio:**
   ```ini
   [Unit]
   Description=ComfyUI API REST
   After=network.target

   [Service]
   Type=simple
   User=tu_usuario
   WorkingDirectory=/ruta/completa/a/comfyUI-apirest
   Environment=PATH=/ruta/completa/a/comfyUI-apirest/venv/bin
   ExecStart=/ruta/completa/a/comfyUI-apirest/venv/bin/python app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Activar servicio:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable comfyui-api.service
   sudo systemctl start comfyui-api.service
   ```

### Configuración con nginx (Proxy reverso)

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoreo

### Logs de la aplicación
```bash
# Ver logs en tiempo real
tail -f app.log

# Ver logs con systemd
sudo journalctl -f -u comfyui-api.service
```

### Verificación de salud
```bash
# Script simple de monitoreo
while true; do
    curl -s http://localhost:5000/health || echo "API DOWN $(date)"
    sleep 60
done
```

## Actualizaciones

```bash
# Actualizar dependencias
pip install -r requirements.txt --upgrade

# Reiniciar servicio
sudo systemctl restart comfyui-api.service
```

## Soporte

Para obtener ayuda:

1. Revisar logs de la aplicación
2. Verificar configuración de ComfyUI
3. Probar endpoints individualmente con curl
4. Usar el script de pruebas: `python test_api.py`
