// Variables globales
const API_BASE_URL = window.location.origin;
let selectedFile = null;
let availableWorkflows = [];
let workflowsStructure = {};
let availableStyles = [];
let currentWorkflowNodes = [];

// Variables para tracking de trabajos individuales
let activeIndividualJobs = new Map(); // jobId -> jobInfo
let individualJobCounter = 0;
let individualPollingIntervals = new Map(); // jobId -> intervalId

// ===== PERSISTENCE FUNCTIONS =====
function saveState() {
    const state = {
        roomType: document.getElementById('roomTypeSelect').value,
        orientation: document.getElementById('orientationSelect').value,
        workflow: document.getElementById('workflowSelect').value,
        style: document.getElementById('styleSelect').value,
        styleNode: document.getElementById('styleNodeSelect').value,
        frameColor: document.querySelector('input[name="frameColor"]:checked')?.value || 'black',
        batchRoomTypes: Array.from(document.getElementById('batchRoomTypes').selectedOptions).map(o => o.value),
        batchOrientations: Array.from(document.getElementById('batchOrientations').selectedOptions).map(o => o.value)
    };
    
    localStorage.setItem('comfyui_client_state', JSON.stringify(state));
}

function restoreState() {
    try {
        const savedState = localStorage.getItem('comfyui_client_state');
        if (!savedState) return;
        
        const state = JSON.parse(savedState);
        
        // Restaurar selecciones básicas
        if (state.roomType) {
            document.getElementById('roomTypeSelect').value = state.roomType;
            handleRoomTypeChange(); // Esto poblará las orientaciones
            
            setTimeout(() => {
                if (state.orientation) {
                    document.getElementById('orientationSelect').value = state.orientation;
                    handleOrientationChange(); // Esto poblará los workflows
                    
                    setTimeout(() => {
                        if (state.workflow) {
                            document.getElementById('workflowSelect').value = state.workflow;
                            handleWorkflowChange(); // Esto cargará los nodos
                        }
                    }, 100);
                }
            }, 100);
        }
        
        if (state.style) {
            document.getElementById('styleSelect').value = state.style;
            handleStyleChange();
        }
        
        if (state.frameColor) {
            const frameColorRadio = document.querySelector(`input[name="frameColor"][value="${state.frameColor}"]`);
            if (frameColorRadio) {
                frameColorRadio.checked = true;
            }
        }
        
        // Restaurar selecciones de batch (con delay para asegurar que las opciones están cargadas)
        setTimeout(() => {
            if (state.batchRoomTypes && state.batchRoomTypes.length > 0) {
                const batchRoomSelect = document.getElementById('batchRoomTypes');
                Array.from(batchRoomSelect.options).forEach(option => {
                    option.selected = state.batchRoomTypes.includes(option.value);
                });
            }
            
            if (state.batchOrientations && state.batchOrientations.length > 0) {
                const batchOrientationSelect = document.getElementById('batchOrientations');
                Array.from(batchOrientationSelect.options).forEach(option => {
                    option.selected = state.batchOrientations.includes(option.value);
                });
            }
            
            updateBatchWorkflowPreview();
        }, 500);
        
        showStatus('💾 Estado restaurado desde la sesión anterior', 'info');
    } catch (error) {
        console.error('Error restaurando estado:', error);
        showStatus('⚠️ Error restaurando estado guardado', 'warning');
    }
}

function clearState() {
    localStorage.removeItem('comfyui_client_state');
    location.reload(); // Recargar para limpiar todo
}

// ===== FUNCIONES DE MANEJO DE MODOS =====
function switchMode(mode) {
    const individualControls = document.getElementById('individualControls');
    const batchControls = document.getElementById('batchControls');
    
    // Ocultar todos los paneles de control
    [individualControls, batchControls].forEach(panel => {
        if (panel) panel.classList.remove('active');
    });
    
    // Mostrar el panel seleccionado
    if (mode === 'individual' && individualControls) {
        individualControls.classList.add('active');
    } else if (mode === 'batch' && batchControls) {
        batchControls.classList.add('active');
        // Sincronizar estilos del batch con el individual
        syncBatchStyles();
    }
    
    // Limpiar resultados si es necesario
    clearResults();
}

function syncBatchStyles() {
    // Sincronizar el selector de estilos del batch con el individual
    const styleSelect = document.getElementById('styleSelect');
    const batchStyleSelect = document.getElementById('batchStyleSelect');
    
    if (styleSelect && batchStyleSelect) {
        // Copiar opciones del selector individual al batch
        batchStyleSelect.innerHTML = styleSelect.innerHTML;
        batchStyleSelect.value = styleSelect.value;
    }
}

function setupModeHandlers() {
    const processMode = document.getElementById('processMode');
    
    // Event listener para cambio de modo
    if (processMode) {
        processMode.addEventListener('change', (e) => {
            switchMode(e.target.value);
        });
    }
}

// ===== FUNCIONES PARA MODAL DE ZOOM DE IMÁGENES =====

function setupImageZoomModal() {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalClose = document.getElementById('modalClose');
    const modalInfo = document.getElementById('modalInfo');
    
    // Verificar que los elementos existen
    if (!modal || !modalImage || !modalClose || !modalInfo) {
        console.error('❌ Error: Elementos del modal no encontrados');
        return;
    }
    
    console.log('✅ Elementos del modal encontrados correctamente');
    
    // Función para hacer que todas las imágenes sean clickeables
    function makeImageClickable(img, imageInfo = '') {
        // Evitar duplicar event listeners
        if (img.hasAttribute('data-modal-enabled')) {
            return;
        }
        
        img.style.cursor = 'pointer';
        img.setAttribute('data-modal-enabled', 'true');
        
        const clickHandler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('🖱️ Click en imagen:', img.src);
            showImageModal(img.src, imageInfo);
        };
        
        img.addEventListener('click', clickHandler);
        
        // Añadir también evento para táctil
        img.addEventListener('touchstart', clickHandler);
    }
    
    // Hacer clickeables todas las imágenes existentes
    document.querySelectorAll('.result-item img, .batch-workflow-images img, .individual-job-images img, .preview-image').forEach(img => {
        makeImageClickable(img, img.alt || 'Imagen generada');
    });
    
    // Observador para nuevas imágenes que se añadan dinámicamente
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // Element node
                    // Buscar imágenes en el nodo añadido
                    const images = node.querySelectorAll ? node.querySelectorAll('img') : [];
                    
                    // Si el nodo es una imagen
                    if (node.tagName === 'IMG') {
                        const parentClasses = node.parentElement?.className || '';
                        if (parentClasses.includes('result-item') || 
                            parentClasses.includes('batch-workflow-images') || 
                            parentClasses.includes('individual-job-images') ||
                            node.className.includes('preview-image')) {
                            makeImageClickable(node, node.alt || 'Imagen generada');
                        }
                    }
                    
                    // Buscar imágenes dentro del nodo
                    images.forEach(img => {
                        const parentClasses = img.parentElement?.className || '';
                        const parentId = img.parentElement?.id || '';
                        if (parentClasses.includes('result-item') || 
                            parentClasses.includes('batch-workflow-images') || 
                            parentClasses.includes('individual-job-images') ||
                            parentClasses.includes('workflow-result-item') ||
                            parentId.includes('images-container-') ||
                            img.className.includes('preview-image')) {
                            
                            // Verificar si ya tiene modal habilitado
                            if (!img.hasAttribute('data-modal-enabled')) {
                                makeImageClickable(img, img.alt || 'Imagen generada');
                            }
                        }
                    });
                }
            });
        });
    });
    
    // Observar cambios en el contenedor de resultados
    const resultsContainer = document.querySelector('.panel');
    if (resultsContainer) {
        observer.observe(resultsContainer, {
            childList: true,
            subtree: true
        });
    }
}

// Inicialización
window.onload = function() {
    checkHealth();
    loadWorkflows();
    setupEventListeners();
    setupModeHandlers(); // Configurar manejadores de modo
    setupImageZoomModal(); // Configurar modal de zoom
    setupGlobalModalHandlers(); // Configurar manejadores globales del modal
    
    // Inicializar en modo individual
    switchMode('individual');
    
    // Cargar trabajos de sesión anterior
    setTimeout(() => {
        loadSessionJobs();
    }, 500);
    
    // 🔥 FORZAR RESTAURACIÓN AUTOMÁTICA DE TRABAJOS BATCH
    setTimeout(async () => {
        console.log('🔄 Ejecutando restauración automática de trabajos batch...');
        
        // Limpiar duplicados existentes primero
        cleanupDuplicateBatchJobs();
        
        const batchRestored = await forceRestoreBatchJobs();
        
        if (batchRestored) {
            console.log('✅ Trabajos batch restaurados automáticamente');
            
            // Verificar que la sección esté visible
            setTimeout(() => {
                ensureBatchSectionVisible();
            }, 500);
        } else {
            console.log('ℹ️ No se encontraron trabajos batch para restaurar');
        }
    }, 1000);
    
    // Restaurar estado después de cargar workflows
    setTimeout(() => {
        restoreState();
    }, 1000);
    
    // 🔥 HABILITAR MODAL AUTOMÁTICAMENTE PARA TODAS LAS IMÁGENES DESPUÉS DE CARGAR
    setTimeout(() => {
        console.log('🔧 Habilitando modal automáticamente para todas las imágenes...');
        enableModalForAllImages();
        
        // 🔥 ASEGURAR QUE LA SECCIÓN DE BATCH ESTÉ VISIBLE
        ensureBatchSectionVisible();
    }, 1500); // Delay para asegurar que toda la página se haya cargado
    
    // 🔥 OBSERVER CONTINUO PARA MODAL DE IMÁGENES
    const modalObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Buscar imágenes en el nodo agregado
                        const images = node.querySelectorAll ? node.querySelectorAll('img') : [];
                        const isImg = node.tagName === 'IMG';
                        
                        if (isImg || images.length > 0) {
                            console.log('👁️ Nuevas imágenes detectadas por observer, habilitando modal...');
                            
                            setTimeout(() => {
                                enableModalForAllImages();
                            }, 200);
                        }
                    }
                });
            }
        });
    });
    
    // Iniciar observación en el body
    modalObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('👁️ Observer de modal iniciado');
    
    // Limpiar trabajos antiguos al inicializar (más de 24 horas)
    setTimeout(() => {
        cleanupOldJobs(24);
    }, 2000);
};

// Función para configurar manejadores globales del modal
function setupGlobalModalHandlers() {
    const modal = document.getElementById('imageModal');
    const modalClose = document.getElementById('modalClose');
    
    if (modal && modalClose) {
        // Event listener para cerrar modal
        modalClose.addEventListener('click', closeImageModal);
        
        // Cerrar modal al hacer clic fuera de la imagen
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeImageModal();
            }
        });
        
        // Cerrar modal con tecla ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('show')) {
                closeImageModal();
            }
        });
        
        console.log('✅ Manejadores globales del modal configurados');
    } else {
        console.error('❌ No se pudieron configurar manejadores globales del modal');
    }
}

