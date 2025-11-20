import { state, setSelectedFile } from './state.js';
import { showStatus } from './utils.js';
import { saveState } from './session.js';
import { loadWorkflowNodesForBatch, updateBatchWorkflowPreview } from './batch.js';

export async function loadWorkflows() {
    try {
        const response = await fetch(`${state.API_BASE_URL}/workflows`);
        const data = await response.json();
        state.availableWorkflows = data.workflows || [];
        state.workflowsStructure = data.structure || {};
        state.availableStyles = data.available_styles || [];

        populateSelectors();
        if (state.availableWorkflows.length > 0) loadWorkflowNodesForBatch(state.availableWorkflows[0].id);
        showStatus(`✅ ${data.total} workflows cargados`, 'success');
    } catch (error) { showStatus('❌ Error cargando workflows', 'error'); }
}

function populateSelectors() {
    const roomSel = document.getElementById('roomTypeSelect');
    const batchRoom = document.getElementById('batchRoomTypes');
    const styleSels = [document.getElementById('styleSelect'), document.getElementById('batchStyleSelect')];
    
    roomSel.innerHTML = '<option value="">Selecciona...</option>';
    if(batchRoom) batchRoom.innerHTML = '';
    
    Object.keys(state.workflowsStructure).forEach(type => {
        roomSel.add(new Option(`🏠 ${type}`, type));
        if(batchRoom) batchRoom.add(new Option(`🏠 ${type}`, type));
    });

    styleSels.forEach(sel => {
        sel.innerHTML = '';
        state.availableStyles.forEach(s => sel.add(new Option(s.name, s.id)));
    });
    
    // Batch Orientations
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
        document.getElementById('previewImage').src = e.target.result;
        document.getElementById('previewSection').style.display = 'block';
    };
    reader.readAsDataURL(file);
    document.getElementById('processBtn').disabled = false;
    document.getElementById('processBatchBtn').disabled = false;
}

export function switchMode(mode) {
    document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
    if (mode === 'individual') document.getElementById('individualControls').classList.add('active');
    if (mode === 'batch') document.getElementById('batchControls').classList.add('active');
}