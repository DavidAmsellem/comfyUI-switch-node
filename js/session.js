// js/session.js
import { state } from './state.js';
import { showStatus } from './utils.js';
import { restoreBatchJob, updateBatchWorkflowPreview } from './batch.js';
import { restoreIndividualJob } from './individual.js';

export function saveState() {
    const s = {
        roomType: document.getElementById('roomTypeSelect')?.value,
        orientation: document.getElementById('orientationSelect')?.value,
        workflow: document.getElementById('workflowSelect')?.value,
        style: document.getElementById('styleSelect')?.value,
        styleNode: document.getElementById('styleNodeSelect')?.value,
        frameColor: document.querySelector('input[name="frameColor"]:checked')?.value || 'black',
        batchRoomTypes: Array.from(document.getElementById('batchRoomTypes')?.selectedOptions || []).map(o => o.value),
        batchOrientations: Array.from(document.getElementById('batchOrientations')?.selectedOptions || []).map(o => o.value)
    };
    localStorage.setItem('comfyui_client_state', JSON.stringify(s));
}

export function restoreState() {
    try {
        const saved = localStorage.getItem('comfyui_client_state');
        if (!saved) return;
        const s = JSON.parse(saved);

        // Restauración en cadena (cascada)
        const roomSelect = document.getElementById('roomTypeSelect');
        if (s.roomType && roomSelect) {
            roomSelect.value = s.roomType;
            // Disparar evento manualmente para activar la cascada
            roomSelect.dispatchEvent(new Event('change'));
            
            setTimeout(() => {
                const orientSelect = document.getElementById('orientationSelect');
                if (s.orientation && orientSelect) {
                    orientSelect.value = s.orientation;
                    orientSelect.dispatchEvent(new Event('change'));
                    
                    setTimeout(() => {
                         const wfSelect = document.getElementById('workflowSelect');
                         if (s.workflow && wfSelect) {
                             wfSelect.value = s.workflow;
                             wfSelect.dispatchEvent(new Event('change'));
                         }
                    }, 100);
                }
            }, 100);
        }

        // Restaurar Batch
        if (s.batchRoomTypes) {
             const batchRoom = document.getElementById('batchRoomTypes');
             if(batchRoom) {
                 Array.from(batchRoom.options).forEach(o => o.selected = s.batchRoomTypes.includes(o.value));
             }
        }
        // Actualizar preview del batch
        setTimeout(updateBatchWorkflowPreview, 500);
        
        showStatus('💾 Estado restaurado', 'info');
    } catch (e) {
        console.error('Error restaurando estado', e);
    }
}

export async function loadSessionJobs() {
    try {
        const response = await fetch(`${state.API_BASE_URL}/session/jobs`);
        const data = await response.json();
        
        if (data.success && data.jobs) {
            Object.values(data.jobs).forEach(job => {
                if (job.type === 'batch') {
                    restoreBatchJob(job);
                } else if (job.type === 'individual') {
                    restoreIndividualJob(job);
                }
            });
            
            // Forzar visualización si hay batch
            const hasBatch = Object.values(data.jobs).some(j => j.type === 'batch');
            if(hasBatch) {
                const section = document.getElementById('batchResultsSection');
                if(section) section.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error cargando sesión:', error);
    }
}

export async function cleanupOldJobs() {
    try {
        await fetch(`${state.API_BASE_URL}/session/cleanup`, {
            method: 'POST',
            body: JSON.stringify({ hours: 24 }),
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (e) { console.error(e); }
}

export function clearState() {
    localStorage.removeItem('comfyui_client_state');
    location.reload();
}