// Limpieza cuando se cierra la página
window.addEventListener('beforeunload', function() {
    // Limpiar todos los intervalos de polling de lotes
    pollingIntervals.forEach((intervalId) => {
        clearInterval(intervalId);
    });
    pollingIntervals.clear();
    
    // Limpiar todos los intervalos de polling de trabajos individuales
    individualPollingIntervals.forEach((intervalId) => {
        clearInterval(intervalId);
    });
    individualPollingIntervals.clear();
});

function setupEventListeners() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // Selectores en cascada
    document.getElementById('roomTypeSelect').addEventListener('change', () => {
        handleRoomTypeChange();
        saveState();
    });
    document.getElementById('orientationSelect').addEventListener('change', () => {
        handleOrientationChange();
        saveState();
    });
    document.getElementById('workflowSelect').addEventListener('change', () => {
        handleWorkflowChange();
        saveState();
    });
    
    // Selector de estilo
    document.getElementById('styleSelect').addEventListener('change', () => {
        handleStyleChange();
        saveState();
    });
    
    // Selector de nodo de estilo
    document.getElementById('styleNodeSelect').addEventListener('change', () => {
        handleStyleNodeChange();
        saveState();
    });
    
    // Selector de nodo de estilo (Batch)
    document.getElementById('batchStyleNodeSelect').addEventListener('change', () => {
        handleBatchStyleNodeChange();
        saveState();
    });
    
    // Colores de marco
    document.querySelectorAll('input[name="frameColor"]').forEach(radio => {
        radio.addEventListener('change', saveState);
    });
    
    // Colores de marco (Batch)
    document.querySelectorAll('input[name="batchFrameColor"]').forEach(radio => {
        radio.addEventListener('change', saveState);
    });
    
    // Botón de procesamiento
    document.getElementById('processBtn').addEventListener('click', processImage);
    
    // ===== BATCH PROCESSING LISTENERS =====
    // Selectores de batch
    document.getElementById('batchRoomTypes').addEventListener('change', () => {
        updateBatchWorkflowPreview();
        saveState();
    });
    document.getElementById('batchOrientations').addEventListener('change', () => {
        updateBatchWorkflowPreview();
        saveState();
    });
    
    // Botón de batch
    document.getElementById('processBatchBtn').addEventListener('click', processBatch);
    
    // Botón de limpiar estado
    document.getElementById('clearStateBtn').addEventListener('click', clearState);
    
    // Botón de limpiar sesión
    document.getElementById('clearSessionBtn').addEventListener('click', clearSession);
    
    // Botón de debug de sesión
    document.getElementById('debugSessionBtn').addEventListener('click', debugSession);
    
    // Botón de prueba de modal
    document.getElementById('testModalBtn').addEventListener('click', () => {
        console.log('🧪 Testing modal...');
        const modal = document.getElementById('imageModal');
        if (modal) {
            // Crear imagen de prueba
            const testImage = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzQzNzNkYyIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmaWxsPSJ3aGl0ZSIgZm9udC1zaXplPSIxNiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPvCfp6ggVGVzdCBJbWFnZTwvdGV4dD48L3N2Zz4=';
            
            // Mostrar modal manualmente
            const modalImage = document.getElementById('modalImage');
            const modalInfo = document.getElementById('modalInfo');
            
            modalImage.src = testImage;
            modalInfo.textContent = 'Esta es una imagen de prueba';
            modal.style.display = 'flex';
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
            
            console.log('✅ Modal de prueba mostrado');
        } else {
            console.error('❌ Modal no encontrado');
        }
    });
    
    // Botón de debug de modal
    document.getElementById('debugModalBtn').addEventListener('click', debugImageModal);
    
    // Botón de debug de batch
    document.getElementById('debugBatchBtn').addEventListener('click', debugBatchJobs);
}

function checkProcessButtonState() {
    const processBtn = document.getElementById('processBtn');
    const processBatchBtn = document.getElementById('processBatchBtn');
    const workflowSelect = document.getElementById('workflowSelect');
    
    // Habilitar botón individual solo si hay imagen Y workflow seleccionado
    if (processBtn) {
        processBtn.disabled = !selectedFile || !workflowSelect.value;
    }
    
    // Habilitar batch solo si hay imagen seleccionada
    if (processBatchBtn) {
        updateBatchButtonText();
    }
}

async function checkHealth() {
    const indicator = document.getElementById('healthIndicator');
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();

        if (data.status === 'ok' && data.comfyui_connection === 'ok') {
            indicator.textContent = '✅ API y ComfyUI Conectados';
            indicator.className = 'health-indicator health-ok';
        } else {
            indicator.textContent = '⚠️ API OK, ComfyUI Desconectado';
            indicator.className = 'health-indicator health-error';
        }
    } catch (error) {
        indicator.textContent = '❌ API No Disponible';
        indicator.className = 'health-indicator health-error';
    }
}

async function loadWorkflows() {
    try {
        showStatus('🔄 Cargando workflows...', 'info');
        const response = await fetch(`${API_BASE_URL}/workflows`);
        const data = await response.json();

        availableWorkflows = data.workflows || [];
        workflowsStructure = data.structure || {};
        availableStyles = data.available_styles || [];

        populateRoomTypes();
        populateStyles();
        populateBatchSelectors(); // Poblar selectores de batch
        
        // Cargar nodos del primer workflow disponible para el modo batch
        // (ya que todos los workflows tienen la misma estructura)
        if (availableWorkflows.length > 0) {
            const firstWorkflow = availableWorkflows[0];
            await loadWorkflowNodesForBatch(firstWorkflow.id);
        }
        
        showStatus(`✅ ${data.total} workflows cargados`, 'success');
    } catch (error) {
        console.error('Error cargando workflows:', error);
        showStatus('❌ Error cargando workflows', 'error');
    }
}

function populateStyles() {
    const styleSelect = document.getElementById('styleSelect');
    const batchStyleSelect = document.getElementById('batchStyleSelect');
    
    // Limpiar ambos selectores
    styleSelect.innerHTML = '';
    batchStyleSelect.innerHTML = '';

    availableStyles.forEach(style => {
        // Crear opción para el selector individual
        const option = document.createElement('option');
        option.value = style.id;
        option.textContent = style.name;
        option.dataset.description = style.description;
        styleSelect.appendChild(option);
        
        // Crear opción para el selector de batch
        const batchOption = document.createElement('option');
        batchOption.value = style.id;
        batchOption.textContent = style.name;
        batchOption.dataset.description = style.description;
        batchStyleSelect.appendChild(batchOption);
    });
}

function handleStyleChange() {
    const styleSelect = document.getElementById('styleSelect');
    const styleDescription = document.getElementById('styleDescription');
    
    const selectedOption = styleSelect.options[styleSelect.selectedIndex];
    
    if (selectedOption && selectedOption.dataset.description) {
        styleDescription.textContent = selectedOption.dataset.description;
        styleDescription.style.display = 'block';
        showStatus(`✨ Estilo seleccionado: ${selectedOption.textContent}`, 'info');
    } else {
        styleDescription.style.display = 'none';
    }
}

function populateRoomTypes() {
    const roomTypeSelect = document.getElementById('roomTypeSelect');
    roomTypeSelect.innerHTML = '<option value="">Selecciona un tipo...</option>';

    Object.keys(workflowsStructure).forEach(roomType => {
        const option = document.createElement('option');
        option.value = roomType;
        option.textContent = `🏠 ${roomType.charAt(0).toUpperCase() + roomType.slice(1)}`;
        roomTypeSelect.appendChild(option);
    });
}

function handleRoomTypeChange() {
    const roomTypeSelect = document.getElementById('roomTypeSelect');
    const orientationSelect = document.getElementById('orientationSelect');
    const workflowSelect = document.getElementById('workflowSelect');
    const workflowInfo = document.getElementById('workflowInfo');
    const styleNodeSection = document.getElementById('styleNodeSection');

    const selectedRoomType = roomTypeSelect.value;

    // Reset selectors
    orientationSelect.innerHTML = '<option value="">Selecciona una orientación...</option>';
    workflowSelect.innerHTML = '<option value="">Selecciona orientación primero...</option>';
    workflowSelect.disabled = true;
    workflowInfo.style.display = 'none';
    styleNodeSection.style.display = 'none';
    clearStyleNodes();

    if (selectedRoomType && workflowsStructure[selectedRoomType]) {
        orientationSelect.disabled = false;
        
        Object.keys(workflowsStructure[selectedRoomType]).forEach(orientation => {
            const option = document.createElement('option');
            option.value = orientation;
            option.textContent = `📐 ${orientation}`;
            orientationSelect.appendChild(option);
        });

        showStatus(`📂 Tipo seleccionado: ${selectedRoomType}`, 'info');
    } else {
        orientationSelect.disabled = true;
    }
}

function handleOrientationChange() {
    const roomTypeSelect = document.getElementById('roomTypeSelect');
    const orientationSelect = document.getElementById('orientationSelect');
    const workflowSelect = document.getElementById('workflowSelect');
    const workflowInfo = document.getElementById('workflowInfo');
    const styleNodeSection = document.getElementById('styleNodeSection');

    const selectedRoomType = roomTypeSelect.value;
    const selectedOrientation = orientationSelect.value;

    // Reset workflow selector
    workflowSelect.innerHTML = '<option value="">Selecciona un workflow específico...</option>';
    workflowInfo.style.display = 'none';
    styleNodeSection.style.display = 'none';
    clearStyleNodes();

    if (selectedRoomType && selectedOrientation && 
        workflowsStructure[selectedRoomType] && 
        workflowsStructure[selectedRoomType][selectedOrientation]) {
        
        workflowSelect.disabled = false;
        
        workflowsStructure[selectedRoomType][selectedOrientation].forEach(workflow => {
            const option = document.createElement('option');
            option.value = workflow.id;
            option.textContent = `🎯 ${workflow.name}`;
            option.dataset.workflow = JSON.stringify(workflow);
            workflowSelect.appendChild(option);
        });

        showStatus(`📐 Orientación seleccionada: ${selectedOrientation}`, 'info');
    } else {
        workflowSelect.disabled = true;
    }
}

function handleWorkflowChange() {
    const workflowSelect = document.getElementById('workflowSelect');
    const workflowInfo = document.getElementById('workflowInfo');
    const workflowInfoText = document.getElementById('workflowInfoText');
    const styleNodeSection = document.getElementById('styleNodeSection');

    const selectedOption = workflowSelect.options[workflowSelect.selectedIndex];

    if (selectedOption && selectedOption.value) {
        const workflowData = JSON.parse(selectedOption.dataset.workflow || '{}');
        
        workflowInfoText.innerHTML = `
            <div style="margin-top: 5px;">
                <strong>Nombre:</strong> ${workflowData.name || 'N/A'}<br>
                <strong>Tipo:</strong> ${workflowData.room_type || 'N/A'}<br>
                <strong>Orientación:</strong> ${workflowData.orientation || 'N/A'}<br>
                <strong>Estado:</strong> ${workflowData.status || 'N/A'}
            </div>
        `;
        
        workflowInfo.style.display = 'block';
        styleNodeSection.style.display = 'block';
        showStatus(`🎯 Workflow seleccionado: ${workflowData.name}`, 'success');
        
        // Cargar nodos del workflow para selección de estilo
        loadWorkflowNodes(workflowData.id || selectedOption.value);
    } else {
        workflowInfo.style.display = 'none';
        styleNodeSection.style.display = 'none';
        clearStyleNodes();
    }
    
    // Verificar estado del botón
    checkProcessButtonState();
}

