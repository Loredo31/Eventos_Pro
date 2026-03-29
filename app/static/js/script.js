// ==================== VARIABLES GLOBALES ====================
let seleccionados = []; // Array de objetos {id, nombre, precio}
let currentCotizacion = {
    tipo: null,   // 'paquete' o 'servicios'
    id: null,     // id del paquete o array de ids de servicios
    nombre: null
};

// ==================== FUNCIONES AUXILIARES ====================
function getAccessToken() {
    return getCookie('access_token');
}

function mostrarModalCotizacion(tipo, ids, nombre) {
    const form = document.getElementById('cotizacionForm');
    if (!form) {
        console.error('Formulario no encontrado');
        return;
    }

    // Resetear formulario
    form.reset();
    // Limpiar cualquier mensaje previo (ya no se usa, pero por si acaso)
    const mensajeDiv = document.getElementById('cotizacion-mensaje');
    if (mensajeDiv) mensajeDiv.innerHTML = '';

    currentCotizacion.tipo = tipo;
    currentCotizacion.id = ids;
    currentCotizacion.nombre = nombre;

    document.getElementById('tipo_solicitud').value = tipo;
    if (tipo === 'paquete') {
        document.getElementById('paquete_id').value = ids;
        document.getElementById('servicios_ids').value = '';
    } else if (tipo === 'servicios') {
        document.getElementById('paquete_id').value = '';
        document.getElementById('servicios_ids').value = JSON.stringify(ids);
    }

    document.getElementById('cotizacionModal').style.display = 'block';
}

function actualizarListaSeleccionados() {
    const listaSection = document.getElementById('lista-seleccionados');
    const seleccionadosContainer = document.getElementById('seleccionados-container');
    
    if (!listaSection || !seleccionadosContainer) return;
    
    if (seleccionados.length === 0) {
        listaSection.classList.add('hidden');
        return;
    }

    listaSection.classList.remove('hidden');
    let html = '';
    let total = 0;
    seleccionados.forEach(item => {
        html += `
            <div class="item-seleccionado">
                <span class="nombre">${item.nombre}</span>
                <span class="precio">$${item.precio} MXN</span>
            </div>
        `;
        total += item.precio;
    });
    html += `<div class="item-seleccionado total"><strong>Total: $${total} MXN</strong></div>`;
    seleccionadosContainer.innerHTML = html;
}

// ==================== TOAST NOTIFICATION ====================
function showToast(message, isSuccess) {
    const toast = document.getElementById('toast-notification');
    if (!toast) {
        // Fallback: alert si no existe el toast (por si acaso)
        alert(message);
        return;
    }
    const icon = document.getElementById('toast-icon');
    const messageEl = document.getElementById('toast-message');
    
    // Resetear clases
    toast.classList.remove('success', 'error', 'hidden');
    
    if (isSuccess) {
        toast.classList.add('success');
        if (icon) icon.textContent = '✓';
    } else {
        toast.classList.add('error');
        if (icon) icon.textContent = '✗';
    }
    
    if (messageEl) messageEl.textContent = message;
    toast.classList.remove('hidden');
    
    // Ocultar después de 2 segundos
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 2000);
}

