// js/individual.js
import { state } from './state.js';
import { showStatus, showImageModal } from './utils.js';

export async function processImage() {
    if (!state.selectedFile) return showStatus('❌ Selecciona imagen', 'error');
    
    const workflowId = document.getElementById('workflowSelect').value;
    if (!workflowId) return showStatus('❌ Selecciona workflow', 'error');

    state.individualJobCounter++;
    const localJobId = `individual_${state.individualJobCounter}`;
    const startTime = new Date();

    // Preparar UI
    createIndividualJobContainer(localJobId, startTime);
    
    state.activeIndividualJobs.set(localJobId, {
        localId: localJobId,
        status: 'submitting',
        startTime: startTime
    });

    try {
        const formData = new FormData();
        formData.append('image', state.selectedFile);
        formData.append('workflow', workflowId);
        formData.append('frame_color', document.querySelector('input[name="frameColor"]:checked')?.value || 'black');
        formData.append('style', document.getElementById('styleSelect')?.value || 'default');
        formData.append('include_upscale', document.getElementById('includeUpscale')?.checked);
        
        // Enviar
        const response = await fetch(`${state.API_BASE_URL}/process-image`, { method: 'POST', body: formData });
        const data = await response.json();

        if (data.success) {
            showStatus(`✅ Trabajo #${state.individualJobCounter} enviado`, 'success');
            startIndividualJobPolling(localJobId, data.job_id);
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
        updateJobStatusUI(localJobId, 'error', error.message);
    }
}

function createIndividualJobContainer(localId, date) {
    const container = document.getElementById('individualResults');
    const div = document.createElement('div');
    div.className = 'individual-job-result processing';
    div.id = `individual-job-${localId}`;
    div.innerHTML = `
        <div class="individual-job-header">🎯 Job #${state.individualJobCounter} <small>${date.toLocaleTimeString()}</small></div>
        <div class="individual-job-stats">
            <span>Estado: <strong id="status-${localId}">Enviando...</strong></span>
        </div>
        <div id="images-container-${localId}" class="individual-job-images"></div>
    `;
    if(container.firstChild) container.insertBefore(div, container.firstChild);
    else container.appendChild(div);
    
    document.getElementById('individualJobsSection').style.display = 'block';
}

function startIndividualJobPolling(localId, serverId) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${state.API_BASE_URL}/session/jobs/${serverId}`);
            const job = await res.json();
            
            updateJobStatusUI(localId, job.status, job.current_operation);
            
            if (job.results && job.results.length > 0) {
                renderImages(localId, job.results);
            }

            if (job.status === 'completed' || job.status === 'error') {
                clearInterval(interval);
            }
        } catch (e) { console.error(e); }
    }, 2000);
    
    state.individualPollingIntervals.set(localId, interval);
}

function updateJobStatusUI(localId, status, operation) {
    const el = document.getElementById(`status-${localId}`);
    const div = document.getElementById(`individual-job-${localId}`);
    if(el) el.textContent = status;
    if(div) div.className = `individual-job-result ${status}`;
}

function renderImages(localId, images) {
    const container = document.getElementById(`images-container-${localId}`);
    container.innerHTML = '';
    images.forEach(img => {
        const i = document.createElement('img');
        const url = img.session_url || img.url;
        // Asegurar URL absoluta si es necesario
        i.src = url.startsWith('http') ? url : `${state.API_BASE_URL}${url}`;
        i.onclick = () => showImageModal(i.src);
        container.appendChild(i);
    });
}

// Para restaurar sesiones anteriores
export function restoreIndividualJob(job) {
    // Lógica simplificada para recrear el UI de un trabajo existente
    state.individualJobCounter++;
    createIndividualJobContainer(`restored_${job.id}`, new Date(job.created_at));
    if(job.status === 'processing') {
        startIndividualJobPolling(`restored_${job.id}`, job.id);
    } else if (job.status === 'completed' && job.image_urls) {
        updateJobStatusUI(`restored_${job.id}`, 'completed', 'Finalizado');
        // Mapear urls simples a objetos esperados por renderImages
        const imgObjs = job.image_urls.map(url => ({ url: url }));
        renderImages(`restored_${job.id}`, imgObjs);
    }
}