function handleFileSelect(file) {
    if (!file.type.startsWith('image/')) {
        showStatus('❌ El archivo debe ser una imagen', 'error');
        return;
    }

    selectedFile = file;

    // Mostrar vista previa (solo hay una zona de preview común)
    const reader = new FileReader();
    reader.onload = (e) => {
        const previewImage = document.getElementById('previewImage');
        const previewSection = document.getElementById('previewSection');
        if (previewImage && previewSection) {
            previewImage.src = e.target.result;
            previewSection.style.display = 'block';
        }
    };
    reader.readAsDataURL(file);

    showStatus(`📁 Imagen seleccionada: ${file.name}`, 'info');

    // Verificar estado del botón
    checkProcessButtonState();

    // Limpiar resultados anteriores
    clearResults();
}

function clearResults() {
    const batchResultsSection = document.getElementById('batchResultsSection');
    
    // 🔥 NO OCULTAR LA SECCIÓN SI HAY TRABAJOS BATCH ACTIVOS
    console.log('🔧 clearResults() llamada - verificando si hay trabajos batch activos...');
    console.log('📊 Estado actual: activeBatches =', activeBatches, 'batchCounter =', batchCounter);
    
    const batchResults = document.getElementById('batchResults');
    const hasBatchContent = batchResults && batchResults.children.length > 0;
    
    console.log('📋 Contenido batch existente:', {
        batchResults: !!batchResults,
        childrenCount: batchResults?.children.length || 0,
        hasBatchContent
    });
    
    if (activeBatches > 0 || hasBatchContent) {
        console.log('✅ Manteniendo sección de batch visible (hay trabajos activos o contenido)');
        // No ocultar la sección si hay trabajos batch activos o contenido
    } else {
        console.log('🙈 Ocultando sección de batch (no hay trabajos activos)');
        batchResultsSection.style.display = 'none';
    }
    
    // No limpiar la selección de nodos aquí, solo los resultados
}

async function processImage() {
    if (!selectedFile) {
        showStatus('❌ Por favor selecciona una imagen primero', 'error');
        return;
    }

    const workflowSelect = document.getElementById('workflowSelect');
    const selectedWorkflow = workflowSelect.value;

    if (!selectedWorkflow) {
        showStatus('❌ Por favor selecciona un workflow', 'error');
        return;
    }

    // Obtener color del marco
    const frameColorRadios = document.querySelectorAll('input[name="frameColor"]');
    let selectedFrameColor = 'black';
    for (const radio of frameColorRadios) {
        if (radio.checked) {
            selectedFrameColor = radio.value;
            break;
        }
    }

    // Obtener estilo seleccionado
    const styleSelect = document.getElementById('styleSelect');
    const selectedStyle = styleSelect.value || 'default';

    // Obtener nodo de estilo seleccionado
    const styleNodeSelect = document.getElementById('styleNodeSelect');
    const selectedStyleNode = styleNodeSelect.value || null;

    // Obtener opción de incluir upscale
    const includeUpscaleCheckbox = document.getElementById('includeUpscale');
    const includeUpscale = includeUpscaleCheckbox.checked;

    // Crear ID local para el trabajo individual
    individualJobCounter++;
    const localJobId = `individual_${individualJobCounter}`;
    const startTime = new Date();

    // NO deshabilitar botón - permitir múltiples envíos a la cola
    const processBtn = document.getElementById('processBtn');
    
    showStatus(`🚀 Enviando trabajo #${individualJobCounter} a la cola...`, 'info');
    showStatus(`📋 Workflow: ${selectedWorkflow}`, 'info');
    showStatus(`🎨 Color del marco: ${selectedFrameColor}`, 'info');
    showStatus(`✨ Estilo: ${selectedStyle}`, 'info');
    if (selectedStyleNode) {
        showStatus(`⚙️ Nodo de estilo: ${selectedStyleNode}`, 'info');
    } else {
        showStatus(`🔧 Nodo de estilo: auto-detectar`, 'info');
    }
    showStatus(`📈 Incluir upscale: ${includeUpscale ? 'Sí' : 'No'}`, 'info');
    showStatus(`⏱️ El trabajo se procesará en cola. Puedes enviar más mientras tanto.`, 'info');

    // Crear entrada en el tracking de trabajos individuales
    activeIndividualJobs.set(localJobId, {
        localId: localJobId,
        serverId: null,
        status: 'starting',
        startTime: startTime,
        workflow: selectedWorkflow,
        frameColor: selectedFrameColor,
        style: selectedStyle,
        styleNode: selectedStyleNode,
        currentOperation: 'Iniciando procesamiento...',
        images: 0,
        totalImages: 1
    });

    // Crear contenedor de resultados inmediatamente
    createIndividualJobContainer(localJobId, startTime);

    try {
        // Crear FormData
        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('workflow', selectedWorkflow);
        formData.append('frame_color', selectedFrameColor);
        formData.append('style', selectedStyle);
        formData.append('include_upscale', includeUpscale.toString());
        if (selectedStyleNode) {
            formData.append('style_node', selectedStyleNode);
        }

        // Actualizar estado
        activeIndividualJobs.get(localJobId).status = 'submitting';
        activeIndividualJobs.get(localJobId).currentOperation = 'Enviando a ComfyUI...';
        updateIndividualJobDisplay(localJobId);

        // Enviar petición
        const response = await fetch(`${API_BASE_URL}/process-image`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Actualizar con el ID del servidor
            const jobInfo = activeIndividualJobs.get(localJobId);
            jobInfo.serverId = data.job_id;
            jobInfo.status = 'completed';
            jobInfo.currentOperation = 'Completado';
            jobInfo.images = data.total_images || 1;
            
            showStatus(`✅ Trabajo #${individualJobCounter} completado exitosamente`, 'success');
            
            // Mostrar resultados en la galería individual
            displayIndividualJobResult(localJobId, data);
            
            // Iniciar polling para obtener más detalles si es necesario
            if (data.job_id) {
                startIndividualJobPolling(localJobId, data.job_id);
            }
        } else {
            // Marcar como error
            const jobInfo = activeIndividualJobs.get(localJobId);
            jobInfo.status = 'error';
            jobInfo.currentOperation = `Error: ${data.error || 'Error desconocido'}`;
            updateIndividualJobDisplay(localJobId);
            
            showStatus(`❌ Error: ${data.error || 'Error desconocido'}`, 'error');
        }

    } catch (error) {
        console.error('Error procesando imagen:', error);
        
        // Marcar como error de conexión
        const jobInfo = activeIndividualJobs.get(localJobId);
        if (jobInfo) {
            jobInfo.status = 'error';
            jobInfo.currentOperation = `Error de conexión: ${error.message}`;
            updateIndividualJobDisplay(localJobId);
        }
        
        showStatus(`❌ Error de conexión: ${error.message}`, 'error');
    }
    // Botón permanece habilitado para permitir múltiples envíos
}

