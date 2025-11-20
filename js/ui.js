// js/ui.js
import { state, setSelectedFile } from './state.js';
import { showStatus } from './utils.js';
import { saveState } from './session.js';
import { loadWorkflowNodesForBatch, updateBatchWorkflowPreview } from './batch.js';

export async function loadWorkflows() {
    try {
        showStatus('🔄 Cargando workflows...', 'info');
        const response = await fetch(`${state.API_BASE_URL}/workflows`);
        const data = await response.json();

        state.availableWorkflows = data.workflows || [];
        state.workflowsStructure = data.structure || {};
        state.availableStyles = data.available_styles || [];

        populateSelectors();
        
        // Cargar nodos para batch (basado en el primero)
        if (state.availableWorkflows.length > 0) {
            loadWorkflowNodesForBatch(state.availableWorkflows[0].id);
        }
        
        showStatus(`✅ ${data.total} workflows cargados`, 'success');
    } catch (error) {
        showStatus('❌ Error cargando workflows', 'error');
    }
}

function populateSelectors() {
    populateRoomTypes();
    populateStyles();
    populateBatchSelectors();
}

function populateStyles() {
    const selects = [document.getElementById('styleSelect'), document.getElementById('batchStyleSelect')];
    selects.forEach(sel => {
        if(!sel) return;
        sel.innerHTML = ''; 
        state.availableStyles.forEach(style => {
            const opt = document.createElement('option');
            opt.value = style.id;
            opt.textContent = style.name;
            opt.dataset.description = style.description;
            sel.appendChild(opt);
        });
    });
}

function populateRoomTypes() {
    const sel = document.getElementById('roomTypeSelect');
    if(!sel) return;
    sel.innerHTML = '<option value="">Selecciona un tipo...</option>';
    Object.keys(state.workflowsStructure).forEach(type => {
        const opt = document.createElement('option');
        opt.value = type;
        opt.textContent = `🏠 ${type.charAt(0).toUpperCase() + type.slice(1)}`;
        sel.appendChild(opt);
    });
}

function populateBatchSelectors() {
    const batchRooms = document.getElementById('batchRoomTypes');
    const batchOrients = document.getElementById('batchOrientations');
    
    if(batchRooms) {
        batchRooms.innerHTML = '';
        Object.keys(state.workflowsStructure).forEach(type => {
            const opt = document.createElement('option');
            opt.value = type;
            opt.textContent = `🏠 ${type}`;
            batchRooms.appendChild(opt);
        });
    }
    
    if(batchOrients) {
        const allOrients = new Set();
        Object.values(state.workflowsStructure).forEach(room => {
            Object.keys(room).forEach(o => allOrients.add(o));
        });
        batchOrients.innerHTML = '';
        allOrients.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o;
            opt.textContent = `📐 ${o}`;
            batchOrients.appendChild(opt);
        });
    }
}

// --- Event Handlers para Selectores ---

export function handleRoomTypeChange() {
    const roomType = document.getElementById('roomTypeSelect').value;
    const orientSelect = document.getElementById('orientationSelect');
    const wfSelect = document.getElementById('workflowSelect');
    
    orientSelect.innerHTML = '<option value="">Selecciona...</option>';
    wfSelect.innerHTML = '<option value="">...</option>';
    wfSelect.disabled = true;

    if (roomType && state.workflowsStructure[roomType]) {
        orientSelect.disabled = false;
        Object.keys(state.workflowsStructure[roomType]).forEach(o => {
            const opt = document.createElement('option');
            opt.value = o;
            opt.textContent = `📐 ${o}`;
            orientSelect.appendChild(opt);
        });
    } else {
        orientSelect.disabled = true;
    }
}

export function handleOrientationChange() {
    const roomType = document.getElementById('roomTypeSelect').value;
    const orient = document.getElementById('orientationSelect').value;
    const wfSelect = document.getElementById('workflowSelect');

    wfSelect.innerHTML = '<option value="">Selecciona workflow...</option>';
    
    if (roomType && orient && state.workflowsStructure[roomType][orient]) {
        wfSelect.disabled = false;
        state.workflowsStructure[roomType][orient].forEach(wf => {
            const opt = document.createElement('option');
            opt.value = wf.id;
            opt.textContent = `🎯 ${wf.name}`;
            opt.dataset.workflow = JSON.stringify(wf);
            wfSelect.appendChild(opt);
        });
    } else {
        wfSelect.disabled = true;
    }
}

export function handleFileSelect(file) {
    if (!file.type.startsWith('image/')) {
        showStatus('❌ Solo imágenes', 'error');
        return;
    }
    setSelectedFile(file);
    
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = document.getElementById('previewImage');
        if(img) {
            img.src = e.target.result;
            document.getElementById('previewSection').style.display = 'block';
        }
    };
    reader.readAsDataURL(file);
    
    // Actualizar botones
    const btnBatch = document.getElementById('processBatchBtn');
    const btnIndiv = document.getElementById('processBtn');
    if(btnBatch) btnBatch.disabled = false;
    if(btnIndiv) btnIndiv.disabled = false;
}

export function switchMode(mode) {
    document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
    if (mode === 'individual') document.getElementById('individualControls')?.classList.add('active');
    if (mode === 'batch') document.getElementById('batchControls')?.classList.add('active');
}