import { state } from './state.js';
import { showStatus, showImageModal } from './utils.js';

export async function loadWorkflowNodesForBatch(wfId) {
    // Implementación opcional si necesitas cargar nodos de estilo dinámicos
}

export function updateBatchWorkflowPreview() {
    // Contar workflows seleccionados
    const rooms = Array.from(document.getElementById('batchRoomTypes').selectedOptions);
    const count = document.getElementById('workflowCount');
    if(count) count.textContent = rooms.length ? "Filtrado activado" : "Todos";
}

export async function processBatch() {
    if (!state.selectedFile) return showStatus('❌ Sin imagen', 'error');
    
    state.batchCounter++;
    const bid = state.batchCounter;
    const config = {
        room_types: Array.from(document.getElementById('batchRoomTypes').selectedOptions).map(o=>o.value),
        orientations: Array.from(document.getElementById('batchOrientations').selectedOptions).map(o=>o.value),
        frame_color: document.querySelector('input[name="batchFrameColor"]:checked')?.value,
        style: document.getElementById('batchStyleSelect').value,
        include_upscale: document.getElementById('batchIncludeUpscale').checked
    };

    try {
        const formData = new FormData();
        formData.append('image', state.selectedFile);
        formData.append('batch_config', JSON.stringify(config));
        
        const res = await fetch(`${state.API_BASE_URL}/process-batch`, { method:'POST', body:formData });
        const data = await res.json();
        
        if(data.success) {
            showStatus(`🚀 Lote #${bid} iniciado`, 'info');
            createBatchContainer(bid, data.batch_id, data.total_workflows);
            startBatchPoll(bid, data.batch_id);
        }
    } catch(e) { showStatus(`❌ Error lote: ${e.message}`, 'error'); }
}

function createBatchContainer(localId, serverId, total) {
    const div = document.createElement('div');
    div.className = 'batch-container';
    div.id = `batch-${localId}`;
    div.innerHTML = `
        <div class="batch-header"><h4>Lote #${localId} <small>(${serverId})</small></h4></div>
        <div>Estado: <span id="b-status-${localId}">Iniciando</span> (<span id="b-prog-${localId}">0</span>/${total})</div>
        <div id="b-imgs-${localId}" class="batch-workflow-images"></div>
    `;
    document.getElementById('batchResults').prepend(div);
    document.getElementById('batchResultsSection').style.display = 'block';
}

function startBatchPoll(localId, serverId) {
    let lastLen = 0;
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${state.API_BASE_URL}/batch-status/${serverId}`);
            if(!res.ok) return;
            const st = await res.json();
            
            document.getElementById(`b-status-${localId}`).textContent = st.status;
            document.getElementById(`b-prog-${localId}`).textContent = st.completed_workflows;
            
            if(st.results && st.results.length > lastLen) {
                appendImages(localId, st.results.slice(lastLen));
                lastLen = st.results.length;
            }
            
            if(st.status === 'completed' || st.status === 'error') clearInterval(interval);
        } catch(e) {}
    }, 2000);
}

function appendImages(localId, results) {
    const c = document.getElementById(`b-imgs-${localId}`);
    results.forEach(r => {
        if(r.generated_images) {
            r.generated_images.forEach(img => {
                const div = document.createElement('div');
                div.className = 'workflow-result-item';
                const url = img.url.startsWith('http') ? img.url : `${state.API_BASE_URL}${img.url}`;
                div.innerHTML = `<div>${r.workflow_id}</div><img src="${url}">`;
                div.querySelector('img').onclick = () => showImageModal(url);
                c.appendChild(div);
            });
        }
    });
}

export function restoreBatchJob(job) {
    state.batchCounter++;
    createBatchContainer(state.batchCounter, job.batch_tracking_id, job.total_workflows);
    if(job.status === 'processing') startBatchPoll(state.batchCounter, job.batch_tracking_id);
    else {
         document.getElementById(`b-status-${state.batchCounter}`).textContent = job.status;
         // Lógica para renderizar resultados históricos si es necesario
    }
}