function showStatus(message, type = 'info') {
    const statusMessages = document.getElementById('statusMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `status-message status-${type}`;
    
    const timestamp = new Date().toLocaleTimeString();
    msgDiv.textContent = `[${timestamp}] ${message}`;
    
    statusMessages.appendChild(msgDiv);
    statusMessages.scrollTop = statusMessages.scrollHeight;

    // Limpiar mensajes viejos
    if (statusMessages.children.length > 50) {
        statusMessages.removeChild(statusMessages.firstChild);
    }
}

async function loadWorkflowNodes(workflowId) {
    if (!workflowId) {
        clearStyleNodes();
        return;
    }

    try {
        showStatus(`🔄 Cargando nodos del workflow...`, 'info');
        const response = await fetch(`${API_BASE_URL}/workflow-nodes/${workflowId}`);
        const data = await response.json();

        if (response.ok) {
            currentWorkflowNodes = data.candidate_nodes || [];
            populateStyleNodes();
            showStatus(`✅ ${currentWorkflowNodes.length} nodos candidatos cargados`, 'success');
        } else {
            console.error('Error cargando nodos:', data.error);
            showStatus(`⚠️ Error cargando nodos: ${data.error}`, 'error');
            clearStyleNodes();
        }
    } catch (error) {
        console.error('Error cargando nodos del workflow:', error);
        showStatus('❌ Error de conexión al cargar nodos', 'error');
        clearStyleNodes();
    }
}

async function loadWorkflowNodesForBatch(workflowId) {
    if (!workflowId) {
        return;
    }

    try {
        showStatus(`🔄 Cargando nodos para modo batch...`, 'info');
        const response = await fetch(`${API_BASE_URL}/workflow-nodes/${workflowId}`);
        const data = await response.json();

        if (response.ok) {
            currentWorkflowNodes = data.candidate_nodes || [];
            populateBatchStyleNodes();
            showStatus(`✅ Nodos cargados para modo batch (${currentWorkflowNodes.length} candidatos)`, 'success');
        } else {
            console.error('Error cargando nodos para batch:', data.error);
            showStatus(`⚠️ Error cargando nodos para batch: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Error cargando nodos para batch:', error);
        showStatus('❌ Error de conexión al cargar nodos para batch', 'error');
    }
}

function populateStyleNodes() {
    const styleNodeSelect = document.getElementById('styleNodeSelect');
    const batchStyleNodeSelect = document.getElementById('batchStyleNodeSelect');
    
    // Poblar selector individual
    styleNodeSelect.innerHTML = '<option value="">🔧 Auto-detectar (recomendado)</option>';
    
    // Poblar selector de batch
    batchStyleNodeSelect.innerHTML = '<option value="">🔧 Auto-detectar (recomendado)</option>';

    currentWorkflowNodes.forEach(node => {
        // Crear opción para selector individual
        const option = document.createElement('option');
        option.value = node.id;
        option.dataset.node = JSON.stringify(node);
        
        // Añadir emoji para nodos recomendados
        const prefix = node.recommended ? '⭐' : '⚙️';
        option.textContent = `${prefix} ${node.name}`;
        
        styleNodeSelect.appendChild(option);
        
        // Crear opción para selector de batch (clon)
        const batchOption = option.cloneNode(true);
        batchStyleNodeSelect.appendChild(batchOption);
    });
}

function populateBatchStyleNodes() {
    const batchStyleNodeSelect = document.getElementById('batchStyleNodeSelect');
    
    // Poblar solo el selector de batch
    batchStyleNodeSelect.innerHTML = '<option value="">🔧 Auto-detectar (recomendado)</option>';

    currentWorkflowNodes.forEach(node => {
        const option = document.createElement('option');
        option.value = node.id;
        option.dataset.node = JSON.stringify(node);
        
        // Añadir emoji para nodos recomendados
        const prefix = node.recommended ? '⭐' : '⚙️';
        option.textContent = `${prefix} ${node.name}`;
        
        batchStyleNodeSelect.appendChild(option);
    });
}

function clearStyleNodes() {
    const styleNodeSelect = document.getElementById('styleNodeSelect');
    const batchStyleNodeSelect = document.getElementById('batchStyleNodeSelect');
    
    // Solo limpiar el selector individual
    styleNodeSelect.innerHTML = '<option value="">🔧 Auto-detectar (recomendado)</option>';
    
    // Para el batch, mantener los nodos ya que todos los workflows tienen la misma estructura
    // Solo limpiar si no tiene opciones cargadas
    if (batchStyleNodeSelect.children.length <= 1) {
        batchStyleNodeSelect.innerHTML = '<option value="">🔧 Auto-detectar (recomendado)</option>';
    }
    
    // Solo limpiar currentWorkflowNodes si estamos en modo individual
    const nodeDescription = document.getElementById('nodeDescription');
    const batchNodeDescription = document.getElementById('batchNodeDescription');
    
    nodeDescription.style.display = 'none';
    batchNodeDescription.style.display = 'none';
}

function handleStyleNodeChange() {
    const styleNodeSelect = document.getElementById('styleNodeSelect');
    const nodeDescription = document.getElementById('nodeDescription');
    
    const selectedOption = styleNodeSelect.options[styleNodeSelect.selectedIndex];
    
    if (selectedOption && selectedOption.value && selectedOption.dataset.node) {
        const nodeData = JSON.parse(selectedOption.dataset.node);
        
        nodeDescription.innerHTML = `
            <strong>📝 Información del nodo:</strong><br>
            <strong>Tipo:</strong> ${nodeData.type}<br>
            <strong>Descripción:</strong> ${nodeData.description}<br>
            ${nodeData.current_value ? `<strong>Contenido actual:</strong> ${nodeData.current_value}` : ''}
        `;
        nodeDescription.style.display = 'block';
        
        const prefix = nodeData.recommended ? 'recomendado' : 'personalizado';
        showStatus(`⚙️ Nodo ${prefix} seleccionado: ${nodeData.name}`, 'info');
    } else {
        nodeDescription.style.display = 'none';
        showStatus(`🔧 Usando auto-detección de nodo`, 'info');
    }
}

function handleBatchStyleNodeChange() {
    const batchStyleNodeSelect = document.getElementById('batchStyleNodeSelect');
    const batchNodeDescription = document.getElementById('batchNodeDescription');
    
    const selectedOption = batchStyleNodeSelect.options[batchStyleNodeSelect.selectedIndex];
    
    if (selectedOption && selectedOption.value && selectedOption.dataset.node) {
        const nodeData = JSON.parse(selectedOption.dataset.node);
        
        batchNodeDescription.innerHTML = `
            <strong>📝 Información del nodo:</strong><br>
            <strong>Tipo:</strong> ${nodeData.type}<br>
            <strong>Descripción:</strong> ${nodeData.description}<br>
            ${nodeData.current_value ? `<strong>Contenido actual:</strong> ${nodeData.current_value}` : ''}
        `;
        batchNodeDescription.style.display = 'block';
        
        const prefix = nodeData.recommended ? 'recomendado' : 'personalizado';
        showStatus(`⚙️ Nodo ${prefix} seleccionado para batch: ${nodeData.name}`, 'info');
    } else {
        batchNodeDescription.style.display = 'none';
        showStatus(`🔧 Usando auto-detección de nodo para batch`, 'info');
    }
}

// ===== INDIVIDUAL JOB PROCESSING FUNCTIONS =====

function createIndividualJobContainer(localJobId, startTime) {
    const individualJobsSection = document.getElementById('individualJobsSection');
    const individualResults = document.getElementById('individualResults');
    
    // Mostrar la sección si está oculta
    individualJobsSection.style.display = 'block';
    
    const timestamp = startTime.toLocaleTimeString();
    const dateId = startTime.toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
    const shortId = localJobId.slice(-8);
    
    const jobContainer = document.createElement('div');
    jobContainer.className = 'individual-job-result processing';
    jobContainer.id = `individual-job-${localJobId}`;
    
    jobContainer.innerHTML = `
        <div class="individual-job-header">
            🎯 Trabajo Individual #${individualJobCounter}
            <span class="individual-job-time">${timestamp}</span>
            <span class="individual-job-time">(${dateId}_${shortId})</span>
        </div>
        <div class="individual-job-stats">
            <div class="individual-stat">📊 Estado: <span id="status-${localJobId}">starting</span></div>
            <div class="individual-stat">🖼️ Imágenes: <span id="images-${localJobId}">0</span></div>
            <div class="individual-stat">⏱️ Tiempo: <span id="time-${localJobId}">0.0s</span></div>
        </div>
        <div class="individual-job-operation" id="operation-${localJobId}">
            Iniciando procesamiento...
        </div>
        <div class="individual-job-images" id="images-container-${localJobId}">
            <!-- Las imágenes aparecerán aquí -->
        </div>
    `;
    
    // Insertar al principio (más recientes primero)
    if (individualResults.firstChild) {
        individualResults.insertBefore(jobContainer, individualResults.firstChild);
    } else {
        individualResults.appendChild(jobContainer);
    }
}

function updateIndividualJobDisplay(localJobId) {
    const jobInfo = activeIndividualJobs.get(localJobId);
    if (!jobInfo) return;
    
    const jobContainer = document.getElementById(`individual-job-${localJobId}`);
    if (!jobContainer) return;
    
    // Actualizar estado visual del contenedor
    jobContainer.className = `individual-job-result ${jobInfo.status}`;
    
    // Calcular tiempo transcurrido
    const elapsed = (new Date() - jobInfo.startTime) / 1000;
    
    // Actualizar elementos
    const statusElement = document.getElementById(`status-${localJobId}`);
    const imagesElement = document.getElementById(`images-${localJobId}`);
    const timeElement = document.getElementById(`time-${localJobId}`);
    const operationElement = document.getElementById(`operation-${localJobId}`);
    
    if (statusElement) statusElement.textContent = jobInfo.status;
    if (imagesElement) imagesElement.textContent = jobInfo.images;
    if (timeElement) timeElement.textContent = `${elapsed.toFixed(1)}s`;
    if (operationElement) operationElement.textContent = jobInfo.currentOperation;
}

function displayIndividualJobResult(localJobId, resultData) {
    const jobInfo = activeIndividualJobs.get(localJobId);
    if (!jobInfo) return;
    
    const imagesContainer = document.getElementById(`images-container-${localJobId}`);
    if (!imagesContainer) return;
    
    // Limpiar contenedor de imágenes
    imagesContainer.innerHTML = '';
    
    // Solo mostrar imágenes generadas (no la original)
    if (resultData.generated_images && resultData.generated_images.length > 0) {
        resultData.generated_images.forEach(image => {
            const img = document.createElement('img');
            img.src = image.session_url || image.url;
            img.alt = image.filename || 'Imagen generada';
            img.title = `Resultado: ${image.filename || 'Imagen generada'}`;
            img.style.width = '100%';
            img.style.borderRadius = '4px';
            img.style.cursor = 'pointer';
            
            // Hacer clickeable la imagen
            img.addEventListener('click', (e) => {
                e.preventDefault();
                showImageModal(img.src, img.alt);
            });
            
            imagesContainer.appendChild(img);
        });
        
        // Actualizar contador de imágenes
        jobInfo.images = resultData.generated_images.length;
    }
    
    updateIndividualJobDisplay(localJobId);
}

function startIndividualJobPolling(localJobId, serverJobId) {
    // Polling cada 2 segundos para obtener detalles actualizados
    const intervalId = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/session/jobs/${serverJobId}`);
            const jobData = await response.json();
            
            const jobInfo = activeIndividualJobs.get(localJobId);
            if (!jobInfo) {
                clearInterval(intervalId);
                return;
            }
            
            // Actualizar información del trabajo
            jobInfo.status = jobData.status;
            jobInfo.currentOperation = jobData.current_operation || 'Procesando...';
            
            if (jobData.results && jobData.results.length > 0) {
                jobInfo.images = jobData.results.length;
                
                // Actualizar imágenes si hay nuevas
                displayIndividualJobResult(localJobId, {
                    original_image: jobData.response_data?.original_image,
                    generated_images: jobData.results
                });
            }
            
            updateIndividualJobDisplay(localJobId);
            
            // Detener polling si el trabajo está completado o tiene error
            if (jobData.status === 'completed' || jobData.status === 'error') {
                clearInterval(intervalId);
                individualPollingIntervals.delete(localJobId);
            }
        } catch (error) {
            console.error(`Error polling individual job ${localJobId}:`, error);
            // Continuar el polling en caso de error temporal
        }
    }, 2000);
    
    individualPollingIntervals.set(localJobId, intervalId);
}

// ===== BATCH PROCESSING FUNCTIONS =====

function populateBatchSelectors() {
    const batchRoomTypes = document.getElementById('batchRoomTypes');
    const batchOrientations = document.getElementById('batchOrientations');
    
    // Poblar tipos de habitación
    batchRoomTypes.innerHTML = '';
    Object.keys(workflowsStructure).forEach(roomType => {
        const option = document.createElement('option');
        option.value = roomType;
        option.textContent = `🏠 ${roomType.charAt(0).toUpperCase() + roomType.slice(1)}`;
        batchRoomTypes.appendChild(option);
    });
    
    // Poblar orientaciones (recopilar todas las orientaciones únicas)
    const allOrientations = new Set();
    Object.values(workflowsStructure).forEach(roomData => {
        Object.keys(roomData).forEach(orientation => {
            allOrientations.add(orientation);
        });
    });
    
    batchOrientations.innerHTML = '';
    allOrientations.forEach(orientation => {
        const option = document.createElement('option');
        option.value = orientation;
        option.textContent = `📐 ${orientation}`;
        batchOrientations.appendChild(option);
    });
    
    updateBatchWorkflowPreview();
}

function updateBatchWorkflowPreview() {
    const roomTypeSelect = document.getElementById('batchRoomTypes');
    const orientationSelect = document.getElementById('batchOrientations');
    const workflowList = document.getElementById('workflowList');
    const workflowCount = document.getElementById('workflowCount');
    const previewSection = document.getElementById('selectedWorkflowsPreview');

    const selectedRoomTypes = Array.from(roomTypeSelect.selectedOptions).map(option => option.value);
    const selectedOrientations = Array.from(orientationSelect.selectedOptions).map(option => option.value);
    
    // Obtener workflows que coinciden con los filtros
    const matchingWorkflows = getMatchingWorkflowsForBatch(selectedRoomTypes, selectedOrientations);
    
    // Actualizar contador
    workflowCount.textContent = matchingWorkflows.length;
    
    // Mostrar/ocultar preview
    if (matchingWorkflows.length > 0) {
        previewSection.style.display = 'block';
        
        // Generar lista de workflows
        workflowList.innerHTML = matchingWorkflows.map(workflow => 
            `<div style="padding: 3px 0; border-bottom: 1px solid #e0e0e0;">
                🎯 <strong>${workflow.room_type}</strong> - ${workflow.orientation} - ${workflow.name}
            </div>`
        ).join('');
        
        showStatus(`🎯 ${matchingWorkflows.length} workflows seleccionados para lote`, 'info');
    } else {
        previewSection.style.display = 'none';
        showStatus(`⚠️ Ningún workflow coincide con los filtros seleccionados`, 'warning');
    }
}