// ==================== ENVÍO DE COTIZACIÓN (con toast) ====================
async function enviarCotizacion(data) {
    const token = getAccessToken();
    if (!token) {
        showToast('Debes iniciar sesión para cotizar', false);
        return false;
    }

    try {
        const response = await fetch('/api/eventos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (response.ok) {
            showToast('✅ Solicitud enviada correctamente. Pronto un asesor se comunicará contigo.', true);
            
            // Limpiar lista de servicios seleccionados si corresponde
            if (currentCotizacion.tipo === 'servicios') {
                seleccionados = [];
                actualizarListaSeleccionados();
            }
            
            // Cerrar el modal de cotización
            document.getElementById('cotizacionModal').style.display = 'none';
            return true;
        } else {
            const errorMsg = result.error || 'No se pudo enviar la solicitud';
            showToast(`❌ Error: ${errorMsg}`, false);
            return false;
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('❌ Error de conexión. Intenta de nuevo.', false);
        return false;
    }
}

// ==================== DOMContentLoaded ====================
document.addEventListener('DOMContentLoaded', function() {
    // === CHATBOT ===
    const btnChat = document.getElementById('btnChat');
    const chatbot = document.getElementById('chatbot');
    const chatClose = document.getElementById('chatClose');
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btnSendMessage');
    const messagesDiv = document.getElementById('chat-messages');

    if (btnChat) {
        btnChat.addEventListener('click', function() {
            chatbot.classList.remove('hidden');
        });
    }
    if (chatClose) {
        chatClose.addEventListener('click', function() {
            chatbot.classList.add('hidden');
        });
    }
    function sendMessage() {
        const message = chatInput.value.trim();
        if (message === '') return;
        addMessage(message, 'user');
        chatInput.value = '';
        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            if (data.respuesta) addMessage(data.respuesta, 'bot');
            else if (data.error) addMessage('Error: ' + data.error, 'bot');
        })
        .catch(error => addMessage('Error de conexión', 'bot'));
    }
    function addMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
        msgDiv.textContent = text;
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    if (btnSend) btnSend.addEventListener('click', sendMessage);
    if (chatInput) chatInput.addEventListener('keypress', function(e) { if (e.key === 'Enter') sendMessage(); });

    // === SERVICIOS: LISTA DE SELECCIONADOS ===
    const btnCancelar = document.getElementById('btnCancelar');
    const btnCotizarLista = document.getElementById('btnCotizarLista');

    // Si estamos en la página de servicios, inicializar eventos
    if (document.getElementById('servicios-container')) {
        // Agregar servicio
        document.querySelectorAll('.btn-agregar').forEach(btn => {
            btn.addEventListener('click', function(e) {
                const card = e.target.closest('.servicio-card');
                if (!card) return;
                const id = card.dataset.servicioId;
                const nombre = card.dataset.servicioNombre;
                const precio = parseInt(card.dataset.servicioPrecio);
                if (!seleccionados.some(s => s.id === id)) {
                    seleccionados.push({ id, nombre, precio });
                    actualizarListaSeleccionados();
                } else {
                    showToast('Este servicio ya está en tu lista', false);
                }
            });
        });

        // Cancelar selección
        if (btnCancelar) {
            btnCancelar.addEventListener('click', function() {
                seleccionados = [];
                actualizarListaSeleccionados();
            });
        }

        // Cotizar lista
        if (btnCotizarLista) {
            btnCotizarLista.addEventListener('click', function() {
                if (seleccionados.length === 0) {
                    showToast('No hay servicios seleccionados', false);
                    return;
                }
                const ids = seleccionados.map(s => parseInt(s.id));
                const nombres = seleccionados.map(s => s.nombre).join(', ');
                mostrarModalCotizacion('servicios', ids, nombres);
            });
        }
    }

   // === PAQUETES: Cotizar ===
document.querySelectorAll('.btn-cotizar').forEach(btn => {
    btn.addEventListener('click', function(e) {
        const paqueteDiv = e.target.closest('.paquete-card'); // <-- antes era '.paquete'
        if (!paqueteDiv) return;
        const paqueteId = parseInt(paqueteDiv.dataset.paqueteId);
        const paqueteNombre = paqueteDiv.dataset.paqueteNombre;
        mostrarModalCotizacion('paquete', paqueteId, paqueteNombre);
    });
});

    // === MODAL DE COTIZACIÓN: ENVÍO Y CIERRE ===
    const form = document.getElementById('cotizacionForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const tipoEvento = document.getElementById('tipo_evento').value;
            const fechaEvento = document.getElementById('fecha_evento').value;
            const lugar = document.getElementById('lugar').value;

            if (!tipoEvento || !fechaEvento) {
                showToast('Por favor completa los campos obligatorios (*).', false);
                return;
            }

            let payload = {
                tipo: currentCotizacion.tipo,
                fecha_evento: fechaEvento,
                tipo_evento: tipoEvento,
                lugar: lugar,
                comentarios: document.getElementById('comentarios').value
            };

            if (currentCotizacion.tipo === 'paquete') {
                payload.paquete_id = currentCotizacion.id;
            } else if (currentCotizacion.tipo === 'servicios') {
                payload.servicios_ids = currentCotizacion.id;
            } else {
                return;
            }

            await enviarCotizacion(payload);
        });
    }

    const cancelBtn = document.getElementById('cancelarCotizacion');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            document.getElementById('cotizacionModal').style.display = 'none';
        });
    }

    const closeModalBtn = document.getElementById('closeCotizacionModal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            document.getElementById('cotizacionModal').style.display = 'none';
        });
    }

    window.addEventListener('click', (event) => {
        const modal = document.getElementById('cotizacionModal');
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});