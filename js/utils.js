import { state } from './state.js';

export function showStatus(message, type = 'info') {
    const statusMessages = document.getElementById('statusMessages');
    if (!statusMessages) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `status-message status-${type}`;
    msgDiv.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    
    statusMessages.appendChild(msgDiv);
    statusMessages.scrollTop = statusMessages.scrollHeight;
}

export async function checkHealth() {
    const indicator = document.getElementById('healthIndicator');
    try {
        const response = await fetch(`${state.API_BASE_URL}/health`);
        const data = await response.json();

        if (data.status === 'ok' && data.comfyui_connection === 'ok') {
            indicator.textContent = '✅ API Conectada';
            indicator.className = 'indicator health-ok';
        } else {
            indicator.textContent = '⚠️ API OK, ComfyUI Error';
            indicator.className = 'indicator health-error';
        }
    } catch (error) {
        indicator.textContent = '❌ API Desconectada';
        indicator.className = 'indicator health-error';
    }
}

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
        
        if (data.online) {
            if (data.status === 'processing') {
                statusEl.textContent = `⚙️ ${data.message}`;
                statusEl.className = 'indicator status-processing';
            } else {
                statusEl.textContent = `🟢 ${data.message}`;
                statusEl.className = 'indicator status-idle';
            }
        } else {
            statusEl.textContent = '❌ ComfyUI Offline';
            statusEl.className = 'indicator status-offline';
        }
    } catch (error) {
        // Silencioso si falla
    }
}

export function setupImageZoomModal() {
    const modal = document.getElementById('imageModal');
    const closeBtn = document.getElementById('modalClose');
    if (closeBtn) closeBtn.onclick = closeImageModal;
    if (modal) modal.onclick = (e) => { if (e.target === modal) closeImageModal(); };
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeImageModal(); });
}

export function showImageModal(src, info = '') {
    const modal = document.getElementById('imageModal');
    const img = document.getElementById('modalImage');
    if (modal && img) {
        img.src = src;
        modal.classList.add('show');
    }
}

export function closeImageModal() {
    document.getElementById('imageModal')?.classList.remove('show');
}