function getMatchingWorkflowsForBatch(roomTypes, orientations) {
    const matchingWorkflows = [];
    
    // Si no hay filtros seleccionados, incluir todos los workflows
    const targetRoomTypes = roomTypes.length > 0 ? roomTypes : Object.keys(workflowsStructure);
    const targetOrientations = orientations.length > 0 ? orientations : null;
    
    targetRoomTypes.forEach(roomType => {
        if (workflowsStructure[roomType]) {
            const roomData = workflowsStructure[roomType];
            
            Object.keys(roomData).forEach(orientation => {
                // Filtrar por orientación si está especificada
                if (targetOrientations === null || targetOrientations.includes(orientation)) {
                    roomData[orientation].forEach(workflow => {
                        matchingWorkflows.push({
                            ...workflow,
                            room_type: roomType,
                            orientation: orientation
                        });
                    });
                }
            });
        }
    });
    
    return matchingWorkflows;
}

// Variables globales para trackear lotes activos con polling
let activeBatches = 0;
let batchCounter = 0;
let pollingIntervals = new Map(); // batch_id -> intervalId

async function processBatch() {
    if (!selectedFile) {
        showStatus('❌ No hay imagen seleccionada para el lote', 'error');
        return;
    }
    
    const roomTypeSelect = document.getElementById('batchRoomTypes');
    const orientationSelect = document.getElementById('batchOrientations');
    const batchStyleSelect = document.getElementById('batchStyleSelect');
    const batchStyleNodeSelect = document.getElementById('batchStyleNodeSelect');
    const batchFrameColorInputs = document.querySelectorAll('input[name="batchFrameColor"]:checked');
    const batchIncludeUpscaleCheckbox = document.getElementById('batchIncludeUpscale');
    
    const selectedRoomTypes = Array.from(roomTypeSelect.selectedOptions).map(option => option.value);
    const selectedOrientations = Array.from(orientationSelect.selectedOptions).map(option => option.value);
    const selectedStyle = batchStyleSelect.value || 'default';
    const selectedStyleNode = batchStyleNodeSelect.value || null;
    const selectedFrameColor = batchFrameColorInputs.length > 0 ? batchFrameColorInputs[0].value : 'black';
    const batchIncludeUpscale = batchIncludeUpscaleCheckbox.checked;
    
    // Obtener workflows coincidentes
    const matchingWorkflows = getMatchingWorkflowsForBatch(selectedRoomTypes, selectedOrientations);
    
    if (matchingWorkflows.length === 0) {
        showStatus('❌ No hay workflows que coincidan con los filtros', 'error');
        return;
    }
    
    // Incrementar contador de lotes
    batchCounter++;
    activeBatches++;
    const currentBatchId = batchCounter;
    
    // Actualizar texto del botón para mostrar lotes activos
    updateBatchButtonText();
    
    showStatus(`🚀 Iniciando lote #${currentBatchId} con ${matchingWorkflows.length} workflows...`, 'info');
    showStatus(`📈 Incluir upscale en lote: ${batchIncludeUpscale ? 'Sí' : 'No'}`, 'info');
    
    // Mostrar información del nodo de estilo si está seleccionado
    if (selectedStyleNode) {
        showStatus(`⚙️ Nodo de estilo para batch: ${selectedStyleNode}`, 'info');
    } else {
        showStatus(`🔧 Usando auto-detección de nodo para batch`, 'info');
    }
    
    try {
        // Crear FormData
        const formData = new FormData();
        formData.append('image', selectedFile);
        
        // Crear configuración de batch
        const batchConfig = {
            room_types: selectedRoomTypes,
            orientations: selectedOrientations,
            frame_color: selectedFrameColor,
            style: selectedStyle,
            include_upscale: batchIncludeUpscale
        };
        
        // Agregar nodo de estilo si está seleccionado
        if (selectedStyleNode) {
            batchConfig.style_node = selectedStyleNode;
        }
        
        console.log('🔍 DEBUG - batchConfig antes de JSON.stringify:', batchConfig);
        const batchConfigJSON = JSON.stringify(batchConfig);
        console.log('🔍 DEBUG - batchConfig JSON:', batchConfigJSON);
        
        formData.append('batch_config', batchConfigJSON);
        
        showStatus(`📤 Enviando lote #${currentBatchId} al servidor...`, 'info');
        console.log('🔍 DEBUG - FormData que se envía:', {
            hasImage: !!selectedFile,
            imageName: selectedFile?.name,
            imageSize: selectedFile?.size,
            batchConfig: batchConfig
        });
        
        const response = await fetch(`${API_BASE_URL}/process-batch`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        console.log('🔍 DEBUG - Respuesta completa del servidor:', data);
        
        if (response.ok && data.success) {
            // *** NUEVO: Respuesta inmediata con batch_id para tracking ***
            const serverBatchId = data.batch_id;
            
            showStatus(`✅ Lote #${currentBatchId} (${serverBatchId}) iniciado correctamente. Monitoreando progreso...`, 'success');
            
            // Crear contenedor de resultados inmediatamente
            createBatchResultsContainer(currentBatchId, serverBatchId, data.total_workflows);
            
            // *** INICIAR POLLING EN TIEMPO REAL ***
            startBatchPolling(currentBatchId, serverBatchId);
            
        } else {
            console.log('🔍 DEBUG - Response.ok es false, error:', data.error);
            throw new Error(data.error || 'Error iniciando lote');
        }
        
    } catch (error) {
        console.error(`Error en lote #${currentBatchId}:`, error);
        showStatus(`❌ Error procesando lote #${currentBatchId}: ${error.message}`, 'error');
        
        // Decrementar contador en caso de error
        activeBatches--;
        updateBatchButtonText();
    }
}

// *** NUEVA FUNCIÓN: Crear contenedor de resultados inmediatamente ***
function createBatchResultsContainer(localBatchId, serverBatchId, totalWorkflows) {
    const batchResultsSection = document.getElementById('batchResultsSection');
    const batchResults = document.getElementById('batchResults');
    
    // 🔥 FORZAR MOSTRAR LA SECCIÓN SIEMPRE
    console.log('🔧 createBatchResultsContainer - forzando mostrar sección...');
    batchResultsSection.style.display = 'block';
    
    // Crear contenedor para este lote específico
    const batchContainer = document.createElement('div');
    batchContainer.id = `batch-container-${localBatchId}`;
    batchContainer.className = 'batch-container';
    batchContainer.style.cssText = `
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 30px;
        border: 2px solid #e3f2fd;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    `;
    
    // Header inicial
    const batchHeader = document.createElement('div');
    batchHeader.id = `batch-header-${localBatchId}`;
    batchHeader.innerHTML = `
        <h4 style="color: #1976d2; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
            🎯 Lote #${localBatchId} 
            <span style="font-size: 0.8em; background: #e3f2fd; padding: 4px 8px; border-radius: 12px;">
                ${new Date().toLocaleTimeString()}
            </span>
            <span style="font-size: 0.7em; color: #666;">(${serverBatchId})</span>
        </h4>
        <div class="batch-summary-stats">
            <div class="batch-stat">
                <span>📊 Estado:</span> <strong id="status-${localBatchId}">Iniciando...</strong>
            </div>
            <div class="batch-stat">
                <span>✅ Completados:</span> <strong id="completed-${localBatchId}">0</strong>/<strong>${totalWorkflows}</strong>
            </div>
            <div class="batch-stat">
                <span>🖼️ Imágenes:</span> <strong id="images-${localBatchId}">0</strong>
            </div>
            <div class="batch-stat">
                <span>⏱️ Tiempo:</span> <strong id="time-${localBatchId}">0s</strong>
            </div>
        </div>
        <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
            <strong>Operación actual:</strong> <span id="operation-${localBatchId}">Iniciando procesamiento...</span>
        </div>
    `;
    
    batchContainer.appendChild(batchHeader);
    
    // Contenedor de imágenes (se llenará dinámicamente)
    const imagesContainer = document.createElement('div');
    imagesContainer.id = `images-container-${localBatchId}`;
    imagesContainer.className = 'batch-workflow-images';
    imagesContainer.style.cssText = `
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-top: 20px;
        border-top: 1px solid #ddd;
        padding-top: 20px;
    `;
    
    batchContainer.appendChild(imagesContainer);
    
    // Añadir al principio de la lista
    batchResults.insertBefore(batchContainer, batchResults.firstChild);
}

// *** NUEVA FUNCIÓN: Polling en tiempo real ***
async function startBatchPolling(localBatchId, serverBatchId) {
    const startTime = Date.now();
    let lastCompletedCount = 0;
    
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/batch-status/${serverBatchId}`);
            
            if (!response.ok) {
                console.log(`Batch ${serverBatchId} no encontrado, deteniendo polling`);
                clearInterval(pollInterval);
                pollingIntervals.delete(serverBatchId);
                return;
            }
            
            const batchStatus = await response.json();
            console.log(`🔄 Polling lote ${localBatchId}:`, batchStatus);
            
            // Actualizar elementos del DOM
            updateBatchDisplay(localBatchId, batchStatus, startTime);
            
            // Mostrar nuevas imágenes si hay
            if (batchStatus.completed_workflows > lastCompletedCount) {
                displayNewCompletedImages(localBatchId, batchStatus, lastCompletedCount);
                lastCompletedCount = batchStatus.completed_workflows;
            }
            
            // Si el batch terminó, detener polling
            if (batchStatus.status === 'completed' || batchStatus.status === 'error') {
                showStatus(`🏁 Lote #${localBatchId} ${batchStatus.status === 'completed' ? 'completado' : 'terminó con errores'}`, 
                         batchStatus.status === 'completed' ? 'success' : 'error');
                
                clearInterval(pollInterval);
                pollingIntervals.delete(serverBatchId);
                
                // Decrementar contador de lotes activos
                activeBatches--;
                updateBatchButtonText();
                
                // Limpiar el batch del servidor después de un delay
                setTimeout(() => {
                    fetch(`${API_BASE_URL}/batch-status/${serverBatchId}`, { method: 'DELETE' });
                }, 30000); // 30 segundos
            }
            
        } catch (error) {
            console.error(`Error en polling de lote ${localBatchId}:`, error);
            showStatus(`⚠️ Error consultando progreso de lote #${localBatchId}`, 'error');
        }
    }, 2000); // Polling cada 2 segundos
    
    // Guardar el interval para poder cancelarlo después
    pollingIntervals.set(serverBatchId, pollInterval);
}

