function initTabs() {
    const tabButtons = document.querySelectorAll('[data-tabs-target]');
    const tabContents = document.querySelectorAll('[role="tabpanel"]');

    if (tabButtons.length === 0 || tabContents.length === 0) return;

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const target = document.querySelector(button.dataset.tabsTarget);

            tabContents.forEach(content => content.classList.add('hidden'));

            tabButtons.forEach(btn => {
                btn.classList.remove('text-jne-red', 'border-jne-red', 'active');
                btn.classList.add('text-gray-500', 'border-transparent');
                btn.setAttribute('aria-selected', 'false');
            });

            button.classList.remove('text-gray-500', 'border-transparent');
            button.classList.add('text-jne-red', 'border-jne-red', 'active');
            button.setAttribute('aria-selected', 'true');

            target.classList.remove('hidden');
        });
    });
}

function initAccordions() {
    const accordionHeaders = document.querySelectorAll('.accordion-header');
    
    accordionHeaders.forEach(header => {
        header.addEventListener('click', () => {
            // Get the target content element
            const targetId = header.getAttribute('data-target');
            const content = document.getElementById(targetId);
            
            // Toggle the content visibility
            content.classList.toggle('hidden');
            
            // Rotate the arrow icon
            const icon = header.querySelector('.accordion-icon');
            icon.classList.toggle('rotate-180');
        });
    });
}

// Agregar estilos de animación
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); }
        to { transform: translateX(0); }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); }
        to { transform: translateX(100%); }
    }
    
    .animate-fade-in {
        animation: fadeIn 0.3s ease-in-out;
    }
    
    .animate-slide-in {
        animation: slideIn 0.3s ease-in-out;
    }
    
    .animate-slide-out {
        animation: slideOut 0.3s ease-in-out;
    }
