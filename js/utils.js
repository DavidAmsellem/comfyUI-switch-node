// js/utils.js
import { state } from './state.js';

export function showStatus(message, type = 'info') {
    const statusMessages = document.getElementById('statusMessages');
    if (!statusMessages) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `status-message status-${type}`;
    
    const timestamp = new Date().toLocaleTimeString();
    msgDiv.textContent = `[${timestamp}] ${message}`;
    
    statusMessages.appendChild(msgDiv);
    statusMessages.scrollTop = statusMessages.scrollHeight;

    if (statusMessages.children.length > 50) {
        statusMessages.removeChild(statusMessages.firstChild);
    }
}

export async function checkHealth() {
    const indicator = document.getElementById('healthIndicator');
    const statusEl = document.getElementById('comfyStatus'); // Nuevo monitor

    try {
        const response = await fetch(`${state.API_BASE_URL}/health`);
        const data = await response.json();

        if (data.status === 'ok' && data.comfyui_connection === 'ok') {
            indicator.textContent = '✅ API Conectada';
            indicator.className = 'health-indicator health-ok';
        } else {
            indicator.textContent = '⚠️ API OK, ComfyUI Desconectado';
            indicator.className = 'health-indicator health-error';
        }
    } catch (error) {
        indicator.textContent = '❌ API No Disponible';
        indicator.className = 'health-indicator health-error';
        if(statusEl) {
            statusEl.textContent = '❓ Desconectado';
            statusEl.className = 'indicator status-offline';
        }
    }
}

// --- Monitor de Estado del Sistema ---
export function startSystemMonitoring() {
    updateSystemStatus();
    setInterval(updateSystemStatus, 2000);
}

async function updateSystemStatus() {
    const statusEl = document.getElementById('comfyStatus');
    if (!statusEl) return;

    try {
        const response = await fetch(`${state.API_BASE_URL}/system-status`);
        const data = await response.json();
        
        statusEl.className = 'indicator'; 
        
        if (data.online) {
            if (data.status === 'processing') {
                statusEl.textContent = `⚙️ ${data.message}`;
                statusEl.classList.add('status-processing');
            } else {
                statusEl.textContent = `🟢 ${data.message}`;
                statusEl.classList.add('status-idle');
            }
        } else {
            statusEl.textContent = '❌ Offline';
            statusEl.classList.add('status-error');
        }
    } catch (error) {
        console.error("Error monitoring:", error);
    }
}

// --- MODAL ---
export function showImageModal(imageSrc, imageInfo = '') {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalInfo = document.getElementById('modalInfo');
    
    if (modal && modalImage) {
        modalImage.src = imageSrc;
        if(modalInfo) modalInfo.textContent = imageInfo;
        modal.style.display = 'flex';
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

export function closeImageModal() {
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
        const modalImage = document.getElementById('modalImage');
        if (modalImage) modalImage.src = '';
    }
}

export function setupImageZoomModal() {
    // Lógica para inicializar listeners del modal y observer
    const modalClose = document.getElementById('modalClose');
    const modal = document.getElementById('imageModal');
    
    if (modalClose) modalClose.addEventListener('click', closeImageModal);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeImageModal();
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeImageModal();
    });

    // Observer para hacer clickeables las imágenes nuevas
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { 
                    const images = node.tagName === 'IMG' ? [node] : node.querySelectorAll('img');
                    images.forEach(img => enableModalForImage(img));
                }
            });
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

function enableModalForImage(img) {
    if (img.hasAttribute('data-modal-enabled')) return;
    
    // Filtro básico para no afectar iconos o UI
    const parentClass = img.parentElement?.className || '';
    if (parentClass.includes('result') || parentClass.includes('batch') || img.classList.contains('preview-image')) {
        img.style.cursor = 'pointer';
        img.setAttribute('data-modal-enabled', 'true');
        img.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            showImageModal(img.src, img.alt || 'Imagen generada');
        });
    }
}