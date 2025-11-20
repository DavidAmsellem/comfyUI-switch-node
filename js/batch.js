// js/batch.js
import { state } from './state.js';
import { showStatus, showImageModal } from './utils.js';

export async function loadWorkflowNodesForBatch(workflowId) {
    // Cargar nodos opcionales para el estilo (misma lógica que individual)
    try {
        const res = await fetch(`${state.API_BASE_URL}/workflow-nodes/${workflowId}`);
        const data = await res.json();
        const sel = document.getElementById('batchStyleNodeSelect');
        if(sel && data.candidate_nodes) {
            sel.innerHTML = '<option value="">🔧 Auto-detectar</option>';
            data.candidate_nodes.forEach(n => {
                const opt = document.createElement('option');
                opt.value = n.id;
                opt.textContent = n.name;
                sel.appendChild(opt);
            });
        }
    } catch(e) { console.error(e); }
}

export function updateBatchWorkflowPreview() {
    // Filtra workflows basados en la selección múltiple
    const rooms = Array.from(document.getElementById('batchRoomTypes').selectedOptions).map(o => o.value);
    const orients = Array.from(document.getElementById('batchOrientations').selectedOptions).map(o => o.value);
    
    let count = 0;
    let html = '';
    
    // Lógica de filtrado cruzando state.workflowsStructure
    // ... (Simplificado para brevedad, copia la lógica de tu script original) ...
    
    document.getElementById('workflowCount').textContent = 'Calculando...'; // Actualizar UI real aquí
}

export async function processBatch() {
    if (!state.selectedFile) return showStatus('❌ Sin imagen', 'error');

    state.batchCounter++;
    state.activeBatches++;
    const currentBatchId = state.batchCounter;

    // Recoger configuración
    const rooms = Array.from(document.getElementById('batchRoomTypes').selectedOptions).map(o => o.value);
    const orients = Array.from(document.getElementById('batchOrientations').selectedOptions).map(o => o.value);
    
    const batchConfig = {
        room_types: rooms,
        orientations: orients,
        frame_color: document.querySelector('input[name="batchFrameColor"]:checked')?.value || 'black',
        style: document.getElementById('batchStyleSelect')?.value || 'default',
        include_upscale: document.getElementById('batchIncludeUpscale')?.checked
    };

    try {
        const formData = new FormData();
        formData.append('image', state.selectedFile);
        formData.append('batch_config', JSON.stringify(batchConfig));

        const res = await fetch(`${state.API_BASE_URL}/process-batch`, { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            showStatus(`🚀 Lote #${currentBatchId} iniciado`, 'info');
            createBatchResultsContainer(currentBatchId, data.batch_id, data.total_workflows);
            startBatchPolling(currentBatchId, data.batch_id);
        }
    } catch (e) {
        state.activeBatches--;
        showStatus(`❌ Error lote: ${e.message}`, 'error');
    }
}

function createBatchResultsContainer(localId, serverId, total) {
    document.getElementById('batchResultsSection').style.display = 'block';
    const container = document.getElementById('batchResults');
    
    const div = document.createElement('div');
    div.className = 'batch-container';
    div.id = `batch-container-${localId}`;
    div.innerHTML = `
        <div class="batch-header">
            <h4>Lote #${localId} <small>(${serverId})</small></h4>
            <div class="batch-stats">
                Estado: <span id="batch-status-${localId}">Iniciando</span> | 
                Completados: <span id="batch-completed-${localId}">0</span>/${total}
            </div>
        </div>
        <div id="batch-images-${localId}" class="batch-workflow-images"></div>
    `;
    
    if(container.firstChild) container.insertBefore(div, container.firstChild);
    else container.appendChild(div);
}

function startBatchPolling(localId, serverId) {
    let lastCount = 0;
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${state.API_BASE_URL}/batch-status/${serverId}`);
            const status = await res.json();
            
            // Actualizar texto
            const statEl = document.getElementById(`batch-status-${localId}`);
            const compEl = document.getElementById(`batch-completed-${localId}`);
            if(statEl) statEl.textContent = status.status;
            if(compEl) compEl.textContent = status.completed_workflows;

            // Nuevas imágenes
            if (status.results && status.results.length > lastCount) {
                const newResults = status.results.slice(lastCount);
                appendBatchImages(localId, newResults);
                lastCount = status.results.length;
            }

            if (status.status === 'completed' || status.status === 'error') {
                clearInterval(interval);
                state.activeBatches--;
                // Limpiar servidor después de un rato
                setTimeout(() => fetch(`${state.API_BASE_URL}/batch-status/${serverId}`, {method: 'DELETE'}), 30000);
            }
        } catch (e) { console.error(e); }
    }, 2000);
    
    state.pollingIntervals.set(serverId, interval);
}

function appendBatchImages(localId, results) {
    const container = document.getElementById(`batch-images-${localId}`);
    results.forEach(r => {
        if(r.success && r.generated_images) {
            r.generated_images.forEach(imgData => {
                const div = document.createElement('div');
                div.className = 'workflow-result-item';
                const url = imgData.url.startsWith('http') ? imgData.url : `${state.API_BASE_URL}${imgData.url}`;
                
                div.innerHTML = `
                    <div style="font-size:0.8em; font-weight:bold">${r.workflow_id}</div>
                    <img src="${url}" style="width:100%; border-radius:4px; cursor:pointer">
                `;
                div.querySelector('img').onclick = () => showImageModal(url, r.workflow_id);
                container.appendChild(div);
            });
        }
    });
}

export function restoreBatchJob(job) {
    const key = `${job.id}_${job.batch_tracking_id}`;
    if (state.restoredBatchJobs.has(key)) return;
    
    state.restoredBatchJobs.add(key);
    state.batchCounter++;
    
    createBatchResultsContainer(state.batchCounter, job.batch_tracking_id, job.total_workflows);
    
    // Si ya terminó, mostrar imágenes estáticas, si no, iniciar polling
    if(job.status === 'processing') {
        startBatchPolling(state.batchCounter, job.batch_tracking_id);
    } else {
        // Renderizar imágenes guardadas en el historial del job
        // (Lógica similar a appendBatchImages adaptada a los datos de sesión)
        document.getElementById(`batch-status-${state.batchCounter}`).textContent = job.status;
    }
}