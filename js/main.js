import { checkHealth, setupImageZoomModal, startSystemMonitoring } from './utils.js';
import { loadWorkflows, handleRoomTypeChange, handleOrientationChange, handleFileSelect, switchMode } from './ui.js';
import { processImage } from './individual.js';
import { processBatch, updateBatchWorkflowPreview } from './batch.js';
import { loadSessionJobs, saveState, restoreState, clearState, cleanupOldJobs, clearSession } from './session.js';

window.onload = async function() {
    await checkHealth();
    startSystemMonitoring();
    await loadWorkflows();
    setupEventListeners();
    setupImageZoomModal();
    restoreState();
    setTimeout(loadSessionJobs, 1000);
    cleanupOldJobs();
};

function setupEventListeners() {
    document.getElementById('uploadArea').onclick = () => document.getElementById('fileInput').click();
    document.getElementById('fileInput').onchange = (e) => { if(e.target.files.length) handleFileSelect(e.target.files[0]); };
    
    document.getElementById('processMode').onchange = (e) => switchMode(e.target.value);
    
    document.getElementById('roomTypeSelect').onchange = () => { handleRoomTypeChange(); saveState(); };
    document.getElementById('orientationSelect').onchange = () => { handleOrientationChange(); saveState(); };
    document.getElementById('workflowSelect').onchange = saveState;
    document.getElementById('styleSelect').onchange = saveState;

    document.getElementById('processBtn').onclick = processImage;
    document.getElementById('processBatchBtn').onclick = processBatch;
    
    document.getElementById('batchRoomTypes').onchange = () => { updateBatchWorkflowPreview(); saveState(); };
    document.getElementById('batchOrientations').onchange = () => { updateBatchWorkflowPreview(); saveState(); };

    // Botones de Gestión
    document.getElementById('clearStateBtn').onclick = clearState;
    document.getElementById('clearSessionBtn').onclick = clearSession;
}