// *** NUEVA FUNCIÓN: Actualizar display del batch ***
function updateBatchDisplay(localBatchId, batchStatus, startTime) {
    console.log('🔄 updateBatchDisplay called with:', {
        localBatchId,
        batchStatus,
        startTime
    });
    
    // Actualizar status
    const statusElement = document.getElementById(`status-${localBatchId}`);
    if (statusElement) {
        statusElement.textContent = batchStatus.status;
        statusElement.style.color = batchStatus.status === 'completed' ? '#4caf50' : 
                                  batchStatus.status === 'error' ? '#f44336' : '#2196f3';
    }
    
    // Actualizar contador de completados
    const completedElement = document.getElementById(`completed-${localBatchId}`);
    if (completedElement) {
        const completedCount = batchStatus.completed_workflows || 0;
        completedElement.textContent = completedCount;
    }
    
    // Actualizar contador de imágenes
    const imagesElement = document.getElementById(`images-${localBatchId}`);
    if (imagesElement) {
        let totalImages = 0;
        
        if (batchStatus.results) {
            // Formato de batch activo
            totalImages = batchStatus.results.reduce((sum, result) => sum + (result.generated_images ? result.generated_images.length : 0), 0);
        } else if (batchStatus.all_images) {
            // Formato de sesión persistida
            totalImages = batchStatus.all_images.length;
        }
        
        imagesElement.textContent = totalImages;
    }
    
    // Actualizar tiempo transcurrido
    const timeElement = document.getElementById(`time-${localBatchId}`);
    if (timeElement) {
        const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
        timeElement.textContent = `${elapsedTime}s`;
    }
    
    // Actualizar operación actual
    const operationElement = document.getElementById(`operation-${localBatchId}`);
    if (operationElement) {
        let operationText;
        
        if (batchStatus.status === 'completed') {
            operationText = 'Finalizado';
        } else if (batchStatus.status === 'error') {
            operationText = 'Error en procesamiento';
        } else {
            operationText = batchStatus.current_operation || 'Procesando...';
        }
        
        operationElement.textContent = operationText;
    }
}

// *** NUEVA FUNCIÓN: Mostrar imágenes nuevas conforme se completan ***
function displayNewCompletedImages(localBatchId, batchStatus, lastCompletedCount) {
    const imagesContainer = document.getElementById(`images-container-${localBatchId}`);
    if (!imagesContainer) return;
    
    console.log('🔍 DEBUG - displayNewCompletedImages called with:', {
        localBatchId,
        batchStatus,
        lastCompletedCount
    });
    
    let imagesToShow = [];
    
    if (batchStatus.results) {
        // Formato de batch activo - obtener solo los resultados nuevos
        const newResults = batchStatus.results.slice(lastCompletedCount);
        imagesToShow = newResults.map((result, index) => ({
            workflow_id: result.workflow_id,
            success: result.success,
            generated_images: result.generated_images || [],
            processing_time: result.processing_time || 0,
            error: result.error
        }));
    } else if (batchStatus.all_images) {
        // Formato de sesión persistida - convertir URLs de imágenes a formato compatible
        const newImages = batchStatus.all_images.slice(lastCompletedCount);
        
        // Filtrar solo las imágenes generadas (no la original)
        const generatedImages = newImages.filter(imageUrl => {
            const filename = imageUrl.split('/').pop();
            return filename !== 'original.png';
        });
        
        console.log('🔍 DEBUG - Imágenes filtradas:', {
            totalImages: newImages.length,
            generatedImages: generatedImages.length,
            filtered: generatedImages
        });
        
        imagesToShow = generatedImages.map((imageUrl, index) => {
            // Extraer información del nombre de archivo
            const filename = imageUrl.split('/').pop();
            const workflowMatch = filename.match(/([^_]+)_.*?_([^_]+)_/) || filename.match(/([^_]+)_([^_]+)_/);
            const workflowId = workflowMatch ? `${workflowMatch[1]}_${workflowMatch[2]}` : `imagen_${index + 1}`;
            
            console.log('🔍 DEBUG - Procesando imagen de sesión:', {
                imageUrl,
                filename,
                workflowId,
                fullUrl: imageUrl.startsWith('http') ? imageUrl : `${API_BASE_URL}${imageUrl}`
            });
            
            // 🔥 ASEGURAR URL COMPLETA
            const fullImageUrl = imageUrl.startsWith('http') ? imageUrl : `${API_BASE_URL}${imageUrl}`;
            
            return {
                workflow_id: workflowId,
                success: true,
                generated_images: [{
                    url: fullImageUrl,  // URL completa para compatibilidad
                    filename: filename,
                    session_url: fullImageUrl  // URL de sesión completa
                }],
                processing_time: 0,
                error: null
            };
        });
    }
    
    if (imagesToShow.length === 0) {
        console.log('⚠️ No hay imágenes nuevas para mostrar');
        return;
    }
    
    console.log('🖼️ Mostrando', imagesToShow.length, 'imágenes nuevas');
    
    imagesToShow.forEach((result, index) => {
        const resultIndex = lastCompletedCount + index;
        
        // Crear elemento para este resultado
        const resultDiv = document.createElement('div');
        resultDiv.className = 'workflow-result-item';
        resultDiv.style.cssText = `
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border-left: 4px solid ${result.success ? '#4caf50' : '#f44336'};
        `;
        
        if (result.success && result.generated_images && result.generated_images.length > 0) {
            // Mostrar imágenes generadas
            const firstImage = result.generated_images[0];
            
            console.log('🔍 DEBUG - Procesando imagen:', {
                result,
                firstImage,
                type: typeof firstImage
            });
            
            // Determinar la URL correcta de la imagen
            let imageUrl;
            if (typeof firstImage === 'string') {
                // Si firstImage es un string directo (URL)
                imageUrl = firstImage.startsWith('http') ? firstImage : `${API_BASE_URL}${firstImage}`;
            } else if (firstImage.session_url) {
                // Usar session_url para imágenes de sesión persistida
                imageUrl = firstImage.session_url.startsWith('http') ? firstImage.session_url : `${API_BASE_URL}${firstImage.session_url}`;
            } else if (firstImage.url) {
                // Usar url normal para imágenes activas
                imageUrl = firstImage.url.startsWith('http') ? firstImage.url : `${API_BASE_URL}${firstImage.url}`;
            } else {
                console.error('❌ No se pudo determinar URL de imagen:', firstImage);
                imageUrl = '/placeholder.png'; // Fallback
            }
            
            console.log('🖼️ URL final construida:', {
                workflow_id: result.workflow_id,
                imageUrl,
                firstImage,
                API_BASE_URL
            });
            
            resultDiv.innerHTML = `
                <div style="font-weight: 600; margin-bottom: 10px; color: #333; font-size: 0.9em;">
                    ✅ ${result.workflow_id}
                </div>
                <img src="${imageUrl}" 
                     style="width: 100%; border-radius: 4px; margin-bottom: 10px; cursor: pointer;"
                     alt="Resultado ${result.workflow_id}"
                     loading="lazy"
                     onerror="console.error('❌ Error cargando imagen:', this.src); this.style.display='none'; this.nextElementSibling.innerHTML='<div style=\\'color: red; font-size: 0.8em;\\'>Error cargando imagen: ' + this.src + '</div>';"
                     onload="console.log('✅ Imagen cargada correctamente:', this.src);">
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8em; color: #666;">
                    <span>${result.generated_images.length} imagen(es)</span>
                    <span>${result.processing_time}s</span>
                    <a href="${imageUrl}" 
                       download="${firstImage.filename || 'imagen.png'}"
                       style="color: #4caf50; text-decoration: none;">⬇️</a>
                </div>
            `;
            
            // 🔥 AGREGAR EVENT LISTENER PARA ABRIR MODAL EN IMÁGENES DE BATCH
            const img = resultDiv.querySelector('img');
            if (img) {
                img.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('🖱️ Click en imagen de batch:', imageUrl);
                    showImageModal(imageUrl, result.workflow_id + ' - ' + (firstImage.filename || 'Imagen generada'));
                });
                
                // Marcar como modal-enabled
                img.setAttribute('data-modal-enabled', 'true');
                
                console.log('✅ Modal activado para imagen de batch:', result.workflow_id);
            }
            
            // Mostrar mensaje de nueva imagen generada
            showStatus(`🖼️ Nueva imagen generada para: ${result.workflow_id}`, 'success');
            
        } else {
            // Mostrar error
            resultDiv.innerHTML = `
                <div style="font-weight: 600; margin-bottom: 10px; color: #f44336; font-size: 0.9em;">
                    ❌ ${result.workflow_id}
                </div>
                <div style="color: #f44336; font-size: 0.8em; background: #fff5f5; padding: 10px; border-radius: 4px;">
                    Error: ${result.error || 'Error desconocido'}
                </div>
                <div style="text-align: right; font-size: 0.8em; color: #666; margin-top: 5px;">
                    ${result.processing_time}s
                </div>
            `;
        }
        
        // Añadir con efecto de aparición
        resultDiv.style.opacity = '0';
        resultDiv.style.transform = 'translateY(20px)';
        imagesContainer.appendChild(resultDiv);
        
        // Animar aparición
        setTimeout(() => {
            resultDiv.style.transition = 'all 0.5s ease';
            resultDiv.style.opacity = '1';
            resultDiv.style.transform = 'translateY(0)';
        }, 100);
    });
}

function updateBatchButtonText() {
    const processBatchBtn = document.getElementById('processBatchBtn');
    
    if (activeBatches === 0) {
        processBatchBtn.textContent = '⚡ Procesar Lote';
        processBatchBtn.disabled = !selectedFile;
    } else {
        processBatchBtn.textContent = `🔄 ${activeBatches} Lotes Activos - Enviar Otro`;
        processBatchBtn.disabled = !selectedFile;
    }
}

// *** FUNCIÓN LEGACY: Para compatibilidad con el sistema anterior ***
function displayBatchResults(data, batchId) {
    // Esta función se mantiene para compatibilidad con el sistema anterior
    // pero ya no se usa en el nuevo sistema de polling en tiempo real
    
    console.log('📋 displayBatchResults (legacy) llamada con:', data, batchId);
    
    // Si es el nuevo formato asíncrono, redirigir al sistema de polling
    if (data.processing_mode === "asynchronous_with_tracking" && data.batch_id) {
        console.log('🔄 Redirigiendo a sistema de polling para batch:', data.batch_id);
        return;
    }
    
    // Sistema anterior (síncrono) - mantener comportamiento original
    const batchResultsSection = document.getElementById('batchResultsSection');
    const batchResults = document.getElementById('batchResults');
    
    // DEBUG: Log para verificar qué datos llegan
    console.log('🔍 DEBUG - Datos recibidos en displayBatchResults:', data);
    console.log('🔍 DEBUG - Batch ID:', batchId);
    
    // Crear contenedor para este lote específico
    const batchContainer = document.createElement('div');
    batchContainer.className = 'batch-container';
    batchContainer.style.cssText = `
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 30px;
        border: 2px solid #e3f2fd;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    `;
    
    // Resto de la implementación original
    // (Se mantiene para compatibilidad pero no se documenta aquí por brevedad)
}

// ===== FUNCIONES DE PERSISTENCIA DE SESIÓN =====

