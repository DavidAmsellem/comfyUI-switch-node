import { state } from './state.js';
import { showStatus, showImageModal } from './utils.js';

// --- FUNCIÓN QUE FALTABA ---
export async function loadWorkflowNodesForBatch(wfId) {
    // Se mantiene vacía para evitar errores de importación
}

export function updateBatchWorkflowPreview() {
    const rooms = Array.from(document.getElementById('batchRoomTypes').selectedOptions);
    const countSpan = document.getElementById('workflowCount');
    const previewBox = document.getElementById('selectedWorkflowsPreview');
    
    if(countSpan && previewBox) {
        if(rooms.length > 0) {
            previewBox.style.display = 'block';
            countSpan.textContent = `${rooms.length} tipos seleccionados`;
        } else {
            previewBox.style.display = 'none';
        }
    }
}

export async function processBatch() {
    if (!state.selectedFile) return showStatus('❌ Selecciona una imagen primero', 'error');
    
    const roomTypes = Array.from(document.getElementById('batchRoomTypes').selectedOptions).map(o=>o.value);
    const orientations = Array.from(document.getElementById('batchOrientations').selectedOptions).map(o=>o.value);
    
    if (roomTypes.length === 0) return showStatus('⚠️ Selecciona al menos un tipo de habitación', 'error');

    state.batchCounter++;
    const localId = state.batchCounter;

    const config = {
        room_types: roomTypes,
        orientations: orientations,
        frame_color: document.querySelector('input[name="batchFrameColor"]:checked')?.value || 'black',
        style: document.getElementById('batchStyleSelect').value,
        include_upscale: document.getElementById('batchIncludeUpscale').checked
    };

    // Crear UI inmediatamente
    createBatchContainer(localId, "Conectando...", "Calculando...");

    try {
        const formData = new FormData();
        formData.append('image', state.selectedFile);
        formData.append('batch_config', JSON.stringify(config));
        
        const res = await fetch(`${state.API_BASE_URL}/process-batch`, { method:'POST', body:formData });
        const data = await res.json();
        
        if(data.success) {
            showStatus(`🚀 Lote #${localId} iniciado`, 'info');
            updateBatchHeader(localId, data.batch_id);
            // Pasamos AMBOS IDs: el de tracking (memoria) y el de sesión (disco)
            startBatchPoll(localId, data.batch_id, data.session_job_id);
        } else {
            markBatchError(localId, data.error);
        }
    } catch(e) { 
        markBatchError(localId, e.message);
    }
}

// --- Funciones Internas ---

function createBatchContainer(localId, serverId, totalText) {
    const div = document.createElement('div');
    div.className = 'batch-container'; 
    div.id = `batch-${localId}`;
    div.innerHTML = `
        <div class="batch-header">
            <strong>📦 Lote #${localId}</strong>
            <small style="color:#666; font-size:0.8em" id="bid-disp-${localId}">${serverId}</small>
        </div>
        <div style="margin: 10px 0;">
            Estado: <span id="b-status-${localId}" class="indicator status-processing">Iniciando</span> 
            <span id="b-stats-${localId}" style="margin-left:10px; font-size:0.9em">Esperando datos...</span>
        </div>
        <div id="b-imgs-${localId}" class="batch-workflow-images"></div>
    `;
    const parent = document.getElementById('batchResults');
    if(parent) {
        parent.prepend(div);
        document.getElementById('batchResultsSection').style.display = 'block';
    }
}

function updateBatchHeader(localId, serverId) {
    const el = document.getElementById(`bid-disp-${localId}`);
    if(el) el.textContent = `ID: ${serverId}`;
}

function markBatchError(localId, errorMsg) {
    const st = document.getElementById(`b-status-${localId}`);
    if(st) {
        st.textContent = "Error";
        st.className = "indicator status-error";
    }
    showStatus(`❌ Error en Lote #${localId}: ${errorMsg}`, 'error');
}

