// js/main.js
import { checkHealth, setupImageZoomModal, startSystemMonitoring } from './utils.js';
import { loadWorkflows, handleRoomTypeChange, handleOrientationChange, handleFileSelect, switchMode } from './ui.js';
import { processImage } from './individual.js';
import { processBatch, updateBatchWorkflowPreview } from './batch.js';
import { loadSessionJobs, saveState, restoreState, clearState, cleanupOldJobs } from './session.js';

window.onload = async function() {
    console.log('🚀 Iniciando Cliente Modular ComfyUI...');
    
    await checkHealth();
    startSystemMonitoring(); // Nuevo monitor de estado
    await loadWorkflows();
    
    setupEventListeners();
    setupImageZoomModal();
    
    // Restauración
    restoreState();
    setTimeout(loadSessionJobs, 1000);
    cleanupOldJobs();
};

function setupEventListeners() {
    // Drag & Drop
    const dropArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    dropArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if(e.target.files.length) handleFileSelect(e.target.files[0]);
    });
    // (Agregar eventos dragover/drop aquí...)

    // Modos
    document.getElementById('processMode').addEventListener('change', (e) => switchMode(e.target.value));
    
    // Selectores Individuales
    document.getElementById('roomTypeSelect').addEventListener('change', () => { handleRoomTypeChange(); saveState(); });
    document.getElementById('orientationSelect').addEventListener('change', () => { handleOrientationChange(); saveState(); });
    document.getElementById('workflowSelect').addEventListener('change', saveState);
    document.getElementById('styleSelect').addEventListener('change', saveState);
    
    // Botones
    document.getElementById('processBtn').addEventListener('click', processImage);
    document.getElementById('processBatchBtn').addEventListener('click', processBatch);
    
    // Batch Listeners
    document.getElementById('batchRoomTypes').addEventListener('change', () => { updateBatchWorkflowPreview(); saveState(); });
    document.getElementById('batchOrientations').addEventListener('change', () => { updateBatchWorkflowPreview(); saveState(); });

    // Debug & Limpieza
    document.getElementById('clearStateBtn')?.addEventListener('click', clearState);
}