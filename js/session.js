import { state } from './state.js';
import { restoreBatchJob } from './batch.js'; 
import { restoreIndividualJob } from './individual.js';

export function saveState() {
    const uiState = {
        mode: document.getElementById('processMode').value,
        roomType: document.getElementById('roomTypeSelect').value,
        orientation: document.getElementById('orientationSelect').value,
        style: document.getElementById('styleSelect').value,
        // Guardamos selects múltiples como arrays
        batchRooms: Array.from(document.getElementById('batchRoomTypes').selectedOptions).map(o=>o.value),
        batchOrients: Array.from(document.getElementById('batchOrientations').selectedOptions).map(o=>o.value)
    };
    localStorage.setItem('comfy_ui_lite_state', JSON.stringify(uiState));
}

export function restoreState() {
    const saved = localStorage.getItem('comfy_ui_lite_state');
    if (!saved) return;
    
    try {
        const data = JSON.parse(saved);
        // Restaurar modo
        if (data.mode) {
            const modeSel = document.getElementById('processMode');
            modeSel.value = data.mode;
            modeSel.dispatchEvent(new Event('change'));
        }
        
        // Restaurar Batch Selects (un poco más complejo por ser múltiples)
        if(data.batchRooms) {
            const sel = document.getElementById('batchRoomTypes');
            Array.from(sel.options).forEach(opt => {
                opt.selected = data.batchRooms.includes(opt.value);
            });
            sel.dispatchEvent(new Event('change')); // Para actualizar preview
        }
        // ... Lógica similar para otros campos si se desea
    } catch(e) { console.log("Error restaurando estado UI", e); }
}

export async function loadSessionJobs() {
    try {
        const res = await fetch(`${state.API_BASE_URL}/session/jobs`);
        const data = await res.json();
        
        if(data.success && data.jobs) {
            // Invertimos para mostrar más reciente arriba si el backend no lo hizo
            data.jobs.forEach(job => {
                if (job.type === 'batch') {
                    restoreBatchJob(job);
                } else if (job.type === 'individual') {
                    restoreIndividualJob(job);
                }
            });
        }
    } catch (e) {
        console.error("Error cargando historial de sesión", e);
    }
}

export async function clearSession() {
    if(confirm('¿Borrar todo el historial de trabajos del servidor?')) {
        await fetch(`${state.API_BASE_URL}/session/clear`, {method:'POST'});
        location.reload();
    }
}

export function clearState() {
    localStorage.removeItem('comfy_ui_lite_state');
    location.reload();
}

// Función helper para limpieza periódica
export function cleanupOldJobs() {
    // Llama al backend para borrar archivos viejos de la carpeta jobs_data
    fetch(`${state.API_BASE_URL}/session/cleanup`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({hours: 24})
    });
}