`;
document.head.appendChild(style);

// Funciones para el manejo de la generación de resolución
function mostrarConfirmacionGenerarResolucion() {
    const modal = document.getElementById('modalConfirmacion');
    modal.classList.remove('hidden');
    modal.classList.add('animate-fade-in');
}

function cerrarModal() {
    const modal = document.getElementById('modalConfirmacion');
    modal.classList.add('hidden');
    modal.classList.remove('animate-fade-in');
}

function mostrarToastExito() {
    const toast = document.getElementById('toastExito');
    toast.classList.remove('hidden');
    toast.classList.add('animate-slide-in');
    
    setTimeout(() => {
        toast.classList.add('animate-slide-out');
        setTimeout(() => {
            toast.classList.add('hidden');
            toast.classList.remove('animate-slide-in', 'animate-slide-out');
        }, 500);
    }, 3000);
}

function mostrarToastError(mensaje) {
    const toast = document.getElementById('toastError');
    const mensajeError = document.getElementById('mensajeError');
    mensajeError.textContent = mensaje;
    
    toast.classList.remove('hidden');
    toast.classList.add('animate-slide-in');
    
    setTimeout(() => {
        toast.classList.add('animate-slide-out');
        setTimeout(() => {
            toast.classList.add('hidden');
            toast.classList.remove('animate-slide-in', 'animate-slide-out');
        }, 500);
    }, 3000);
}

async function generarResolucion() {
    try {
        const normativasSeleccionadas = obtenerNormativasSeleccionadas();
        
        // Mostrar indicador de carga
        const botonConfirmar = document.getElementById('btnConfirmarNormativas');
        botonConfirmar.disabled = true;
        botonConfirmar.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Generando...
        `;

        const numeroExpediente = "{{ nombre_expediente }}";
        
        if (!numeroExpediente) {
            throw new Error("No se encontró el número del expediente");
        }

        const response = await fetch(`/generar_resolucion?nombre_expediente=${encodeURIComponent(numeroExpediente)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                normativas: normativasSeleccionadas
            })
        });
        
        if (response.ok) {
            cerrarModalNormativas();
            mostrarToastExito();
            setTimeout(() => {
                window.location.href = '/listado_procesados';
            }, 1000);
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Error al generar la resolución');
        }
    } catch (error) {
        console.error('Error en generarResolucion:', error);
        mostrarToastError(error.message);
    } finally {
        const botonConfirmar = document.getElementById('btnConfirmarNormativas');
        botonConfirmar.disabled = false;
        botonConfirmar.innerHTML = 'Confirmar y Generar Resolución';
    }
}

// Función para mostrar el modal de normativas
function mostrarModalNormativas() {
    const modal = document.getElementById('modalNormativas');
    modal.classList.remove('hidden');
    modal.classList.add('animate-fade-in');
}

// Función para cerrar el modal de normativas
function cerrarModalNormativas() {
    const modal = document.getElementById('modalNormativas');
    modal.classList.add('hidden');
    modal.classList.remove('animate-fade-in');
}

// Función para manejar la selección de normativas
function initNormativasTabs() {
    const tabButtons = document.querySelectorAll('#normativas-tabs button');
    const tabContents = document.querySelectorAll('[role="tabpanel"]');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const target = document.querySelector(button.dataset.tabsTarget);

            tabContents.forEach(content => content.classList.add('hidden'));
            tabButtons.forEach(btn => {
                btn.classList.remove('text-jne-red', 'border-jne-red', 'active');
                btn.classList.add('text-gray-500', 'border-transparent');
                btn.setAttribute('aria-selected', 'false');
            });

            button.classList.remove('text-gray-500', 'border-transparent');
            button.classList.add('text-jne-red', 'border-jne-red', 'active');
            button.setAttribute('aria-selected', 'true');

            target.classList.remove('hidden');
        });
    });
}

// Función para manejar la selección de normativas y artículos
function initNormativasCheckboxes() {
    // Manejar selección de normativa completa
    document.querySelectorAll('input[data-tipo="ley"], input[data-tipo="reglamento"]').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const normativaId = e.target.dataset.normativaId;
            const isChecked = e.target.checked;
            
            // Seleccionar/deseleccionar todos los artículos de esta normativa
            document.querySelectorAll(`input[data-normativa-id="${normativaId}"]`).forEach(artCheckbox => {
                artCheckbox.checked = isChecked;
            });
        });
    });

    // Manejar selección de artículos individuales
    document.querySelectorAll('input[data-articulo-id]').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const normativaId = e.target.dataset.normativaId;
            const normativaCheckbox = document.querySelector(`input[data-normativa-id="${normativaId}"][data-tipo]`);
            
            // Verificar si todos los artículos están seleccionados
            const articulos = document.querySelectorAll(`input[data-normativa-id="${normativaId}"][data-articulo-id]`);
            const todosSeleccionados = Array.from(articulos).every(art => art.checked);
            
            normativaCheckbox.checked = todosSeleccionados;
        });
    });
}

// Función para obtener las normativas seleccionadas
function obtenerNormativasSeleccionadas() {
    const normativasSeleccionadas = {
        leyes: [],
        reglamentos: []
    };

    // Obtener leyes seleccionadas
    document.querySelectorAll('input[data-tipo="ley"]:checked').forEach(checkbox => {
        const normativaId = checkbox.dataset.normativaId;
        const articulos = Array.from(document.querySelectorAll(`input[data-normativa-id="${normativaId}"][data-articulo-id]:checked`))
            .map(art => art.dataset.articuloId);
        
        normativasSeleccionadas.leyes.push({
            nombre: normativaId,
            articulos: articulos
        });
    });

    // Obtener reglamentos seleccionados
    document.querySelectorAll('input[data-tipo="reglamento"]:checked').forEach(checkbox => {
        const normativaId = checkbox.dataset.normativaId;
        const articulos = Array.from(document.querySelectorAll(`input[data-normativa-id="${normativaId}"][data-articulo-id]:checked`))
            .map(art => art.dataset.articuloId);
        
        normativasSeleccionadas.reglamentos.push({
            nombre: normativaId,
            articulos: articulos
        });
    });

    return normativasSeleccionadas;
}

// Inicialización cuando el documento está listo
document.addEventListener('DOMContentLoaded', () => {
    console.log('Documento cargado, inicializando componentes...');
    
    // Inicializar tabs y accordions
    initTabs();
    initAccordions();

    // Inicializar tabs y checkboxes de normativas
    initNormativasTabs();
    initNormativasCheckboxes();

    // Asignar eventos a los botones
    const btnGenerarResolucion = document.getElementById('btnGenerarResolucion');
    const btnCancelar = document.getElementById('btnCancelar');
    const btnConfirmar = document.getElementById('btnConfirmar');
    const btnVerInforme = document.getElementById('btnVerInforme');
    const btnCerrarInforme = document.getElementById('btnCerrarInforme');
    const btnDescargarInforme = document.getElementById('btnDescargarInforme');
    const btnCerrarNormativas = document.getElementById('btnCerrarNormativas');
    const btnCancelarNormativas = document.getElementById('btnCancelarNormativas');
    const btnConfirmarNormativas = document.getElementById('btnConfirmarNormativas');

    console.log('Botones encontrados:', {
        btnGenerarResolucion: !!btnGenerarResolucion,
        btnCancelar: !!btnCancelar,
        btnConfirmar: !!btnConfirmar,
        btnVerInforme: !!btnVerInforme,
        btnCerrarInforme: !!btnCerrarInforme,
        btnDescargarInforme: !!btnDescargarInforme,
        btnCerrarNormativas: !!btnCerrarNormativas,
        btnCancelarNormativas: !!btnCancelarNormativas,
        btnConfirmarNormativas: !!btnConfirmarNormativas
    });

    if (btnGenerarResolucion) {
        btnGenerarResolucion.addEventListener('click', mostrarModalNormativas);
    }
    if (btnCancelar) {
        btnCancelar.addEventListener('click', cerrarModal);
    }
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', () => {
            console.log('Botón confirmar clickeado');
            generarResolucion();
        });
    }
    if (btnVerInforme) {
        btnVerInforme.addEventListener('click', () => {
            console.log('Botón ver informe clickeado');
            mostrarModalInforme();
        });
    }
    if (btnCerrarInforme) {
        btnCerrarInforme.addEventListener('click', cerrarModalInforme);
    }
    if (btnDescargarInforme) {
        btnDescargarInforme.addEventListener('click', () => {
            console.log('Botón descargar informe clickeado');
            generarPDF();
        });
    }
    if (btnCerrarNormativas) {
        btnCerrarNormativas.addEventListener('click', cerrarModalNormativas);
    }
    if (btnCancelarNormativas) {
        btnCancelarNormativas.addEventListener('click', cerrarModalNormativas);
    }
    if (btnConfirmarNormativas) {
        btnConfirmarNormativas.addEventListener('click', generarResolucion);
    }
});

function mostrarModalInforme() {
    const modal = document.getElementById('modalInforme');
    modal.classList.remove('hidden');
    modal.classList.add('animate-fade-in');
}

function cerrarModalInforme() {
    const modal = document.getElementById('modalInforme');
    modal.classList.add('hidden');
    modal.classList.remove('animate-fade-in');
}

async function generarPDF() {
    try {
        // Mostrar indicador de carga
        const btnDescargar = document.getElementById('btnDescargarInforme');
        const originalContent = btnDescargar.innerHTML;
        btnDescargar.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Generando PDF...
        `;

        // Obtener el contenido del modal
        const modal = document.getElementById('modalInforme');
        const content = modal.querySelector('.relative');

        // Crear un contenedor temporal para el PDF
        const tempContainer = document.createElement('div');
        tempContainer.style.width = '210mm'; // Ancho A4
        tempContainer.style.padding = '20mm';
        tempContainer.style.backgroundColor = '#ffffff';
        
        // Clonar el contenido
        const contentClone = content.cloneNode(true);
        
        // Ajustar estilos del contenido clonado
        const allElements = contentClone.querySelectorAll('*');
        allElements.forEach(el => {
            if (el.style) {
                el.style.maxHeight = 'none';
                el.style.height = 'auto';
                el.style.overflow = 'visible';
                el.style.pageBreakInside = 'avoid';
            }
        });

        // Ajustar contenedores específicos
        const containers = contentClone.querySelectorAll('.max-w-5xl, .max-w-4xl, .max-w-7xl');
        containers.forEach(container => {
            container.style.maxWidth = '100%';
            container.style.width = '100%';
        });

        // Agregar el contenido clonado al contenedor temporal
        tempContainer.appendChild(contentClone);
        document.body.appendChild(tempContainer);

        // Configuración para html2pdf
        const opt = {
            margin: 0,
            filename: `informe_{{ nombre_expediente }}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { 
                scale: 2,
                useCORS: true,
                letterRendering: true,
                scrollY: 0,
                windowHeight: tempContainer.scrollHeight,
                height: tempContainer.scrollHeight,
                onclone: function(clonedDoc) {
                    const elements = clonedDoc.querySelectorAll('*');
                    elements.forEach(el => {
                        if (el.style) {
                            el.style.overflow = 'visible';
                            el.style.height = 'auto';
                            el.style.maxHeight = 'none';
                            el.style.pageBreakInside = 'avoid';
                        }
                    });
                }
            },
            jsPDF: { 
                unit: 'mm', 
                format: 'a4', 
                orientation: 'portrait',
                compress: true
            },
            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
        };

        // Generar el PDF
        await html2pdf().set(opt).from(tempContainer).save();
        
        // Limpiar
        document.body.removeChild(tempContainer);
        
        // Restaurar el botón
        btnDescargar.innerHTML = originalContent;
    } catch (error) {
        console.error('Error al generar el PDF:', error);
        mostrarToastError('Error al generar el PDF');
    }
}

// Agregar variable global para almacenar cambios temporales
let cambiosTemporales = new Map();

function abrirModalEditarRequisito(nombre, estado, observacion, id_estado_requisito) {
    const modal = document.getElementById('modalEditarRequisito');
    const nombreRequisito = document.getElementById('nombreRequisito');
    const estadoRequisito = document.getElementById('estadoRequisito');
    const observacionRequisito = document.getElementById('observacionRequisito');
    const idEstadoRequisito = document.getElementById('id_estado_requisito');
    
    // Si hay cambios temporales, usarlos
    if (cambiosTemporales.has(id_estado_requisito)) {
        const cambios = cambiosTemporales.get(id_estado_requisito);
        estadoRequisito.value = cambios.estado;
        observacionRequisito.value = cambios.observacion || '';
    } else {
        estadoRequisito.value = estado;
        observacionRequisito.value = observacion || '';
    }
    
    nombreRequisito.textContent = nombre;
    idEstadoRequisito.value = id_estado_requisito;
    
    modal.classList.remove('hidden');
    modal.classList.add('animate-fade-in');
}

function cerrarModalEditarRequisito() {
    const modal = document.getElementById('modalEditarRequisito');
    modal.classList.add('hidden');
    modal.classList.remove('animate-fade-in');
}

function mostrarToastExitoEdicion() {
    const toast = document.getElementById('toastExitoEdicion');
    toast.classList.remove('hidden');
    toast.classList.add('animate-slide-in');
    
    setTimeout(() => {
        toast.classList.add('animate-slide-out');
        setTimeout(() => {
            toast.classList.add('hidden');
            toast.classList.remove('animate-slide-in', 'animate-slide-out');
        }, 500);
    }, 3000);
}

function mostrarToastErrorEdicion(mensaje) {
    const toast = document.getElementById('toastErrorEdicion');
    const mensajeError = document.getElementById('mensajeErrorEdicion');
    mensajeError.textContent = mensaje;
    
    toast.classList.remove('hidden');
    toast.classList.add('animate-slide-in');
    
    setTimeout(() => {
        toast.classList.add('animate-slide-out');
        setTimeout(() => {
            toast.classList.add('hidden');
            toast.classList.remove('animate-slide-in', 'animate-slide-out');
        }, 500);
    }, 3000);
}

// Inicialización cuando el documento está listo
document.addEventListener('DOMContentLoaded', () => {
    // ... existing code ...
    
    // Agregar eventos para el modal de edición de requisito
    const btnCerrarEditarRequisito = document.getElementById('btnCerrarEditarRequisito');
    const btnCancelarEditarRequisito = document.getElementById('btnCancelarEditarRequisito');
    const formEditarRequisito = document.getElementById('formEditarRequisito');
    
    if (btnCerrarEditarRequisito) {
        btnCerrarEditarRequisito.addEventListener('click', cerrarModalEditarRequisito);
    }
    
    if (btnCancelarEditarRequisito) {
        btnCancelarEditarRequisito.addEventListener('click', cerrarModalEditarRequisito);
    }
    
    if (formEditarRequisito) {
        formEditarRequisito.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(formEditarRequisito);
            const id_estado_requisito = formData.get('id_estado_requisito');
            const estado = formData.get('estado');
            const observacion = formData.get('observacion');
            
            // Guardar cambios temporalmente
            cambiosTemporales.set(id_estado_requisito, {
                estado: estado,
                observacion: observacion
            });
            
            // Actualizar la vista
            const requisitoElement = document.querySelector(`[data-requisito-id="${id_estado_requisito}"]`);
            if (requisitoElement) {
                const estadoBadge = requisitoElement.querySelector('.text-xs');
                let estadoColor, estadoTexto;
                
                if (estado === 'CUMPLE') {
                    estadoColor = 'green';
                    estadoTexto = 'Cumple';
                } else if (estado === 'NO_CUMPLE') {
                    estadoColor = 'red';
                    estadoTexto = 'No Cumple';
                } else if (estado === 'ALERTA') {
                    estadoColor = 'amber';
                    estadoTexto = 'Alerta';
                }
                
                estadoBadge.className = `text-xs bg-${estadoColor}-100 text-${estadoColor}-800 px-2 py-1 rounded-full`;
                estadoBadge.textContent = estadoTexto;
                
                // Actualizar observación si existe
                const observacionElement = requisitoElement.querySelector(`.bg-${estadoColor}-100`);
                if (observacionElement && observacion) {
                    observacionElement.innerHTML = `<p><strong>Observación:</strong> ${observacion}</p>`;
                }
            }
            
            cerrarModalEditarRequisito();
            mostrarToastExitoEdicion();
        });
    }
});

// Agregar variable global para el estado de edición
let modoEdicion = false;

// Función para actualizar la interfaz según el modo de edición
function actualizarInterfazEdicion() {
    const btnHabilitarEdicion = document.getElementById('btnHabilitarEdicion');
    const btnCancelarEdicion = document.getElementById('btnCancelarEdicion');
    const botonesEditar = document.querySelectorAll('button[onclick^="abrirModalEditarRequisito"]');
    
    if (modoEdicion) {
        btnHabilitarEdicion.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            Guardar Cambios
        `;
        btnHabilitarEdicion.classList.remove('bg-jne-red', 'hover:bg-red-700');
        btnHabilitarEdicion.classList.add('bg-green-600', 'hover:bg-green-700');
        btnCancelarEdicion.classList.remove('hidden');
        
        // Mostrar botones de edición
        botonesEditar.forEach(btn => {
            btn.classList.remove('hidden');
        });
    } else {
        btnHabilitarEdicion.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Habilitar Edición
        `;
        btnHabilitarEdicion.classList.remove('bg-green-600', 'hover:bg-green-700');
        btnHabilitarEdicion.classList.add('bg-jne-red', 'hover:bg-red-700');
        btnCancelarEdicion.classList.add('hidden');
        
        // Ocultar botones de edición
        botonesEditar.forEach(btn => {
            btn.classList.add('hidden');
        });
    }
}

// Función para cancelar la edición
function cancelarEdicion() {
    // Restaurar los valores originales
    for (const [id_estado_requisito, cambios] of cambiosTemporales) {
        const requisitoElement = document.querySelector(`[data-requisito-id="${id_estado_requisito}"]`);
        if (requisitoElement) {
            // Restaurar estado original
            const estadoBadge = requisitoElement.querySelector('.text-xs');
            const estadoOriginal = requisitoElement.getAttribute('data-estado-original');
            let estadoColor, estadoTexto;
            
            if (estadoOriginal === 'CUMPLE') {
                estadoColor = 'green';
                estadoTexto = 'Cumple';
            } else if (estadoOriginal === 'NO_CUMPLE') {
                estadoColor = 'red';
                estadoTexto = 'No Cumple';
            } else if (estadoOriginal === 'ALERTA') {
                estadoColor = 'amber';
                estadoTexto = 'Alerta';
            }
            
            estadoBadge.className = `text-xs bg-${estadoColor}-100 text-${estadoColor}-800 px-2 py-1 rounded-full`;
            estadoBadge.textContent = estadoTexto;
            
            // Restaurar observación original
            const observacionElement = requisitoElement.querySelector(`.bg-${estadoColor}-100`);
            const observacionOriginal = requisitoElement.getAttribute('data-observacion-original');
            if (observacionElement && observacionOriginal) {
                observacionElement.innerHTML = `<p><strong>Observación:</strong> ${observacionOriginal}</p>`;
            }
        }
    }
    
    // Limpiar cambios temporales
    cambiosTemporales.clear();
    
    // Deshabilitar modo edición
    modoEdicion = false;
    actualizarInterfazEdicion();
}

// Inicialización cuando el documento está listo
document.addEventListener('DOMContentLoaded', () => {
    // ... existing code ...
    
    // Agregar evento para el botón de habilitar edición
    const btnHabilitarEdicion = document.getElementById('btnHabilitarEdicion');
    const btnCancelarEdicion = document.getElementById('btnCancelarEdicion');
    
    if (btnHabilitarEdicion) {
        btnHabilitarEdicion.addEventListener('click', () => {
            if (modoEdicion) {
                guardarCambios();
            } else {
                // Guardar estados originales antes de habilitar edición
                document.querySelectorAll('[data-requisito-id]').forEach(element => {
                    const id = element.getAttribute('data-requisito-id');
                    const estadoBadge = element.querySelector('.text-xs');
                    const observacionElement = element.querySelector('[class*="bg-"]');
                    
                    element.setAttribute('data-estado-original', estadoBadge.textContent.trim());
                    if (observacionElement) {
                        element.setAttribute('data-observacion-original', observacionElement.textContent.replace('Observación:', '').trim());
                    }
                });
                
                modoEdicion = true;
                actualizarInterfazEdicion();
            }
        });
    }
    
    if (btnCancelarEdicion) {
        btnCancelarEdicion.addEventListener('click', cancelarEdicion);
    }
    
    // Inicializar la interfaz
    actualizarInterfazEdicion();
});

// Función para guardar cambios usando AJAX
async function guardarCambios() {
    try {
        const formData = new FormData();
        formData.append('id_expediente', '{{ id_expediente }}');
        
        // Agregar los requisitos editados al formData
        for (const [id_estado_requisito, cambios] of cambiosTemporales) {
            formData.append(`requisito_${id_estado_requisito}`, cambios.estado);
            if (cambios.observacion) {
                formData.append(`observacion_${id_estado_requisito}`, cambios.observacion);
            }
        }
        
        // Mostrar indicador de carga
        const btnHabilitarEdicion = document.getElementById('btnHabilitarEdicion');
        const originalContent = btnHabilitarEdicion.innerHTML;
        btnHabilitarEdicion.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Guardando...
        `;
        btnHabilitarEdicion.disabled = true;
        
        // Enviar la solicitud
        const response = await fetch('/guardar_cambios_requisitos', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // Obtener los nuevos datos
            const responseData = await response.json();
            
            if (responseData) {
                // Actualizar contadores en el Resumen de Validación
                const requisitosCompletos = document.getElementById('requisitosCompletos');
                const requisitosFaltantes = document.getElementById('requisitosFaltantes');
                const totalRequisitos = document.querySelector('.text-3xl.font-bold.text-blue-700');
                const porcentajeCumplimiento = document.querySelector('.text-3xl.font-bold.text-yellow-700');
                
                if (requisitosCompletos) requisitosCompletos.textContent = responseData.requisitos_cumplidos;
                if (requisitosFaltantes) requisitosFaltantes.textContent = responseData.requisitos_faltantes;
                if (totalRequisitos) totalRequisitos.textContent = responseData.total_requisitos;
                if (porcentajeCumplimiento) porcentajeCumplimiento.textContent = `${responseData.porcentaje_cumplimiento}%`;
                
                // Actualizar mensaje de alerta en el Resumen de Validación
                const mensajeAlerta = document.querySelector('.text-sm.text-yellow-700 strong');
                if (mensajeAlerta) {
                    const mensaje = responseData.requisitos_faltantes > 0 
                        ? `Faltan ${responseData.requisitos_faltantes} requisitos por cumplir.`
                        : "Todos los requisitos aplicables han sido cumplidos satisfactoriamente.";
                    mensajeAlerta.nextSibling.textContent = mensaje;
                }

                // Actualizar Recomendación de Resolución
                const motivoResolucion = document.getElementById('motivoResolucion');
                const tipoResolucion = document.querySelector('.font-semibold.text-jne-red');
                
                if (motivoResolucion) motivoResolucion.textContent = responseData.motivo_resolucion;
                if (tipoResolucion) tipoResolucion.textContent = responseData.tipo_resolucion;

                // Actualizar la vista de los requisitos
                for (const [id_estado_requisito, cambios] of cambiosTemporales) {
                    const requisitoElement = document.querySelector(`[data-requisito-id="${id_estado_requisito}"]`);
                    if (requisitoElement) {
                        // Actualizar estado
                        const estadoBadge = requisitoElement.querySelector('.text-xs');
                        let estadoColor, estadoTexto;
                        
                        if (cambios.estado === 'CUMPLE') {
                            estadoColor = 'green';
                            estadoTexto = 'Cumple';
                        } else if (cambios.estado === 'NO_CUMPLE') {
                            estadoColor = 'red';
                            estadoTexto = 'No Cumple';
                        } else if (cambios.estado === 'ALERTA') {
                            estadoColor = 'amber';
                            estadoTexto = 'Alerta';
                        }
                        
                        estadoBadge.className = `text-xs bg-${estadoColor}-100 text-${estadoColor}-800 px-2 py-1 rounded-full`;
                        estadoBadge.textContent = estadoTexto;
                        
                        // Actualizar observación
                        const observacionElement = requisitoElement.querySelector(`.bg-${estadoColor}-100`);
                        if (observacionElement && cambios.observacion) {
                            observacionElement.innerHTML = `<p><strong>Observación:</strong> ${cambios.observacion}</p>`;
                        }

                        // Actualizar el estado del candidato si es un requisito de candidato
                        const candidatoContainer = requisitoElement.closest('.bg-white.rounded-lg.shadow-md.p-4');
                        if (candidatoContainer) {
                            const candidatoBadge = candidatoContainer.querySelector('.inline-flex.items-center.px-3.py-1.rounded-full');
                            if (candidatoBadge) {
                                const todosLosRequisitos = Array.from(candidatoContainer.querySelectorAll('[data-requisito-id]'))
                                    .map(req => req.querySelector('.text-xs').textContent.trim() === 'Cumple');
                                const todosCumplen = todosLosRequisitos.every(cumple => cumple);
                                
                                candidatoBadge.className = `inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${todosCumplen ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`;
                                candidatoBadge.innerHTML = todosCumplen ? 
                                    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>Cumple' :
                                    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>No Cumple';
                            }
                        }
                    }
                }
            }
            
            // Limpiar cambios temporales
            cambiosTemporales.clear();
            
            // Deshabilitar modo edición
            modoEdicion = false;
            actualizarInterfazEdicion();
            
            // Mostrar mensaje de éxito
            mostrarToastExitoEdicion();
        } else {
            throw new Error('Error al guardar los cambios');
        }
        
    } catch (error) {
        console.error('Error:', error);
        mostrarToastErrorEdicion('Error al guardar los cambios');
    } finally {
        // Restaurar el botón
        const btnHabilitarEdicion = document.getElementById('btnHabilitarEdicion');
        btnHabilitarEdicion.innerHTML = originalContent;
        btnHabilitarEdicion.disabled = false;
    }
}