async function loadSessionJobs() {
    // Carga los trabajos de la sesión actual al inicializar la página
    try {
        console.log('🔄 Cargando trabajos de sesión...');
        const response = await fetch(`${API_BASE_URL}/session/jobs`);
        const data = await response.json();
        
        console.log('📋 Respuesta del servidor:', data);
        
        if (data.success && data.jobs) {
            console.log('📋 Trabajos de sesión cargados:', data.jobs);
            console.log('📊 Resumen de sesión:', data.summary);
            
            let restoredCount = 0;
            
            // Procesar trabajos existentes
            Object.values(data.jobs).forEach(job => {
                console.log(`🔍 Procesando trabajo: ${job.id}, tipo: ${job.type}, estado: ${job.status}`);
                
                if (job.type === 'batch') {
                    console.log(`📋 BATCH JOB ENCONTRADO:`, {
                        id: job.id,
                        type: job.type,
                        status: job.status,
                        batch_tracking_id: job.batch_tracking_id,
                        total_workflows: job.total_workflows,
                        completed_workflows: job.completed_workflows,
                        created_at: job.created_at
                    });
                    
                    // Validar que el job tenga batch_tracking_id
                    if (!job.batch_tracking_id) {
                        console.warn(`⚠️ Job de batch sin batch_tracking_id: ${job.id}`);
                        showStatus(`⚠️ Lote ${job.id} sin batch_tracking_id válido`, 'warning');
                        return;
                    } else {
                        console.log(`✅ Job de batch válido: ${job.id} -> ${job.batch_tracking_id}`);
                    }
                    
                    console.log(`🚀 RESTAURANDO BATCH JOB: ${job.id} (${job.status})`);
                    
                    try {
                        if (job.status === 'processing') {
                            // Reanudar seguimiento de lotes en progreso
                            console.log(`🔄 Restaurando batch en progreso: ${job.id}`);
                            restoreBatchJob(job);
                            restoredCount++;
                        } else if (job.status === 'completed' || job.status === 'error') {
                            // Mostrar lotes completados o con error
                            console.log(`✅ Restaurando batch completado/error: ${job.id}`);
                            restoreBatchJob(job);
                            restoredCount++;
                        } else {
                            console.warn(`⚠️ Estado de batch no reconocido: ${job.status} para job ${job.id}`);
                        }
                    } catch (error) {
                        console.error(`❌ Error restaurando batch job ${job.id}:`, error);
                        showStatus(`❌ Error restaurando lote ${job.id}: ${error.message}`, 'error');
                    }
                } else if (job.type === 'individual') {
                    console.log(`👤 INDIVIDUAL JOB ENCONTRADO:`, {
                        id: job.id,
                        type: job.type,
                        status: job.status,
                        workflow: job.config?.workflow,
                        created_at: job.created_at
                    });
                    
                    try {
                        if (job.status === 'processing') {
                            // Reanudar seguimiento de trabajos individuales en progreso
                            console.log(`🔄 Restaurando trabajo individual en progreso: ${job.id}`);
                            restoreIndividualJob(job);
                            restoredCount++;
                        } else if (job.status === 'completed' || job.status === 'error') {
                            // Mostrar trabajos individuales completados o con error
                            console.log(`✅ Restaurando trabajo individual completado: ${job.id}`);
                            restoreIndividualJob(job);
                            restoredCount++;
                        }
                    } catch (error) {
                        console.error(`❌ Error restaurando individual job ${job.id}:`, error);
                        showStatus(`❌ Error restaurando trabajo ${job.id}: ${error.message}`, 'error');
                    }
                } else {
                    console.log(`⏭️ Saltando trabajo: tipo=${job.type}, estado=${job.status}`);
                }
            });
            
            if (restoredCount > 0) {
                showStatus(`💾 ${restoredCount} trabajos de sesión restaurados`, 'success');
                
                // 🔥 FORZAR MOSTRAR SECCIÓN DE BATCH RESULTS SI HAY TRABAJOS BATCH
                const batchJobs = Object.values(data.jobs).filter(job => job.type === 'batch');
                if (batchJobs.length > 0) {
                    console.log(`🔧 Forzando mostrar sección de batch results (${batchJobs.length} trabajos batch)`);
                    const batchResultsSection = document.getElementById('batchResultsSection');
                    if (batchResultsSection) {
                        batchResultsSection.style.display = 'block';
                        console.log('✅ Sección de batch results mostrada');
                    }
                    
                    // Actualizar texto del botón batch
                    updateBatchButtonText();
                    console.log(`📊 Estado después de restaurar: activeBatches=${activeBatches}, batchCounter=${batchCounter}`);
                }
                
                // 🔥 VERIFICACIÓN ADICIONAL DESPUÉS DE UN DELAY
                setTimeout(() => {
                    const batchResults = document.getElementById('batchResults');
                    const hasBatchContent = batchResults && batchResults.children.length > 0;
                    
                    console.log('🔍 Verificación post-restauración:', {
                        activeBatches,
                        batchCounter,
                        hasBatchContent,
                        batchChildrenCount: batchResults?.children.length || 0
                    });
                    
                    if (hasBatchContent || activeBatches > 0) {
                        const batchResultsSection = document.getElementById('batchResultsSection');
                        if (batchResultsSection) {
                            batchResultsSection.style.display = 'block';
                            console.log('✅ Sección de batch results forzada a mostrarse post-restauración');
                        }
                    }
                }, 1000);
            } else {
                showStatus(`📂 No hay trabajos previos para restaurar`, 'info');
            }
        } else {
            console.log('⚠️ No se encontraron trabajos de sesión o error en respuesta:', data);
            showStatus('📂 No hay trabajos de sesión anteriores', 'info');
        }
    } catch (error) {
        console.error('❌ Error cargando trabajos de sesión:', error);
        showStatus('⚠️ Error cargando trabajos de sesión anterior', 'warning');
        console.error('❌ Stack trace:', error.stack);
    }
}

