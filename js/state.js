// js/state.js
export const state = {
    API_BASE_URL: window.location.origin,
    selectedFile: null,
    availableWorkflows: [],
    workflowsStructure: {},
    availableStyles: [],
    currentWorkflowNodes: [],
    
    // Tracking
    activeIndividualJobs: new Map(),
    individualJobCounter: 0,
    individualPollingIntervals: new Map(),
    
    activeBatches: 0,
    batchCounter: 0,
    pollingIntervals: new Map(),
    restoredBatchJobs: new Set()
};

// Setter para selectedFile para usarlo desde otros módulos
export function setSelectedFile(file) {
    state.selectedFile = file;
}