import { state, setSelectedFile } from './state.js';
import { showStatus } from './utils.js';
// import { saveState } from './session.js'; // Descomenta si usas persistencia de UI
// Asegúrate que la ruta coincida
import { loadWorkflowNodesForBatch, updateBatchWorkflowPreview } from './batch.js';

export async function loadWorkflows() {
    try {
        const response = await fetch(`${state.API_BASE_URL}/workflows`);
        const data = await response.json();
        state.availableWorkflows = data.workflows || [];
        state.workflowsStructure = data.structure || {};
        state.availableStyles = data.available_styles || [];

        populateSelectors();
        
        // AQUÍ LLAMAMOS A LA FUNCIÓN QUE DABA ERROR
        // Como ahora existe en batch.js, funcionará.
        if (state.availableWorkflows.length > 0) {
            loadWorkflowNodesForBatch(state.availableWorkflows[0].id);
        }
        
        showStatus(`✅ ${data.total} workflows cargados`, 'success');
    } catch (error) { 
        console.error(error);
        showStatus('❌ Error cargando workflows', 'error'); 
    }
}

function populateSelectors() {
    const roomSel = document.getElementById('roomTypeSelect');
    const batchRoom = document.getElementById('batchRoomTypes');
    const styleSels = [document.getElementById('styleSelect'), document.getElementById('batchStyleSelect')];
    
    if(roomSel) roomSel.innerHTML = '<option value="">Selecciona...</option>';
    if(batchRoom) batchRoom.innerHTML = '';
    
    Object.keys(state.workflowsStructure).forEach(type => {
        if(roomSel) roomSel.add(new Option(`🏠 ${type}`, type));
        if(batchRoom) batchRoom.add(new Option(`🏠 ${type}`, type));
    });

    styleSels.forEach(sel => {
        if (sel) {
            sel.innerHTML = '';
            state.availableStyles.forEach(s => sel.add(new Option(s.name, s.id)));
        }
    });
    
    const batchOrient = document.getElementById('batchOrientations');
    if(batchOrient) {
        const orients = new Set();
        Object.values(state.workflowsStructure).forEach(r => Object.keys(r).forEach(o => orients.add(o)));
        batchOrient.innerHTML = '';
        orients.forEach(o => batchOrient.add(new Option(`📐 ${o}`, o)));
    }
}

export function handleRoomTypeChange() {
    const type = document.getElementById('roomTypeSelect').value;
    const orientSel = document.getElementById('orientationSelect');
    const wfSel = document.getElementById('workflowSelect');
    
    if(!orientSel || !wfSel) return;

    orientSel.innerHTML = '<option value="">Selecciona...</option>';
    wfSel.innerHTML = '<option value="">...</option>';
    wfSel.disabled = true;

    if (type && state.workflowsStructure[type]) {
        orientSel.disabled = false;
        Object.keys(state.workflowsStructure[type]).forEach(o => orientSel.add(new Option(`📐 ${o}`, o)));
    } else { orientSel.disabled = true; }
}

export function handleOrientationChange() {
    const type = document.getElementById('roomTypeSelect').value;
    const orient = document.getElementById('orientationSelect').value;
    const wfSel = document.getElementById('workflowSelect');
    
    if(!wfSel) return;

    wfSel.innerHTML = '<option value="">Selecciona workflow...</option>';
    if (type && orient && state.workflowsStructure[type][orient]) {
        wfSel.disabled = false;
        state.workflowsStructure[type][orient].forEach(wf => wfSel.add(new Option(`🎯 ${wf.name}`, wf.id)));
    } else { wfSel.disabled = true; }
}

export function handleFileSelect(file) {
    if (!file.type.startsWith('image/')) return showStatus('❌ Solo imágenes', 'error');
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = document.getElementById('previewImage');
        const section = document.getElementById('previewSection');
        if(img && section) {
            img.src = e.target.result;
            section.style.display = 'block';
        }
    };
    reader.readAsDataURL(file);
    
    const btn1 = document.getElementById('processBtn');
    const btn2 = document.getElementById('processBatchBtn');
    if(btn1) btn1.disabled = false;
    if(btn2) btn2.disabled = false;
}

export function switchMode(mode) {
    document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
    
    const indPanel = document.getElementById('individualControls');
    const batchPanel = document.getElementById('batchControls');
    const indRes = document.getElementById('individualJobsSection');
    const batchRes = document.getElementById('batchResultsSection');

    if (mode === 'individual') {
        if(indPanel) indPanel.classList.add('active');
        if(indRes) indRes.style.display = 'block';
        if(batchRes) batchRes.style.display = 'none';
    }
    if (mode === 'batch') {
        if(batchPanel) batchPanel.classList.add('active');
        if(indRes) indRes.style.display = 'none';
        if(batchRes) batchRes.style.display = 'block';
    }
}