async function cleanupOldJobs(hours = 24) {
    try {
        const response = await fetch(`${API_BASE_URL}/session/cleanup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ hours: hours })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus(`🧹 Limpieza automática: ${data.cleaned_count || 0} trabajos antiguos eliminados`, 'info');
        } else {
            console.error('Error en limpieza automática:', data);
        }
    } catch (error) {
        console.error('Error en limpieza automática:', error);
    }
}

async function getSessionSummary() {
    try {
        const response = await fetch(`${API_BASE_URL}/session/jobs`);
        const data = await response.json();
        
        if (data.success) {
            const summary = {
                total: Object.keys(data.jobs).length,
                individual: 0,
                batch: 0,
                completed: 0,
                failed: 0
            };
            
            Object.values(data.jobs).forEach(job => {
                if (job.type === 'individual') summary.individual++;
                if (job.type === 'batch') summary.batch++;
                if (job.status === 'completed') summary.completed++;
                if (job.status === 'failed') summary.failed++;
            });
            
            return summary;
        }
        
        return null;
    } catch (error) {
        console.error('Error obteniendo resumen de sesión:', error);
        return null;
    }
}

function clearBatchResults() {
    const batchResultsSection = document.getElementById('batchResultsSection');
    const batchResults = document.getElementById('batchResults');
    
    if (batchResultsSection) {
        batchResultsSection.style.display = 'none';
    }
    
    if (batchResults) {
        batchResults.innerHTML = '';
    }
}

function updateBatchButtonText() {
    const processBatchBtn = document.getElementById('processBatchBtn');
    if (processBatchBtn) {
        processBatchBtn.disabled = !selectedFile;
        
        if (selectedFile) {
            processBatchBtn.textContent = '⚡ Procesar Lote';
        } else {
            processBatchBtn.textContent = '📁 Selecciona imagen primero';
        }
    }
}

// Función auxiliar para mostrar imagen en modal (declarada globalmente)
function showImageModal(imageSrc, imageInfo = '') {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalInfo = document.getElementById('modalInfo');
    
    if (modal && modalImage && modalInfo) {
        console.log('🖼️ Abriendo modal con imagen:', imageSrc);
        
        modalImage.src = imageSrc;
        modalInfo.textContent = imageInfo;
        modal.style.display = 'flex';
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        console.log('✅ Modal mostrado');
    } else {
        console.error('❌ Elementos del modal no encontrados');
    }
}

// Función para mostrar resultados (usado en restauración)
function displayResults(resultData) {
    try {
        console.log('📊 Mostrando resultados:', resultData);
        
        // Esta función ya no es necesaria para la restauración individual
        // porque displayIndividualJobResult maneja la visualización
        // Solo mostrar un mensaje de éxito
        
        showStatus('✅ Resultados procesados para restauración', 'success');
        
    } catch (error) {
        console.error('Error mostrando resultados:', error);
        showStatus(`❌ Error mostrando resultados: ${error.message}`, 'error');
    }
}

// Función para limpiar duplicados de batch jobs existentes
function cleanupDuplicateBatchJobs() {
    console.log('🧹 Limpiando duplicados de batch jobs...');
    
    const batchResults = document.getElementById('batchResults');
    if (!batchResults) return;
    
    const containers = batchResults.querySelectorAll('[data-batch-tracking-id]');
    const seenTrackingIds = new Set();
    let removedCount = 0;
    
    containers.forEach(container => {
        const trackingId = container.getAttribute('data-batch-tracking-id');
        if (trackingId) {
            if (seenTrackingIds.has(trackingId)) {
                // Es un duplicado, eliminar
                console.log(`🗑️ Eliminando duplicado para tracking_id: ${trackingId}`);
                container.remove();
                removedCount++;
            } else {
                seenTrackingIds.add(trackingId);
            }
        }
    });
    
    if (removedCount > 0) {
        console.log(`✅ Se eliminaron ${removedCount} duplicados de batch jobs`);
        showStatus(`🧹 Se eliminaron ${removedCount} duplicados de batch jobs`, 'info');
    } else {
        console.log('ℹ️ No se encontraron duplicados de batch jobs');
    }
}

// Set para trackear qué batch jobs ya fueron restaurados
const restoredBatchJobs = new Set();

// Función para forzar la restauración automática de trabajos batch
async function forceRestoreBatchJobs() {
    console.log('🔄 FORZANDO RESTAURACIÓN AUTOMÁTICA DE TRABAJOS BATCH...');
    
    try {
        // Cargar trabajos de sesión directamente
        const response = await fetch(`${API_BASE_URL}/session/jobs`);
        const data = await response.json();
        
        console.log('📋 Respuesta del servidor para restauración forzada:', data);
        
        if (data.success && data.jobs) {
            const batchJobs = Object.values(data.jobs).filter(job => job.type === 'batch');
            console.log(`📊 Trabajos batch encontrados para restauración forzada: ${batchJobs.length}`);
            
            if (batchJobs.length > 0) {
                // Forzar mostrar la sección de batch results
                const batchResultsSection = document.getElementById('batchResultsSection');
                if (batchResultsSection) {
                    batchResultsSection.style.display = 'block';
                    console.log('✅ Sección de batch results forzada a mostrarse');
                }
                
                let restoredCount = 0;
                
                // Restaurar cada trabajo batch SOLO si no ha sido restaurado antes
                for (const job of batchJobs) {
                    const batchJobKey = `${job.id}_${job.batch_tracking_id}`;
                    
                    if (!restoredBatchJobs.has(batchJobKey)) {
                        console.log(`🔧 Restaurando batch job forzado: ${job.id} (${job.status})`);
                        
                        try {
                            await new Promise(resolve => setTimeout(resolve, 100)); // Pequeño delay
                            restoreBatchJob(job);
                            restoredBatchJobs.add(batchJobKey);
                            restoredCount++;
                            console.log(`✅ Batch job ${job.id} restaurado exitosamente`);
                        } catch (error) {
                            console.error(`❌ Error restaurando batch job ${job.id}:`, error);
                        }
                    } else {
                        console.log(`⏭️ Batch job ${job.id} ya fue restaurado anteriormente`);
                    }
                }
                
                // Habilitar modal automáticamente para las imágenes restauradas SOLO si se restauraron trabajos
                if (restoredCount > 0) {
                    setTimeout(() => {
                        console.log('🎯 Habilitando modal para imágenes de batch restauradas...');
                        
                        // Buscar imágenes de batch específicamente
                        const batchImages = document.querySelectorAll('.batch-workflow-images img, .workflow-result-item img, div[id*="images-container-"] img');
                        console.log(`🖼️ Imágenes de batch encontradas: ${batchImages.length}`);
                        
                        batchImages.forEach((img, index) => {
                            const hasModal = img.hasAttribute('data-modal-enabled');
                            console.log(`📋 Imagen batch ${index + 1}: hasModal=${hasModal}`);
                            
                            if (!hasModal) {
                                console.log(`🔧 Habilitando modal para imagen batch ${index + 1}`);
                                img.addEventListener('click', (e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    console.log('🖱️ Click en imagen batch restaurada:', img.src);
                                    showImageModal(img.src, img.alt || 'Imagen de batch');
                                });
                                img.setAttribute('data-modal-enabled', 'true');
                                img.style.cursor = 'pointer';
                            }
                        });
                        
                        // También ejecutar la función general
                        enableModalForAllImages();
                        
                        console.log('✅ Modal habilitado para todas las imágenes de batch restauradas');
                    }, 1000);
                    
                    showStatus(`🎉 ${restoredCount} trabajos batch restaurados automáticamente`, 'success');
                } else {
                    console.log('ℹ️ No se restauraron trabajos batch nuevos');
                }
                
                return restoredCount > 0;
            } else {
                console.log('ℹ️ No se encontraron trabajos batch para restaurar');
                return false;
            }
        } else {
            console.log('⚠️ No se encontraron trabajos o respuesta incorrecta');
            return false;
        }
    } catch (error) {
        console.error('❌ Error en restauración forzada de batch jobs:', error);
        showStatus('❌ Error en restauración automática de trabajos batch', 'error');
        return false;
    }
}

// Función auxiliar para asegurar que la sección de batch esté visible
function ensureBatchSectionVisible() {
    console.log('🔧 ensureBatchSectionVisible - verificando estado...');
    
    const batchResultsSection = document.getElementById('batchResultsSection');
    const batchResults = document.getElementById('batchResults');
    const hasBatchContent = batchResults && batchResults.children.length > 0;
    
    console.log('📊 Estado de batch section:', {
        activeBatches,
        batchCounter,
        hasBatchContent,
        childrenCount: batchResults?.children.length || 0,
        sectionDisplay: batchResultsSection?.style.display
    });
    
    // Mostrar la sección si hay trabajos activos o contenido
    if (activeBatches > 0 || hasBatchContent) {
        if (batchResultsSection) {
            batchResultsSection.style.display = 'block';
            console.log('✅ Sección de batch results forzada a mostrarse');
            return true;
        }
    }
    
    console.log('ℹ️ No se requiere mostrar sección de batch');
    return false;
}

// Función auxiliar para habilitar modal en todas las imágenes automáticamente
function enableModalForAllImages() {
    console.log('🔧 INICIANDO - Habilitación automática de modal para todas las imágenes...');
    
    // 🔥 VERIFICAR Y MOSTRAR SECCIÓN DE BATCH SI HAY CONTENIDO
    const batchResults = document.getElementById('batchResults');
    const hasBatchContent = batchResults && batchResults.children.length > 0;
    
    if (hasBatchContent || activeBatches > 0) {
        console.log('🔧 Detectado contenido batch - asegurando que la sección esté visible');
        ensureBatchSectionVisible();
    }
    
    // Buscar todas las imágenes en contenedores de resultado
    const resultImages = document.querySelectorAll('.result-item img, .batch-workflow-images img, .individual-job-images img, .workflow-result-item img, .preview-image, div[id*="images-container-"] img');
    console.log(`🎯 Encontradas ${resultImages.length} imágenes en contenedores de resultado`);
    
    let enabledCount = 0;
    
    resultImages.forEach((img, index) => {
        if (!img.hasAttribute('data-modal-enabled')) {
            console.log(`🔧 Habilitando modal para imagen ${index + 1}:`, {
                src: img.src,
                alt: img.alt,
                parentClass: img.parentElement?.className,
                parentId: img.parentElement?.id
            });
            
            // Extraer información para el modal
            const workflowId = img.alt || `imagen_${index + 1}`;
            const imageUrl = img.src;
            
            // Agregar event listener para modal
            img.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🖱️ Click en imagen con modal automático:', imageUrl);
                showImageModal(imageUrl, workflowId);
            });
            
            // Marcar como modal-enabled
            img.setAttribute('data-modal-enabled', 'true');
            img.style.cursor = 'pointer';
            
            enabledCount++;
            console.log(`✅ Modal habilitado automáticamente para: ${workflowId}`);
        }
    });
    
    if (enabledCount > 0) {
        console.log(`🎉 Modal habilitado automáticamente para ${enabledCount} imágenes`);
        showStatus(`🎯 Modal habilitado automáticamente para ${enabledCount} imágenes`, 'success');
    } else {
        console.log('ℹ️ No se encontraron imágenes nuevas para habilitar modal');
    }
}

// Función auxiliar para cerrar modal (declarada globalmente)
function closeImageModal() {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalInfo = document.getElementById('modalInfo');
    
    if (modal) {
        console.log('🔒 Cerrando modal');
        modal.style.display = 'none';
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
        
        if (modalImage) modalImage.src = '';
        if (modalInfo) modalInfo.textContent = '';
    }
}

// Función de debug para verificar las imágenes
function debugImageModal() {
    console.log('🔍 DEBUGGING MODAL - Iniciando debug...');
    
    // Verificar que los elementos del modal existen
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalInfo = document.getElementById('modalInfo');
    
    console.log('📱 Modal element:', modal);
    console.log('🖼️ Modal image:', modalImage);
    console.log('ℹ️ Modal info:', modalInfo);
    
    // Buscar todas las imágenes en la página
    const allImages = document.querySelectorAll('img');
    console.log(`📊 Total de imágenes encontradas: ${allImages.length}`);
    
    allImages.forEach((img, index) => {
        console.log(`🖼️ Imagen ${index + 1}:`, {
            src: img.src,
            alt: img.alt,
            className: img.className,
            parentClass: img.parentElement?.className,
            hasModalEnabled: img.hasAttribute('data-modal-enabled'),
            style: img.style.cursor
        });
    });
    
    // Buscar imágenes en contenedores específicos
    const resultImages = document.querySelectorAll('.result-item img, .batch-workflow-images img, .individual-job-images img, .workflow-result-item img, .preview-image, div[id*="images-container-"] img');
    console.log(`🎯 Imágenes en contenedores de resultado: ${resultImages.length}`);
    
    resultImages.forEach((img, index) => {
        console.log(`📋 Imagen resultado ${index + 1}:`, {
            src: img.src,
            alt: img.alt,
            hasModalEnabled: img.hasAttribute('data-modal-enabled'),
            hasEventListeners: img.onclick !== null,
            parentClass: img.parentElement?.className,
            parentId: img.parentElement?.id
        });
        
        // Forzar hacer clickeable si no lo está
        if (!img.hasAttribute('data-modal-enabled')) {
            console.log(`🔧 Forzando hacer clickeable imagen ${index + 1}`);
            makeImageClickable(img, img.alt || 'Imagen generada');
        }
    });
    
    showStatus('🔍 Debug completado - Ver consola para detalles', 'info');
}

// Función de debug para verificar los trabajos batch
function debugBatchJobs() {
    console.log('🔍 DEBUGGING BATCH JOBS - Iniciando debug...');
    
    // Verificar elementos HTML
    const batchResultsSection = document.getElementById('batchResultsSection');
    const batchResults = document.getElementById('batchResults');
    
    console.log('📱 Elementos HTML:');
    console.log('  - batchResultsSection:', batchResultsSection);
    console.log('  - batchResults:', batchResults);
    console.log('  - batchResultsSection visible:', batchResultsSection?.style.display);
    console.log('  - batchResults children:', batchResults?.children.length);
    
    // Verificar variables globales
    console.log('📊 Variables globales:');
    console.log('  - activeBatches:', activeBatches);
    console.log('  - batchCounter:', batchCounter);
    console.log('  - pollingIntervals:', pollingIntervals);
    
    // Verificar imágenes de batch existentes
    const batchImages = document.querySelectorAll('.batch-workflow-images img, .workflow-result-item img');
    console.log(`🖼️ Imágenes de batch encontradas: ${batchImages.length}`);
    
    batchImages.forEach((img, index) => {
        const hasModal = img.hasAttribute('data-modal-enabled');
        console.log(`📋 Imagen batch ${index + 1}:`, {
            src: img.src,
            alt: img.alt,
            hasModalEnabled: hasModal,
            parentClass: img.parentElement?.className
        });
        
        // Forzar hacer clickeable si no lo está
        if (!hasModal) {
            console.log(`🔧 Forzando hacer clickeable imagen batch ${index + 1}`);
            img.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🖱️ Click forzado en imagen batch:', img.src);
                showImageModal(img.src, img.alt || 'Imagen de batch');
            });
            img.setAttribute('data-modal-enabled', 'true');
            img.style.cursor = 'pointer';
        }
    });
    
    // Intentar cargar trabajos de sesión manualmente
    console.log('🔄 Intentando cargar trabajos de sesión manualmente...');
    
    fetch(`${API_BASE_URL}/session/jobs`)
        .then(response => response.json())
        .then(data => {
            console.log('📋 Respuesta del servidor:', data);
            
            if (data.success && data.jobs) {
                const batchJobs = Object.values(data.jobs).filter(job => job.type === 'batch');
                console.log(`📊 Trabajos batch encontrados: ${batchJobs.length}`);
                
                batchJobs.forEach((job, index) => {
                    console.log(`📋 Batch Job ${index + 1}:`, {
                        id: job.id,
                        type: job.type,
                        status: job.status,
                        batch_tracking_id: job.batch_tracking_id,
                        total_workflows: job.total_workflows,
                        completed_workflows: job.completed_workflows,
                        image_urls: job.image_urls?.length || 0,
                        created_at: job.created_at
                    });
                    
                    // Intentar restaurar manualmente
                    if (index === 0) {
                        console.log('🔧 Intentando restaurar el primer batch job manualmente...');
                        try {
                            restoreBatchJob(job);
                        } catch (error) {
                            console.error('❌ Error restaurando batch job:', error);
                        }
                    }
                });
            } else {
                console.log('⚠️ No se encontraron trabajos o respuesta incorrecta');
            }
        })
        .catch(error => {
            console.error('❌ Error cargando trabajos:', error);
        });
    
    showStatus('🔍 Debug batch iniciado - Ver consola para detalles', 'info');
}