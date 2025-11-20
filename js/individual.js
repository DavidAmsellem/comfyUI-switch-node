import { state } from './state.js';
import { showStatus, showImageModal } from './utils.js';

export async function processImage() {
    if (!state.selectedFile) return showStatus('❌ Sin imagen', 'error');
    const wfId = document.getElementById('workflowSelect').value;
    if (!wfId) return showStatus('❌ Sin workflow', 'error');

    state.individualJobCounter++;
    const localId = `indiv_${state.individualJobCounter}`;
    
    // Crear tarjeta simple en la UI
    const div = document.createElement('div');
    div.className = 'individual-job-result processing';
    div.id = `job-${localId}`;
    div.innerHTML = `
        <div class="individual-job-header">🎯 Trabajo #${state.individualJobCounter}</div>
        <div>Estado: <strong id="status-${localId}">Enviando...</strong></div>
        <div id="imgs-${localId}" class="individual-job-images"></div>
    `;
    document.getElementById('individualResults').prepend(div);
    document.getElementById('individualJobsSection').style.display = 'block';

    try {
        const formData = new FormData();
        formData.append('image', state.selectedFile);
        formData.append('workflow', wfId);
        formData.append('frame_color', document.querySelector('input[name="frameColor"]:checked')?.value || 'black');
        formData.append('style', document.getElementById('styleSelect').value);
        formData.append('include_upscale', document.getElementById('includeUpscale').checked);
        
        // Añadir nodo de estilo si existe
        const styleNodeVal = document.getElementById('styleNodeSelect')?.value;
        if(styleNodeVal) formData.append('style_node', styleNodeVal);

        const res = await fetch(`${state.API_BASE_URL}/process-image`, { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            document.getElementById(`status-${localId}`).textContent = "Procesando en segundo plano...";
            // Iniciar polling simple
            startSimplePolling(localId, data.job_id);
        } else throw new Error(data.error);
    } catch (e) {
        document.getElementById(`status-${localId}`).textContent = "Error al enviar";
        showStatus(`❌ Error: ${e.message}`, 'error');
    }
}

function startSimplePolling(localId, serverId) {
    // Consultar cada 2 segundos
    const interval = setInterval(async () => {
        try {
            // Usar timestamp para evitar caché del navegador
            const t = new Date().getTime();
            const res = await fetch(`${state.API_BASE_URL}/session/jobs/${serverId}?t=${t}`);
            
            if(res.ok) {
                const job = await res.json();
                const el = document.getElementById(`status-${localId}`);
                const box = document.getElementById(`job-${localId}`);
                
                if (job.status === 'processing') {
                    el.textContent = "Procesando... (Espere)";
                } 
                else if (job.status === 'completed') {
                    el.textContent = "✅ Completado";
                    box.className = 'individual-job-result completed';
                    
                    // Mostrar imágenes
                    if(job.results && job.results.length) {
                        const c = document.getElementById(`imgs-${localId}`);
                        c.innerHTML = '';
                        job.results.forEach(img => {
                            const i = document.createElement('img');
                            const url = img.session_url || img.url;
                            // Asegurar URL absoluta
                            i.src = url.startsWith('http') ? url : `${state.API_BASE_URL}${url}`;
                            i.onclick = () => showImageModal(i.src);
                            c.appendChild(i);
                        });
                    }
                    clearInterval(interval); // Detener polling
                    showStatus('🎉 Imagen generada correctamente', 'success');
                } 
                else if (job.status === 'error') {
                    el.textContent = `❌ Error: ${job.error || 'Desconocido'}`;
                    box.className = 'individual-job-result error';
                    clearInterval(interval);
                }
            }
        } catch(e) { console.error("Error polling:", e); }
    }, 2000);
    
    // Guardar intervalo para poder limpiarlo si se limpia la sesión
    state.individualPollingIntervals.set(localId, interval);
}

export function restoreIndividualJob(job) {
    // Función simple para restaurar visualmente
    state.individualJobCounter++;
    const localId = `restored_${job.id}`;
    const div = document.createElement('div');
    div.className = `individual-job-result ${job.status}`;
    div.id = `job-${localId}`;
    div.innerHTML = `
        <div class="individual-job-header">🎯 Trabajo Restaurado</div>
        <div>Estado: <strong id="status-${localId}">${job.status}</strong></div>
        <div id="imgs-${localId}" class="individual-job-images"></div>
    `;
    document.getElementById('individualResults').appendChild(div);
    
    if(job.results && job.results.length) {
        const c = document.getElementById(`imgs-${localId}`);
        job.results.forEach(img => {
            const i = document.createElement('img');
            const url = img.session_url || img.url;
            i.src = url.startsWith('http') ? url : `${state.API_BASE_URL}${url}`;
            i.onclick = () => showImageModal(i.src);
            c.appendChild(i);
        });
    }
}