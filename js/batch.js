import { state } from './state.js';
import { showStatus, showImageModal } from './utils.js';

export async function loadWorkflowNodesForBatch(wfId) {}

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
            startBatchPoll(localId, data.batch_id, data.session_job_id);
        } else {
            markBatchError(localId, data.error);
        }
    } catch(e) { 
        markBatchError(localId, e.message);
    }
}

function createBatchContainer(localId, serverId, totalText) {
    const div = document.createElement('div');
    div.className = 'batch-container'; 
    div.id = `batch-${localId}`;
    div.innerHTML = `
        <div class="batch-header" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <strong>📦 Lote #${localId}</strong>
                <br><small style="color:#666; font-size:0.8em" id="bid-disp-${localId}">${serverId}</small>
            </div>
            <button onclick="window.cancelBatch('${serverId}', '${localId}')" class="mini-btn" style="background:#dc3545; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">
                🛑 Cancelar
            </button>
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

function startBatchPoll(localId, batchId, sessionJobId) {
    let lastLen = 0;
    let useFallback = false; 

    const interval = setInterval(async () => {
        try {
            let st = null;

            // Plan A: Memoria
            if (!useFallback) {
                const res = await fetch(`${state.API_BASE_URL}/batch-status/${batchId}`);
                if (res.ok) {
                    st = await res.json();
                } else {
                    useFallback = true;
                    if (!sessionJobId) sessionJobId = batchId; 
                }
            }

            // Plan B: Disco
            if (useFallback) {
                const res = await fetch(`${state.API_BASE_URL}/session/jobs/${sessionJobId}`);
                if (res.ok) {
                    const diskData = await res.json();
                    st = {
                        status: diskData.status,
                        completed_workflows: diskData.results ? diskData.results.length : 0,
                        total_workflows: diskData.total_workflows || '?',
                        results: diskData.results || [],
                        successful: diskData.results ? diskData.results.length : 0,
                    };
                }
            }

            if (!st) return;
            
            const statusEl = document.getElementById(`b-status-${localId}`);
            const statsEl = document.getElementById(`b-stats-${localId}`);
            
            if(statusEl) {
                if(st.status === 'cancelled') {
                    statusEl.textContent = 'Cancelado';
                    statusEl.className = 'indicator status-error';
                } else {
                    statusEl.textContent = st.status === 'processing' ? 'Procesando' : st.status;
                    
                    if(useFallback && st.status === 'processing') {
                         statusEl.textContent = 'Interrumpido'; 
                         statusEl.className = 'indicator status-error';
                         clearInterval(interval);
                    } else {
                        statusEl.className = `indicator status-${st.status === 'completed' ? 'idle' : 'processing'}`;
                        if(st.status === 'completed') statusEl.className = 'indicator health-ok';
                    }
                }
            }

            if(statsEl) {
                const total = st.total_workflows || '?';
                const done = st.completed_workflows || 0;
                const remain = (total !== '?') ? total - done : '?';
                statsEl.textContent = `✅ ${done} | ⏳ Faltan: ${remain}`;
            }
            
            if(st.results && st.results.length > lastLen) {
                appendImages(localId, st.results.slice(lastLen));
                lastLen = st.results.length;
            }
            
            if(st.status === 'completed' || st.status === 'error' || st.status === 'cancelled') {
                clearInterval(interval);
                if(st.status === 'completed') showStatus(`✅ Lote #${localId} finalizado`, 'success');
                if(st.status === 'cancelled') {
                    // Limpieza visual extra por si acaso
                    const imgContainer = document.getElementById(`b-imgs-${localId}`);
                    if(imgContainer && imgContainer.children.length > 0) {
                        imgContainer.innerHTML = '<div style="color:#999; font-style:italic; padding:10px;">🗑️ Limpieza automática completada.</div>';
                    }
                }
            }

        } catch(e) { console.error(e); }
    }, 2000);
}

function appendImages(localId, results) {
    const container = document.getElementById(`b-imgs-${localId}`);
    if(!container) return;

    results.forEach(r => {
        const imgs = r.generated_images || [r]; 
        
        imgs.forEach(img => {
            if (!img.url && !img.session_url) return;  

            const div = document.createElement('div');
            div.className = 'workflow-result-item';
            
            let url = img.url || img.session_url;
            if (url && !url.startsWith('http') && !url.startsWith('/')) url = `/${url}`;
            const fullUrl = url.startsWith('http') ? url : `${state.API_BASE_URL}${url}`;
            
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
    const serverId = job.batch_tracking_id || job.id;
    
    createBatchContainer(localId, serverId, "Restaurado");
    
    if (job.results && Array.isArray(job.results)) {
         appendImages(localId, job.results);
    }
    
    startBatchPoll(localId, serverId, job.id);
}

// Función Global para el botón de cancelar en el HTML
window.cancelBatch = async function(serverId, localId) {
    if(!confirm('⚠️ ¿Seguro? Se detendrá el proceso y se BORRARÁN las imágenes generadas.')) return;
    
    try {
        const res = await fetch(`/cancel-batch/${serverId}`, { method: 'POST' });
        const data = await res.json();
        
        if(data.success) {
            const st = document.getElementById(`b-status-${localId}`);
            if(st) {
                st.textContent = "Cancelado y Limpiado";
                st.className = "indicator status-error";
            }
            
            const imgContainer = document.getElementById(`b-imgs-${localId}`);
            if(imgContainer) {
                imgContainer.innerHTML = '<div style="color:#999; font-style:italic; padding:10px;">🗑️ Imágenes eliminadas del disco.</div>';
            }

            showStatus("🧹 Lote cancelado y archivos eliminados.", "success");
        } else {
            showStatus("❌ Error cancelando: " + data.error, "error");
        }
    } catch(e) { console.error(e); }
};