// --- POLL ROBUSTO (PLAN A: Memoria, PLAN B: Disco) ---
function startBatchPoll(localId, batchId, sessionJobId) {
    let lastLen = 0;
    let useFallback = false; // Bandera para saber si el servidor perdió la memoria

    const interval = setInterval(async () => {
        try {
            let st = null;

            // 1. INTENTO PLAN A: Memoria RAM (Rápido y con detalles de progreso)
            if (!useFallback) {
                const res = await fetch(`${state.API_BASE_URL}/batch-status/${batchId}`);
                if (res.ok) {
                    st = await res.json();
                } else {
                    // Si da 404, el servidor se reinició. Cambiamos a Plan B.
                    useFallback = true;
                    // Si no tenemos sessionJobId (casos antiguos), usamos batchId como fallback
                    if (!sessionJobId) sessionJobId = batchId; 
                }
            }

            // 2. INTENTO PLAN B: Disco (Persistencia)
            if (useFallback) {
                const res = await fetch(`${state.API_BASE_URL}/session/jobs/${sessionJobId}`);
                if (res.ok) {
                    const diskData = await res.json();
                    // Convertimos el formato de disco al formato que espera la UI
                    st = {
                        status: diskData.status,
                        // Calculamos completados contando las imágenes guardadas
                        completed_workflows: diskData.results ? diskData.results.length : 0,
                        total_workflows: diskData.total_workflows || '?',
                        results: diskData.results || [],
                        successful: diskData.results ? diskData.results.length : 0,
                        failed: 0 // En disco no solemos guardar fallos detallados
                    };
                }
            }

            // Si no conseguimos datos de ningún lado, salimos de este ciclo
            if (!st) return;
            
            // 3. ACTUALIZAR UI
            const statusEl = document.getElementById(`b-status-${localId}`);
            const statsEl = document.getElementById(`b-stats-${localId}`);
            
            if(statusEl) {
                statusEl.textContent = st.status === 'processing' ? 'Procesando' : st.status;
                // Si estamos en fallback y status es 'processing', probablemente sea un zombie (servidor reiniciado)
                if(useFallback && st.status === 'processing') {
                     statusEl.textContent = 'Interrumpido'; // O "Zombie"
                     statusEl.className = 'indicator status-error';
                     // Detenemos el poll porque si el server reinició, este trabajo no avanzará más
                     clearInterval(interval);
                } else {
                    statusEl.className = `indicator status-${st.status === 'completed' ? 'idle' : 'processing'}`;
                    if(st.status === 'completed') statusEl.className = 'indicator health-ok';
                }
            }

            if(statsEl) {
                const total = st.total_workflows || '?';
                const done = st.completed_workflows || 0;
                const remain = (total !== '?') ? total - done : '?';
                statsEl.textContent = `✅ ${done} | ⏳ Faltan: ${remain}`;
            }
            
            // Renderizar nuevas imágenes
            if(st.results && st.results.length > lastLen) {
                appendImages(localId, st.results.slice(lastLen));
                lastLen = st.results.length;
            }
            
            if(st.status === 'completed' || st.status === 'error') {
                clearInterval(interval);
                if(st.status === 'completed') showStatus(`✅ Lote #${localId} finalizado`, 'success');
            }

        } catch(e) { console.error(e); }
    }, 2000);
}

function appendImages(localId, results) {
    const container = document.getElementById(`b-imgs-${localId}`);
    if(!container) return;

    results.forEach(r => {
        // A veces viene 'generated_images' (memoria), a veces es el objeto directo (disco)
        const imgs = r.generated_images || [r]; 
        
        imgs.forEach(img => {
            if (!img.session_url && !img.url) return; // Protección

            const div = document.createElement('div');
            div.className = 'workflow-result-item';
            
            let url = img.session_url || img.url;
            if (url && !url.startsWith('http') && !url.startsWith('/')) url = `/${url}`;
            const fullUrl = url.startsWith('http') ? url : `${state.API_BASE_URL}${url}`;
            
            // Intentar sacar nombre del workflow o usar ID
            const label = r.workflow ? r.workflow.split('/').pop() : (img.filename ? 'Img' : 'Res');

            div.innerHTML = `
                <div style="font-size:0.8em; margin-bottom:5px; font-weight:bold; color:#555;">${label}</div>
                <img src="${fullUrl}" loading="lazy">
            `;
            div.querySelector('img').onclick = () => showImageModal(fullUrl);
            container.appendChild(div);
        });
    });
}

export function restoreBatchJob(job) {
    state.batchCounter++;
    const localId = state.batchCounter;
    
    // Usamos tracking_id si existe, si no, el id normal
    const serverId = job.batch_tracking_id || job.id;
    
    createBatchContainer(localId, serverId, "Restaurado");
    
    // Restaurar imágenes ya existentes
    if (job.results && Array.isArray(job.results)) {
         appendImages(localId, job.results);
    }
    
    // SIEMPRE iniciamos el poll, pero le pasamos el ID de sesión para que use el Plan B si hace falta
    // job.id es el sessionJobId
    startBatchPoll(localId, serverId, job.id);
}