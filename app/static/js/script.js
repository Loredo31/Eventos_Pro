// ==================== MODAL TWITCH ====================
document.addEventListener('DOMContentLoaded', function() {
    const btnLive = document.getElementById('btnLive');
    const modal = document.getElementById('liveModal');
    const closeBtn = document.getElementById('closeModal');

    if (btnLive) {
        btnLive.addEventListener('click', function() {
            modal.style.display = 'block';
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// ==================== CHATBOT ====================
document.addEventListener('DOMContentLoaded', function() {
    const btnChat = document.getElementById('btnChat');
    const chatbot = document.getElementById('chatbot');
    const chatClose = document.getElementById('chatClose');
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btnSendMessage');
    const messagesDiv = document.getElementById('chat-messages');

    // Mostrar el chatbot con el botón del menú
    if (btnChat) {
        btnChat.addEventListener('click', function() {
            chatbot.classList.remove('hidden');
        });
    }

    // Cerrar el chatbot con la X
    if (chatClose) {
        chatClose.addEventListener('click', function() {
            chatbot.classList.add('hidden');
        });
    }

    // Enviar mensaje
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
            if (data.respuesta) {
                addMessage(data.respuesta, 'bot');
            } else if (data.error) {
                addMessage('Error: ' + data.error, 'bot');
            }
        })
        .catch(error => {
            addMessage('Error de conexión', 'bot');
        });
    }

    function addMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
        msgDiv.textContent = text;
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    if (btnSend) {
        btnSend.addEventListener('click', sendMessage);
    }
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    }
});

// ==================== NOTICIAS ====================
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('noticias-container');
    if (!container) return;

    fetch('/api/noticias')
        .then(response => response.json())
        .then(noticias => {
            if (noticias.error) {
                container.innerHTML = '<p>No se pudieron cargar las noticias.</p>';
                return;
            }
            if (noticias.length === 0) {
                container.innerHTML = '<p>No hay noticias disponibles.</p>';
                return;
            }
            let html = '';
            noticias.forEach(articulo => {
                html += `
                    <div class="noticia-card">
                        <h3>${articulo.title}</h3>
                        <p>${articulo.description || ''}</p>
                        <a href="${articulo.url}" target="_blank">Leer más</a>
                    </div>
                `;
            });
            container.innerHTML = html;
        })
        .catch(err => {
            container.innerHTML = '<p>Error al cargar noticias.</p>';
        });
});

// ==================== COTIZACIÓN DE PAQUETES (modal) ====================
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('cotizacionModal');
    const closeBtn = document.getElementById('closeCotizacionModal');
    const mensajeDiv = document.getElementById('cotizacion-mensaje');

    function mostrarModal(mensaje) {
        mensajeDiv.textContent = mensaje;
        modal.style.display = 'block';
    }

    // Cotizar paquetes
    document.querySelectorAll('.btn-cotizar').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const paqueteDiv = e.target.closest('.paquete');
            const paqueteId = paqueteDiv.dataset.paqueteId;
            const paqueteNombre = paqueteDiv.dataset.paqueteNombre;
            mostrarModal(`Cotización del paquete "${paqueteNombre}" (ID: ${paqueteId}) - Próximamente recibirás un correo con detalles.`);
        });
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// ==================== SERVICIOS: LISTA DE SELECCIONADOS ====================
document.addEventListener('DOMContentLoaded', function() {
    const listaSection = document.getElementById('lista-seleccionados');
    const seleccionadosContainer = document.getElementById('seleccionados-container');
    const btnCancelar = document.getElementById('btnCancelar');
    const btnCotizarLista = document.getElementById('btnCotizarLista');
    const modal = document.getElementById('cotizacionModal');
    const mensajeDiv = document.getElementById('cotizacion-mensaje');
    let seleccionados = []; // Array de objetos {id, nombre, precio}

    // Función para actualizar la lista en la interfaz
    function actualizarLista() {
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

    // Agregar servicio
    document.querySelectorAll('.btn-agregar').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const servicioDiv = e.target.closest('.servicio');
            const id = servicioDiv.dataset.servicioId;
            const nombre = servicioDiv.dataset.servicioNombre;
            const precio = parseInt(servicioDiv.dataset.servicioPrecio);

            // Evitar duplicados (opcional: podrías permitir múltiples, pero aquí evitamos duplicados por id)
            if (!seleccionados.some(s => s.id === id)) {
                seleccionados.push({ id, nombre, precio });
                actualizarLista();
            } else {
                alert('Este servicio ya está en tu lista');
            }
        });
    });

    // Cancelar: limpia la lista y la oculta
    if (btnCancelar) {
        btnCancelar.addEventListener('click', function() {
            seleccionados = [];
            actualizarLista();
        });
    }

    // Cotizar: muestra modal con el total
    if (btnCotizarLista) {
        btnCotizarLista.addEventListener('click', function() {
            if (seleccionados.length === 0) {
                alert('No hay servicios seleccionados');
                return;
            }
            const total = seleccionados.reduce((acc, item) => acc + item.precio, 0);
            mensajeDiv.textContent = `Cotización de servicios personalizados. Total: $${total} MXN. Próximamente recibirás un correo con detalles.`;
            modal.style.display = 'block';
        });
    }
});