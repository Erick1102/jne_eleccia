/**
 * Funcionalidad de paginación para ELECCIA
 * Sistema de validación de inscripción de listas - JNE
 */

const paginationUtils = {
    /**
     * Inicializa la paginación en el elemento contenedor especificado
     * @param {string} tableId - ID de la tabla que contiene los datos
     * @param {string} paginationContainerId - ID del contenedor de paginación
     * @param {Object} options - Opciones adicionales de configuración
     */
    initPagination: function(tableId, paginationContainerId, options = {}) {
        const config = {
            itemsPerPage: 10,
            visiblePages: 5,
            ...options
        };

        const tableElement = document.getElementById(tableId);
        const paginationContainer = document.getElementById(paginationContainerId);
        
        if (!tableElement || !paginationContainer) {
            console.error('No se encontraron los elementos necesarios para la paginación');
            return;
        }
        
        const rows = tableElement.querySelectorAll('tbody tr');
        const totalItems = rows.length;
        const totalPages = Math.ceil(totalItems / config.itemsPerPage);
        
        // Ocultar todas las filas inicialmente
        rows.forEach(row => row.style.display = 'none');
        
        // Mostrar solo las filas de la primera página
        this.showPage(1, rows, config.itemsPerPage);
        
        // Generar los controles de paginación
        this.renderPaginationControls(paginationContainer, totalPages, 1, rows, config);
        
        // Actualizar el texto de información de paginación
        this.updatePaginationInfo(1, config.itemsPerPage, totalItems);
    },

    /**
     * Muestra las filas correspondientes a la página especificada
     */
    showPage: function(pageNumber, rows, itemsPerPage) {
        const startIndex = (pageNumber - 1) * itemsPerPage;
        const endIndex = startIndex + itemsPerPage;
        
        rows.forEach((row, index) => {
            row.style.display = (index >= startIndex && index < endIndex) ? '' : 'none';
        });
    },

    /**
     * Genera los controles de paginación
     */
    renderPaginationControls: function(container, totalPages, currentPage, rows, config) {
        container.innerHTML = '';
        
        if (totalPages <= 1) return;

        const nav = document.createElement('nav');
        nav.className = 'relative z-0 inline-flex rounded-md shadow-sm -space-x-px';
        nav.setAttribute('aria-label', 'Paginación');
        
        // Botón Anterior
        const prevButton = this.createPaginationButton('Anterior', currentPage > 1, () => {
            if (currentPage > 1) {
                this.goToPage(currentPage - 1, rows, config, container, totalPages);
            }
        }, true);
        nav.appendChild(prevButton);
        
        // Determinar qué páginas mostrar
        const pagesToShow = this.getPagesToShow(currentPage, totalPages, config.visiblePages);
        
        // Botones de páginas
        pagesToShow.forEach(pageNum => {
            if (pageNum === '...') {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700';
                ellipsis.textContent = '...';
                nav.appendChild(ellipsis);
            } else {
                const isCurrentPage = pageNum === currentPage;
                const pageButton = document.createElement('a');
                pageButton.href = '#';
                pageButton.className = isCurrentPage 
                    ? 'z-10 bg-jne-red border-jne-red text-white relative inline-flex items-center px-4 py-2 border text-sm font-medium'
                    : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50 relative inline-flex items-center px-4 py-2 border text-sm font-medium';
                
                if (isCurrentPage) {
                    pageButton.setAttribute('aria-current', 'page');
                }
                
                pageButton.textContent = pageNum;
                pageButton.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.goToPage(pageNum, rows, config, container, totalPages);
                });
                
                nav.appendChild(pageButton);
            }
        });
        
        // Botón Siguiente
        const nextButton = this.createPaginationButton('Siguiente', currentPage < totalPages, () => {
            if (currentPage < totalPages) {
                this.goToPage(currentPage + 1, rows, config, container, totalPages);
            }
        }, false);
        nav.appendChild(nextButton);
        
        container.appendChild(nav);
    },

    /**
     * Crea un botón de navegación (anterior/siguiente)
     */
    createPaginationButton: function(label, isEnabled, onClick, isPrevious) {
        const button = document.createElement('a');
        button.href = '#';
        button.className = `relative inline-flex items-center px-2 py-2 ${isPrevious ? 'rounded-l-md' : 'rounded-r-md'} border border-gray-300 bg-white text-sm font-medium ${isEnabled ? 'text-gray-500 hover:bg-gray-50' : 'text-gray-300 cursor-not-allowed'}`;
        
        const span = document.createElement('span');
        span.className = 'sr-only';
        span.textContent = label;
        button.appendChild(span);
        
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'h-5 w-5');
        svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        svg.setAttribute('viewBox', '0 0 20 20');
        svg.setAttribute('fill', 'currentColor');
        svg.setAttribute('aria-hidden', 'true');
        
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('fill-rule', 'evenodd');
        path.setAttribute('d', isPrevious 
            ? 'M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z'
            : 'M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z'
        );
        path.setAttribute('clip-rule', 'evenodd');
        svg.appendChild(path);
        button.appendChild(svg);
        
        if (isEnabled) {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                onClick();
            });
        }
        
        return button;
    },

    /**
     * Determina qué números de página mostrar en la paginación
     */
    getPagesToShow: function(currentPage, totalPages, visiblePages) {
        if (totalPages <= visiblePages) {
            return Array.from({ length: totalPages }, (_, i) => i + 1);
        }
        
        const pages = [1];
        let startPage = Math.max(2, currentPage - Math.floor(visiblePages / 2));
        let endPage = Math.min(totalPages - 1, startPage + visiblePages - 3);
        
        if (startPage === 2) {
            endPage = Math.min(totalPages - 1, visiblePages - 1);
        }
        
        if (endPage === totalPages - 1 && endPage - startPage < visiblePages - 3) {
            startPage = Math.max(2, totalPages - visiblePages + 2);
        }
        
        if (startPage > 2) pages.push('...');
        for (let i = startPage; i <= endPage; i++) pages.push(i);
        if (endPage < totalPages - 1) pages.push('...');
        if (totalPages > 1) pages.push(totalPages);
        
        return pages;
    },

    /**
     * Navega a la página especificada
     */
    goToPage: function(pageNumber, rows, config, container, totalPages) {
        this.showPage(pageNumber, rows, config.itemsPerPage);
        this.renderPaginationControls(container, totalPages, pageNumber, rows, config);
        this.updatePaginationInfo(pageNumber, config.itemsPerPage, rows.length);
        
        // Desplazarse al inicio de la tabla
        const tableElement = rows[0].closest('table');
        if (tableElement) {
            tableElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    },

    /**
     * Actualiza la información de paginación
     */
    updatePaginationInfo: function(currentPage, itemsPerPage, totalItems) {
        const infoElement = document.querySelector('.pagination-info');
        if (!infoElement) return;
        
        const start = Math.min(((currentPage - 1) * itemsPerPage) + 1, totalItems);
        const end = Math.min(start + itemsPerPage - 1, totalItems);
        
        infoElement.innerHTML = `Mostrando <span class="font-medium">${start}</span> a <span class="font-medium">${end}</span> de <span class="font-medium">${totalItems}</span> resultados`;
    }
};

// Exportar para uso global
window.paginationUtils = paginationUtils;