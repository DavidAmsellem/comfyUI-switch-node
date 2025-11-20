import { state } from './state.js';
import { showStatus, showImageModal } from './utils.js';

export async function processImage() {
    if (!state.selectedFile) return showStatus('❌ Selecciona una imagen primero', 'status-error');

    const workflow = document.getElementById('workflowSelect').value;
    if (!workflow) return showStatus('⚠️ Selecciona un workflow específico', 'status-error');

    // UI Updates
    const btn = document.getElementById('processBtn');
    btn.disabled = true;
    
    state.individualJobCounter++;
    const localId = state.individualJobCounter;

    // Crear tarjeta visual
    createIndividualContainer(localId);

    try {
        const formData = new FormData();
        formData.append('image', state.selectedFile);
        formData.append('workflow', workflow);
        formData.append('style', document.getElementById('styleSelect').value);
        formData.append('frame_color', document.querySelector('input[name="frameColor"]:checked').value);
        formData.append('include_upscale', document.getElementById('includeUpscale').checked);
        
        // Opcional: Style Node
        const sn = document.getElementById('styleNodeSelect').value;
        if(sn) formData.append('style_node', sn);

        const res = await fetch(`${state.API_BASE_URL}/process-image`, { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            updateIndividualStatus(localId, 'processing', 'Procesando en servidor...');
            startIndividualPoll(localId, data.job_id);
        } else {
            throw new Error(data.error);
        }

    } catch (error) {
        updateIndividualStatus(localId, 'error', error.message);
        btn.disabled = false;
    }
}

function createIndividualContainer(id) {
    const container = document.getElementById('individualResults');
    const div = document.createElement('div');
    div.className = 'individual-job-result processing'; // Clase CSS
    div.id = `job-card-${id}`;
    div.innerHTML = `
        <div class="individual-job-header">
            <span>Trabajo #${id}</span>
            <span class="indicator status-processing" id="job-status-badge-${id}">Iniciando</span>
        </div>
        <div class="job-status-text" id="job-text-${id}">Subiendo...</div>
        <div class="individual-job-images" id="job-imgs-${id}"></div>
    `;
    container.prepend(div);
    // Asegurar que la sección es visible
    document.getElementById('individualJobsSection').style.display = 'block';
}

function updateIndividualStatus(id, status, text) {
    const badge = document.getElementById(`job-status-badge-${id}`);
    const txt = document.getElementById(`job-text-${id}`);
    const card = document.getElementById(`job-card-${id}`);

    if(badge) {
        if(status === 'completed') {
            badge.className = 'indicator health-ok';
            badge.textContent = 'Completado';
            if(card) card.className = 'individual-job-result completed';
        } else if (status === 'error') {
            badge.className = 'indicator status-error';
            badge.textContent = 'Error';
            if(card) card.className = 'individual-job-result error';
        } else {
            badge.className = 'indicator status-processing';
        }
    }
    if(txt) txt.textContent = text;
}

function startIndividualPoll(localId, jobId) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${state.API_BASE_URL}/session/jobs/${jobId}`);
            if(!res.ok) return;
            const job = await res.json();

            if (job.status === 'completed') {
                clearInterval(interval);
                updateIndividualStatus(localId, 'completed', 'Generación finalizada');
                document.getElementById('processBtn').disabled = false;
                
                // Renderizar imágenes
                const imgContainer = document.getElementById(`job-imgs-${localId}`);
                if(job.results && job.results.length) {
                    job.results.forEach(img => {
                        const el = document.createElement('img');
                        // Priorizar url sobre session_url
                        const imageUrl = img.url || img.session_url;
                        const url = imageUrl.startsWith('http') ? imageUrl : `${state.API_BASE_URL}${imageUrl}`;
                        el.src = url;
                        el.onclick = () => showImageModal(url);
                        imgContainer.appendChild(el);
                    });
                }
            } else if (job.status === 'error') {
                clearInterval(interval);
                updateIndividualStatus(localId, 'error', job.error || 'Error desconocido');
                document.getElementById('processBtn').disabled = false;
            }
        } catch (e) { console.error(e); }
    }, 2000);
}

export function restoreIndividualJob(job) {
    // Incrementar contador y crear container
    state.individualCounter++;
    const localId = state.individualCounter;
    
    createIndividualContainer(localId);
    
    // Determinar el estado del trabajo
    if (job.status === 'completed' && job.results && job.results.length > 0) {
        // Trabajo completado - mostrar resultados
        updateIndividualStatus(localId, 'completed', 'Generación completada (restaurado)');
        
        // Mostrar imágenes
        const imgContainer = document.getElementById(`job-imgs-${localId}`);
        job.results.forEach(img => {
            const el = document.createElement('img');
            // Priorizar url sobre session_url
            const imageUrl = img.url || img.session_url;
            const url = imageUrl.startsWith('http') ? imageUrl : `${state.API_BASE_URL}${imageUrl}`;
            el.src = url;
            el.onclick = () => showImageModal(url);
            imgContainer.appendChild(el);
        });
    } else if (job.status === 'error') {
        // Trabajo con error
        updateIndividualStatus(localId, 'error', job.error || 'Error en trabajo anterior');
    } else {
        // Trabajo en progreso - reiniciar polling
        updateIndividualStatus(localId, 'processing', 'Restaurando trabajo en progreso...');
        startIndividualPoll(localId, job.id);
    }
}