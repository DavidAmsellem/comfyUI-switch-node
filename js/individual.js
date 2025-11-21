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
    
    const interval = setInterval(async () => {
        try {
            console.log(`🔍 [INDIVIDUAL #${localId}] Consultando estado del JobID: ${jobId}`);
            
            const res = await fetch(`${state.API_BASE_URL}/session/jobs/${jobId}`);
            if(!res.ok) {
                console.warn(`⚠️ [INDIVIDUAL #${localId}] Response not ok: ${res.status}`);
                return;
            }
            const job = await res.json();
            
            console.log(`📋 [INDIVIDUAL #${localId}] Estado recibido:`, job.status, `- Results:`, job.results?.length || 0);

            if (job.status === 'completed') {
                console.log(`🎉 [INDIVIDUAL #${localId}] Trabajo completado! Procesando resultados...`);
                
                clearInterval(interval);
                state.individualPollingIntervals.delete(localId);
                state.activeIndividualJobs.delete(localId);
                
                updateIndividualStatus(localId, 'completed', 'Generación finalizada');
                
                // Solo reactivar botón si no hay más trabajos activos
                if (state.activeIndividualJobs.size === 0) {
                    console.log(`✅ [INDIVIDUAL] Todos los trabajos completados, reactivando botón`);
                    document.getElementById('processBtn').disabled = false;
                } else {
                    console.log(`⏳ [INDIVIDUAL] Aún quedan ${state.activeIndividualJobs.size} trabajos activos`);
                }
                
                // Renderizar imágenes
                const imgContainer = document.getElementById(`job-imgs-${localId}`);
                if(!imgContainer) {
                    console.error(`❌ [INDIVIDUAL #${localId}] No se encontró contenedor job-imgs-${localId}`);
                    return;
                }
                
                if(job.results && job.results.length) {
                    console.log(`🖼️ [INDIVIDUAL #${localId}] Renderizando ${job.results.length} imágenes`);
                    
                    job.results.forEach((img, index) => {
                        console.log(`🖼️ [INDIVIDUAL #${localId}] Imagen ${index + 1}:`, {
                            url: img.url, 
                            session_url: img.session_url,
                            filename: img.filename
                        });
                        
                        const el = document.createElement('img');
                        // Priorizar url sobre session_url
                        const imageUrl = img.url || img.session_url;
                        const url = imageUrl.startsWith('http') ? imageUrl : `${state.API_BASE_URL}${imageUrl}`;
                        
                        console.log(`🔗 [INDIVIDUAL #${localId}] URL final imagen ${index + 1}: ${url}`);
                        
                        el.src = url;
                        el.onclick = () => showImageModal(url);
                        imgContainer.appendChild(el);
                    });
                } else {
                    console.warn(`⚠️ [INDIVIDUAL #${localId}] No hay resultados para mostrar`);
                }
                
            } else if (job.status === 'error') {
                console.error(`❌ [INDIVIDUAL #${localId}] Trabajo falló:`, job.error);
                
                clearInterval(interval);
                state.individualPollingIntervals.delete(localId);
                state.activeIndividualJobs.delete(localId);
                
                updateIndividualStatus(localId, 'error', job.error || 'Error desconocido');
                
                // Solo reactivar botón si no hay más trabajos activos
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
    console.log(`📝 [INDIVIDUAL #${localId}] Polling registrado, intervals activos: ${state.individualPollingIntervals.size}`);
}

export function restoreIndividualJob(job) {
    // Incrementar contador y crear container
    state.individualJobCounter++;  // FIX: Usar el contador correcto, no individualCounter
    const localId = state.individualJobCounter;
    
    console.log(`🔄 [RESTORE] Restaurando trabajo individual #${localId} - JobID: ${job.id}`);
    console.log(`📋 [RESTORE] Estado del trabajo:`, job.status, `- Results:`, job.results?.length || 0);
    
    createIndividualContainer(localId);
    
    // Determinar el estado del trabajo
    if (job.status === 'completed' && job.results && job.results.length > 0) {
        console.log(`✅ [RESTORE #${localId}] Trabajo completado - mostrando resultados`);
        
        // Trabajo completado - mostrar resultados
        updateIndividualStatus(localId, 'completed', 'Generación completada (restaurado)');
        
        // Mostrar imágenes
        const imgContainer = document.getElementById(`job-imgs-${localId}`);
        if (!imgContainer) {
            console.error(`❌ [RESTORE #${localId}] No se encontró contenedor job-imgs-${localId}`);
            return;
        }
        
        job.results.forEach((img, index) => {
            console.log(`🖼️ [RESTORE #${localId}] Imagen ${index + 1}:`, {
                url: img.url, 
                session_url: img.session_url,
                filename: img.filename
            });
            
            const el = document.createElement('img');
            // Priorizar url sobre session_url
            const imageUrl = img.url || img.session_url;
            const url = imageUrl.startsWith('http') ? imageUrl : `${state.API_BASE_URL}${imageUrl}`;
            
            console.log(`🔗 [RESTORE #${localId}] URL final imagen ${index + 1}: ${url}`);
            
            el.src = url;
            el.onclick = () => showImageModal(url);
            imgContainer.appendChild(el);
        });
        
    } else if (job.status === 'error') {
        console.log(`❌ [RESTORE #${localId}] Trabajo con error: ${job.error}`);
        // Trabajo con error
        updateIndividualStatus(localId, 'error', job.error || 'Error en trabajo anterior');
        
    } else {
        console.log(`⏳ [RESTORE #${localId}] Trabajo en progreso - reiniciando polling`);
        // Trabajo en progreso - reiniciar polling
        updateIndividualStatus(localId, 'processing', 'Restaurando trabajo en progreso...');
        
        // Registrar como trabajo activo
        state.activeIndividualJobs.set(localId, {
            jobId: job.id,
            localId: localId,
            startTime: Date.now(),
            restored: true
        });
        
        startIndividualPoll(localId, job.id);
    }
}