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
        frameColor: document.querySelector('input[name="frameColor"]:checked')?.value,
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

        const roomSelect = document.getElementById('roomTypeSelect');
        if (s.roomType && roomSelect) {
            roomSelect.value = s.roomType;
            roomSelect.dispatchEvent(new Event('change'));
            setTimeout(() => {
                const orientSelect = document.getElementById('orientationSelect');
                if (s.orientation && orientSelect) {
                    orientSelect.value = s.orientation;
                    orientSelect.dispatchEvent(new Event('change'));
                    setTimeout(() => {
                         const wfSelect = document.getElementById('workflowSelect');
                         if (s.workflow && wfSelect) wfSelect.value = s.workflow;
                    }, 100);
                }
            }, 100);
        }
        
        if (s.style) document.getElementById('styleSelect').value = s.style;
        if (s.batchRoomTypes) {
             const batchRoom = document.getElementById('batchRoomTypes');
             Array.from(batchRoom.options).forEach(o => o.selected = s.batchRoomTypes.includes(o.value));
        }
        setTimeout(updateBatchWorkflowPreview, 500);
    } catch (e) { console.error(e); }
}

export async function loadSessionJobs() {
    try {
        const response = await fetch(`${state.API_BASE_URL}/session/jobs`);
        const data = await response.json();
        if (data.success && data.jobs) {
            Object.values(data.jobs).forEach(job => {
                if (job.type === 'batch') restoreBatchJob(job);
                else if (job.type === 'individual') restoreIndividualJob(job);
            });
            if (Object.values(data.jobs).some(j => j.type === 'batch')) {
                document.getElementById('batchResultsSection').style.display = 'block';
            }
        }
    } catch (e) { console.error("Error loading session", e); }
}

export async function cleanupOldJobs() {
    try {
        await fetch(`${state.API_BASE_URL}/session/cleanup`, {
            method: 'POST', body: JSON.stringify({ hours: 24 }), headers: {'Content-Type': 'application/json'}
        });
    } catch (e) { console.error(e); }
}

export function clearState() {
    if(confirm("¿Borrar preferencias guardadas?")) {
        localStorage.removeItem('comfyui_client_state');
        location.reload();
    }
}

export async function clearSession() {
    if(!confirm("⚠️ ¿Borrar todo el historial de trabajos e imágenes?")) return;
    try {
        const res = await fetch(`${state.API_BASE_URL}/session/clear`, { method: 'POST' });
        if(res.ok) {
            document.getElementById('individualResults').innerHTML = '';
            document.getElementById('batchResults').innerHTML = '';
            document.getElementById('batchResultsSection').style.display = 'none';
            state.activeIndividualJobs.clear();
            state.restoredBatchJobs.clear();
            showStatus('🧹 Sesión limpiada', 'success');
        }
    } catch(e) { showStatus('❌ Error limpiando sesión', 'error'); }
}