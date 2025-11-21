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

    console.log(`🚀 [INDIVIDUAL] Iniciando trabajo individual #${localId}`);
    console.log(`📊 [INDIVIDUAL] Estado actual - JobCounter: ${state.individualJobCounter}, Trabajos activos: ${state.activeIndividualJobs.size}`);

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
            console.log(`✅ [INDIVIDUAL #${localId}] Trabajo creado en servidor - JobID: ${data.job_id}`);
            
            // Registrar trabajo activo
            state.activeIndividualJobs.set(localId, {
                jobId: data.job_id,
                localId: localId,
                startTime: Date.now()
            });
            
            updateIndividualStatus(localId, 'processing', 'Procesando en servidor...');
            startIndividualPoll(localId, data.job_id);
        } else {
            console.error(`❌ [INDIVIDUAL #${localId}] Error del servidor:`, data.error);
            throw new Error(data.error);
        }

    } catch (error) {
        console.error(`❌ [INDIVIDUAL #${localId}] Error en processImage:`, error.message);
        updateIndividualStatus(localId, 'error', error.message);
        btn.disabled = false;
        
        // Limpiar trabajo fallido
        state.activeIndividualJobs.delete(localId);
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
    console.log(`🔄 [INDIVIDUAL #${localId}] Iniciando polling para JobID: ${jobId}`);
    
    // Limpiar polling anterior si existe
    if (state.individualPollingIntervals.has(localId)) {
        console.log(`🧹 [INDIVIDUAL #${localId}] Limpiando polling anterior`);
        clearInterval(state.individualPollingIntervals.get(localId));
    }
    
    // Contador para tracking incremental (como batch)
    let lastResultsCount = 0;
    
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${state.API_BASE_URL}/session/jobs/${jobId}`);
            if(!res.ok) {
                console.warn(`⚠️ [INDIVIDUAL #${localId}] Response not ok: ${res.status}`);
                return;
            }
            const job = await res.json();
            
            console.log(`📋 [INDIVIDUAL #${localId}] Status: ${job.status}, Results: ${job.results?.length || 0}`);

            // ⭐ MOSTRAR IMÁGENES INCREMENTALMENTE (igual que batch)
            if (job.results && job.results.length > lastResultsCount) {
                console.log(`�️ [INDIVIDUAL #${localId}] Nuevas imágenes: ${job.results.length - lastResultsCount}`);
                
                const imgContainer = document.getElementById(`job-imgs-${localId}`);
                if (imgContainer) {
                    // Mostrar solo las imágenes nuevas
                    const newResults = job.results.slice(lastResultsCount);
                    newResults.forEach((img, index) => {
                        const globalIndex = lastResultsCount + index + 1;
                        console.log(`🖼️ [INDIVIDUAL #${localId}] Imagen ${globalIndex}:`, img.filename);
                        
                        const el = document.createElement('img');
                        const imageUrl = img.url || img.session_url;
                        const url = imageUrl.startsWith('http') ? imageUrl : `${state.API_BASE_URL}${imageUrl}`;
                        
                        el.src = url;
                        el.onclick = () => showImageModal(url);
                        imgContainer.appendChild(el);
                    });
                    
                    lastResultsCount = job.results.length;
                    
                    // Actualizar estado visual con progreso
                    updateIndividualStatus(localId, 'processing', `Generando... (${job.results.length} imágenes)`);
                }
            }

            if (job.status === 'completed') {
                console.log(`🎉 [INDIVIDUAL #${localId}] Trabajo completado!`);
                
                clearInterval(interval);
                state.individualPollingIntervals.delete(localId);
                state.activeIndividualJobs.delete(localId);
                
                updateIndividualStatus(localId, 'completed', `Completado (${job.results?.length || 0} imágenes)`);
                
                // Solo reactivar botón si no hay más trabajos activos
                if (state.activeIndividualJobs.size === 0) {
                    console.log(`✅ [INDIVIDUAL] Todos completados, reactivando botón`);
                    document.getElementById('processBtn').disabled = false;
                }
                
            } else if (job.status === 'error') {
                console.error(`❌ [INDIVIDUAL #${localId}] Error:`, job.error);
                
                clearInterval(interval);
                state.individualPollingIntervals.delete(localId);
                state.activeIndividualJobs.delete(localId);
                
                updateIndividualStatus(localId, 'error', job.error || 'Error desconocido');
                
                if (state.activeIndividualJobs.size === 0) {
                    document.getElementById('processBtn').disabled = false;
                }
            }
        } catch (e) { 
            console.error(`💥 [INDIVIDUAL #${localId}] Error en polling:`, e); 
        }
    }, 2000);
    
    // Registrar el interval
    state.individualPollingIntervals.set(localId, interval);
    console.log(`📝 [INDIVIDUAL #${localId}] Polling registrado`);
}

export function restoreIndividualJob(job) {
    state.individualJobCounter++;
    const localId = state.individualJobCounter;
    
    console.log(`🔄 [RESTORE] Restaurando trabajo individual #${localId} - JobID: ${job.id}`);
    createIndividualContainer(localId);
    
    if (job.status === 'completed' && job.results && job.results.length > 0) {
        console.log(`✅ [RESTORE #${localId}] Trabajo completado - mostrando ${job.results.length} imágenes`);
        
        updateIndividualStatus(localId, 'completed', `Completado (${job.results.length} imágenes)`);
        
        // Mostrar todas las imágenes
        const imgContainer = document.getElementById(`job-imgs-${localId}`);
        if (imgContainer) {
            job.results.forEach((img, index) => {
                const el = document.createElement('img');
                const imageUrl = img.url || img.session_url;
                const url = imageUrl.startsWith('http') ? imageUrl : `${state.API_BASE_URL}${imageUrl}`;
                
                el.src = url;
                el.onclick = () => showImageModal(url);
                imgContainer.appendChild(el);
            });
        }
        
    } else if (job.status === 'error') {
        console.log(`❌ [RESTORE #${localId}] Trabajo con error: ${job.error}`);
        updateIndividualStatus(localId, 'error', job.error || 'Error en trabajo anterior');
        
    } else {
        console.log(`⏳ [RESTORE #${localId}] Trabajo en progreso - reiniciando polling`);
        
        const existingCount = job.results ? job.results.length : 0;
        updateIndividualStatus(localId, 'processing', `Restaurando... (${existingCount} imágenes)`);
        
        // Mostrar imágenes ya existentes
        if (existingCount > 0) {
            const imgContainer = document.getElementById(`job-imgs-${localId}`);
            if (imgContainer) {
                job.results.forEach((img) => {
                    const el = document.createElement('img');
                    const imageUrl = img.url || img.session_url;
                    const url = imageUrl.startsWith('http') ? imageUrl : `${state.API_BASE_URL}${imageUrl}`;
                    
                    el.src = url;
                    el.onclick = () => showImageModal(url);
                    imgContainer.appendChild(el);
                });
            }
        }
        
        // Registrar como trabajo activo y continuar polling
        state.activeIndividualJobs.set(localId, {
            jobId: job.id,
            localId: localId,
            startTime: Date.now(),
            restored: true
        });
        
        startIndividualPoll(localId, job.id);
    }
}