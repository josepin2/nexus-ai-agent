/**
 * Chatbot Frontend Application
 */
console.log("🚀 app.js v1.1 cargado con éxito");

// Configuración
const API_BASE_URL = `http://${window.location.hostname}:8000`;
console.log("🔗 API_BASE_URL configurada en:", API_BASE_URL);

// Estado de la aplicación
let availableModels = [];
let currentModel = null;
let isTyping = false;
let chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
let currentChatId = null;
let selectedFile = null;
let userHasScrolledUp = false;

// Elementos del DOM
const modelSelect = document.getElementById('model-select');
const refreshBtn = document.getElementById('refresh-models');
const systemPromptInput = document.getElementById('system-prompt');
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');
const connectionStatus = document.getElementById('connection-status');
const welcomeMessage = document.querySelector('.welcome-message');
const chatHistoryList = document.getElementById('chat-history-list');
const settingsModal = document.getElementById('settings-modal');

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', () => {
    console.log("📦 DOM cargado, iniciando componentes...");
    
    // Iniciar precarga del modelo
    preloadModel("gemma4:e4b-it-q4_K_M");

    loadModels();
    checkConnection();
    setupEventListeners();
    
    // Pequeño retardo para asegurar que el servidor API esté listo
    setTimeout(() => {
        console.log("📡 Iniciando conexión EventSource...");
        setupEventSource();
    }, 500);
    
    // ... rest of init ...
    const savedPrompt = localStorage.getItem('systemPrompt');
    if (savedPrompt) {
        systemPromptInput.value = savedPrompt;
    }

    const savedModel = localStorage.getItem('selectedModel');
    if (savedModel) {
        currentModel = savedModel;
    }

    // Cargar historial
    renderChatHistory();
    // Iniciar con interfaz limpia sin crear entrada en el historial todavía
    currentChatId = null;
    clearChatUI();
});

// Configurar event listeners
function setupEventListeners() {
    // Cambiar modelo
    modelSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            switchModel(e.target.value);
        }
    });

    // Actualizar modelos
    refreshBtn.addEventListener('click', loadModels);

    // Enviar mensaje
    sendBtn.addEventListener('click', sendMessage);

    // Enter para enviar (sin Shift)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    userInput.addEventListener('input', (e) => autoResize(e.target));

    // Habilitar/deshabilitar botón send
    userInput.addEventListener('input', () => {
        sendBtn.disabled = userInput.value.trim() === '' && !selectedFile;
    });

    // Cerrar modal al hacer click en el fondo
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettings();
    });

    // Interceptar clics en enlaces especiales (Abrir Carpeta)
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('md-link')) {
            const href = e.target.getAttribute('href');
            if (href && href.includes('/api/open-downloads')) {
                e.preventDefault();
                try {
                    await fetch(href);
                } catch (err) {
                    console.error("Error al abrir carpeta:", err);
                }
            }
        }
    });

    // Detectar si el usuario hace scroll hacia arriba para pausar el auto-scroll
    chatMessages.addEventListener('scroll', () => {
        // Tolerancia de 50px
        const isAtBottom = chatMessages.scrollHeight - chatMessages.clientHeight <= chatMessages.scrollTop + 50;
        userHasScrolledUp = !isAtBottom;
    });
}

// Auto-resize textarea
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

// Cargar modelos disponibles
async function loadModels() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/models`);
        const data = await response.json();

        if (data.success) {
            availableModels = data.models;
            currentModel = data.current_model;

            // Actualizar select
            modelSelect.innerHTML = '';
            
            // Si tenemos un modelo guardado en localStorage, intentamos usar ese si el backend no tiene uno activo
            const savedModel = localStorage.getItem('selectedModel');
            if (!currentModel && savedModel && availableModels.includes(savedModel)) {
                currentModel = savedModel;
                switchModel(savedModel); // Sincronizar con el backend
            }

            availableModels.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                if (model === currentModel) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });

            if (availableModels.length === 0) {
                modelSelect.innerHTML = '<option value="">No hay modelos disponibles</option>';
            }

            // Actualizar estado
            updateConnectionStatus(true);
        } else {
            throw new Error('Error al cargar modelos');
        }
    } catch (error) {
        console.error('Error cargando modelos:', error);
        modelSelect.innerHTML = '<option value="">Error al cargar modelos</option>';
        updateConnectionStatus(false);
    }
}

async function preloadModel(modelName) {
    const loaderModal = document.getElementById('loader-modal');
    if (loaderModal) loaderModal.style.display = 'flex';

    try {
        console.log(`🧠 Precargando modelo: ${modelName}`);
        const response = await fetch(`${API_BASE_URL}/api/model/switch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelName }),
        });

        const data = await response.json();
        if (data.success) {
            console.log(`✅ Modelo ${modelName} precargado.`);
            // Intentar una pequeña petición para forzar la carga en VRAM
            await fetch(`${API_BASE_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt: "ping", 
                    model: modelName,
                    system_prompt: "Responde solo 'pong'" 
                }),
            });
            console.log("🚀 VRAM lista.");
        }
    } catch (error) {
        console.error("❌ Error en precarga:", error);
    } finally {
        if (loaderModal) loaderModal.style.display = 'none';
    }
}

// Cambiar de modelo
async function switchModel(modelName) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/model/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ model: modelName }),
        });

        const data = await response.json();

        if (data.success) {
            currentModel = modelName;
            modelSelect.value = modelName;
            localStorage.setItem('selectedModel', modelName); // Guardar persistencia
            addSystemMessage(`Modelo cambiado a: ${modelName}`);
        } else {
            throw new Error(data.message || 'Error al cambiar modelo');
        }
    } catch (error) {
        console.error('Error cambiando modelo:', error);
        alert('Error al cambiar el modelo: ' + error.message);
    }
}

// Enviar mensaje
async function sendMessage() {
    const message = userInput.value.trim();
    
    if ((!message && !selectedFile) || isTyping) return;
    
    // Verificar que haya un modelo seleccionado
    if (!currentModel) {
        alert('Por favor selecciona un modelo primero');
        return;
    }

    // Habilitar estado de envío
    isTyping = true;
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.disabled = true;
    typingIndicator.style.display = 'block';

    // Leer imagen como dataURL antes de limpiar la selección
    let imageUrl = null;
    let docInfo = null;
    if (selectedFile) {
        if (selectedFile.type.startsWith('image/')) {
            imageUrl = await readFileAsDataURL(selectedFile);
        } else {
            docInfo = {
                name: selectedFile.name,
                label: getFileTypeLabel(selectedFile)
            };
        }
    }

    // Agregar mensaje del usuario (con miniatura si es imagen, chip si es doc)
    const displayText = message || '';
    addMessage('user', displayText, { imageUrl, docInfo });
    saveMessageToCurrentChat('user', displayText, imageUrl, docInfo);

    // Tomar el archivo antes de limpiar
    const fileToSend = selectedFile;
    removeFile();

    // Obtener sistema prompt
    const systemPrompt = localStorage.getItem('systemPrompt') || systemPromptInput.value.trim();

    // Obtener el historial del chat actual para mantener el contexto
    const currentChat = chatHistory.find(c => c.id === currentChatId);
    const historyContext = currentChat ? currentChat.messages.slice(-10).map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content
    })) : [];

    try {
        let response;
        
        // Obtener configuración de herramientas
        const toolSettings = {
            web_search: localStorage.getItem('toolWebSearch') !== 'false',
            youtube: localStorage.getItem('toolYoutube') !== 'false',
            word: localStorage.getItem('toolWord') !== 'false',
            patterns: localStorage.getItem('toolPatterns') !== 'false',
            automator: localStorage.getItem('toolAutomator') !== 'false'
        };

        if (fileToSend) {
            // Enviar con FormData al endpoint de upload
            const formData = new FormData();
            formData.append('prompt', message);
            formData.append('model', currentModel);
            if (systemPrompt) formData.append('system_prompt', systemPrompt);
            formData.append('history', JSON.stringify(historyContext));
            formData.append('tool_settings', JSON.stringify(toolSettings));
            formData.append('file', fileToSend);

            response = await fetch(`${API_BASE_URL}/api/chat/upload`, {
                method: 'POST',
                body: formData,
            });
        } else {
            response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: message,
                    model: currentModel,
                    system_prompt: systemPrompt,
                    history: historyContext,
                    tool_settings: toolSettings
                }),
            });
        }

        typingIndicator.style.display = 'none';

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const messageId = Date.now().toString();
        addStreamingMessage('ai', '', messageId);

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;
        let fullText = "";

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            done = readerDone;
            if (value) {
                const chunk = decoder.decode(value, {stream: true});
                fullText += chunk;
                updateStreamingMessage(messageId, fullText);
            }
        }

        if (!fullText.trim()) {
            updateStreamingMessage(messageId, 'No contesta');
            saveMessageToCurrentChat('ai', 'No contesta');
        } else {
            saveMessageToCurrentChat('ai', fullText);
        }

    } catch (error) {
        typingIndicator.style.display = 'none';
        console.error("Detalle COMPLETO del error:", error);
        addMessage('error', `Error: ${error.message}. Si es un 'network error', el servidor podría haber cortado la conexión durante la descarga.`);
        saveMessageToCurrentChat('error', `Error de conexión: ${error.message}`);
    } finally {
        isTyping = false;
        sendBtn.disabled = userInput.value.trim() === '' && !selectedFile;
    }
}

// Helper: leer archivo como dataURL
function readFileAsDataURL(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// Agregar mensaje al chat
function addMessage(type, content, options = {}) {
    const { imageUrl, docInfo } = options;
    const messageDiv = document.createElement('div');
    
    if (type === 'error') {
        messageDiv.className = 'message-error';
        messageDiv.textContent = content;
    } else if (type === 'user') {
        messageDiv.className = 'message user';
        const imgHtml = imageUrl
            ? `<img src="${imageUrl}" class="msg-image-thumb" alt="imagen adjunta">`
            : '';
        const docHtml = docInfo
            ? `<div class="doc-chip-msg">
                <span class="doc-chip-msg-icon">${getDocIcon(docInfo.label)}</span>
                <div class="doc-chip-msg-body">
                    <span class="doc-chip-msg-name">${escapeHtml(docInfo.name)}</span>
                    <span class="doc-chip-msg-type">${docInfo.label.toUpperCase()}</span>
                </div>
               </div>`
            : '';
        const textHtml = content
            ? `<div class="message-content">${escapeHtml(content)}</div>`
            : '';
        messageDiv.innerHTML = `
            <div class="message-bubble-user">${imgHtml}${docHtml}${textHtml}</div>
        `;
    } else if (type === 'ai') {
        messageDiv.className = 'message-ai';
        messageDiv.innerHTML = `
            <div class="message-content">${formatResponse(content)}</div>
        `;
    } else {
        messageDiv.className = 'message';
        messageDiv.textContent = content;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Agregar mensaje al chat en streaming
function addStreamingMessage(type, initialContent, id) {
    const messageDiv = document.createElement('div');
    messageDiv.id = `msg-${id}`;
    
    if (type === 'ai') {
        messageDiv.className = 'message-ai';
        messageDiv.innerHTML = `
            <div class="message-content">${formatResponse(initialContent)}</div>
        `;
    }
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Actualizar mensaje en streaming
function updateStreamingMessage(id, content) {
    const messageDiv = document.getElementById(`msg-${id}`);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        if (contentDiv) {
            contentDiv.innerHTML = formatResponse(content);
            
            // Si el usuario no ha subido a leer, seguimos bajando el scroll automáticamente
            if (!userHasScrolledUp) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }
    }
}

// Agregar mensaje de sistema
function addSystemMessage(content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message-system';
    messageDiv.style.textAlign = 'center';
    messageDiv.style.fontSize = '0.85rem';
    messageDiv.style.color = 'var(--text-secondary)';
    messageDiv.style.padding = '0.5rem';
    messageDiv.textContent = content;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Limpiar UI del chat
function clearChatUI() {
    chatMessages.innerHTML = '';
    if (welcomeMessage) {
        chatMessages.appendChild(welcomeMessage);
    }
}

// ── Manejo de archivos adjuntos ──────────────────────────────
function handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    selectedFile = file;

    const chip = document.getElementById('file-chip');
    const chipName = document.getElementById('file-chip-name');
    const chipIcon = document.getElementById('file-chip-icon');

    const isImage = file.type.startsWith('image/');
    chipIcon.textContent = isImage ? '🖼️' : '📄';
    chipName.textContent = file.name;
    chip.style.display = 'flex';

    // Activar el botón de enviar aunque no haya texto
    sendBtn.disabled = false;

    // Reset input para permitir seleccionar el mismo archivo de nuevo
    document.getElementById('file-input').value = '';
}

function removeFile() {
    selectedFile = null;
    document.getElementById('file-chip').style.display = 'none';
    document.getElementById('file-input').value = '';
    sendBtn.disabled = userInput.value.trim() === '';
}

// Borrar historial del chat actual
function clearChat() {
    if (!currentChatId) return;
    if (!confirm('¿Seguro que quieres borrar todos los mensajes de este chat?')) return;
    
    const chatIndex = chatHistory.findIndex(c => c.id === currentChatId);
    if (chatIndex !== -1) {
        chatHistory[chatIndex].messages = [];
        saveChatHistory();
    }
    clearChatUI();
}

// Funciones de Configuración
function openSettings() {
    // Cargar siempre el prompt guardado para que sea visible
    systemPromptInput.value = localStorage.getItem('systemPrompt') || '';
    
    // Cargar opciones de herramientas
    document.getElementById('tool-web-search').checked = localStorage.getItem('toolWebSearch') !== 'false';
    document.getElementById('tool-youtube').checked = localStorage.getItem('toolYoutube') !== 'false';
    document.getElementById('tool-word').checked = localStorage.getItem('toolWord') !== 'false';
    document.getElementById('tool-patterns').checked = localStorage.getItem('toolPatterns') !== 'false';
    document.getElementById('tool-automator').checked = localStorage.getItem('toolAutomator') !== 'false';
    
    settingsModal.style.display = 'flex';
}

function closeSettings() {
    settingsModal.style.display = 'none';
}

function saveSettings() {
    const prompt = systemPromptInput.value.trim();
    localStorage.setItem('systemPrompt', prompt);
    
    // Guardar opciones de herramientas
    localStorage.setItem('toolWebSearch', document.getElementById('tool-web-search').checked);
    localStorage.setItem('toolYoutube', document.getElementById('tool-youtube').checked);
    localStorage.setItem('toolWord', document.getElementById('tool-word').checked);
    localStorage.setItem('toolPatterns', document.getElementById('tool-patterns').checked);
    localStorage.setItem('toolAutomator', document.getElementById('tool-automator').checked);
    
    closeSettings();
    addSystemMessage('Configuración guardada.');
}

// ── Borrar todos los chats ──────────────────────
function deleteAllChats() {
    if (!confirm('¿Seguro que quieres eliminar TODOS los chats? Esta acción no se puede deshacer.')) return;
    chatHistory = [];
    currentChatId = null;
    saveChatHistory();
    renderChatHistory();
    createNewChat();
    closeSettings();
    addSystemMessage('Todos los chats han sido eliminados.');
}

// ── Borrar memoria a largo plazo ──────────────────────
async function clearMemory() {
    if (!confirm('¿Seguro que quieres borrar todo lo que la IA ha aprendido de tus gustos e intereses? Esta acción no se puede deshacer.')) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/memory/clear`, {
            method: 'POST',
        });
        const data = await response.json();
        if (data.success) {
            closeSettings();
            addSystemMessage('Memoria a largo plazo borrada con éxito. El agente ha olvidado tus intereses pasados.');
        } else {
            alert('Error al borrar la memoria.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión al intentar borrar la memoria.');
    }
}

// Funciones de Historial
function createNewChat(clearUI = true) {
    currentChatId = Date.now().toString();
    const newChat = {
        id: currentChatId,
        title: 'Nuevo Chat',
        messages: []
    };
    chatHistory.unshift(newChat);
    saveChatHistory();
    renderChatHistory();
    if (clearUI) {
        clearChatUI();
    }
}

function saveChatHistory() {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

function saveMessageToCurrentChat(type, content, imageUrl = null, docInfo = null) {
    // Si no hay un chat activo (por ejemplo, al iniciar sesión nueva), creamos uno ahora
    // Pasamos false para NO limpiar la UI, ya que el mensaje ya se añadió visualmente
    if (!currentChatId || !chatHistory.find(c => c.id === currentChatId)) {
        createNewChat(false);
    }
    const chatIndex = chatHistory.findIndex(c => c.id === currentChatId);
    if (chatIndex !== -1) {
        if (chatHistory[chatIndex].messages.length === 0 && type === 'user') {
            chatHistory[chatIndex].title = (content || docInfo?.name || '(archivo)').substring(0, 30)
                + ((content || '').length > 30 ? '...' : '');
        }
        chatHistory[chatIndex].messages.push({ type, content, imageUrl, docInfo });
        saveChatHistory();
        renderChatHistory();
    }
}

function renderChatHistory() {
    if (!chatHistoryList) return;
    chatHistoryList.innerHTML = '';
    chatHistory.forEach(chat => {
        const li = document.createElement('li');
        li.textContent = chat.title;
        if (chat.id === currentChatId) {
            li.className = 'active';
        }
        li.onclick = () => loadChat(chat.id);
        chatHistoryList.appendChild(li);
    });
}

function loadChat(id) {
    const chat = chatHistory.find(c => c.id === id);
    if (chat) {
        currentChatId = id;
        clearChatUI();
        chat.messages.forEach(msg => {
            addMessage(msg.type, msg.content, { imageUrl: msg.imageUrl || null, docInfo: msg.docInfo || null });
        });
        renderChatHistory();
    }
}

// Verificar conexión
async function checkConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            updateConnectionStatus(true);
        } else {
            updateConnectionStatus(false);
        }
    } catch (error) {
        updateConnectionStatus(false);
    }
}

// Actualizar estado de conexión
function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.textContent = 'Conectado';
        connectionStatus.style.color = 'var(--success)';
        document.querySelector('.status-dot').classList.remove('error');
    } else {
        connectionStatus.textContent = 'Desconectado';
        connectionStatus.style.color = 'var(--error)';
        document.querySelector('.status-dot').classList.add('error');
    }
}

// ── Eventos SSE (Progreso de descarga) ───────────────────────
let eventSource = null;

function setupEventSource() {
    if (eventSource) {
        eventSource.close();
    }

    console.log("DEBUG: Intentando conectar EventSource a:", `${API_BASE_URL}/api/events`);
    eventSource = new EventSource(`${API_BASE_URL}/api/events`);
    
    const progressContainer = document.getElementById('download-progress-container');
    const progressBar = document.getElementById('download-progress-bar');
    const statusText = document.getElementById('download-status-text');
    const percentText = document.getElementById('download-percent');

    eventSource.onopen = () => {
        console.log("DEBUG: Conexión SSE establecida con éxito.");
        updateConnectionStatus(true);
        document.getElementById('sse-dot').style.background = 'var(--success)';
        document.getElementById('sse-text').textContent = 'Panel: Conectado';
    };

    eventSource.onmessage = (event) => {
        console.log("DEBUG: Evento SSE recibido:", event.data);
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'download_progress') {
                const percent = Math.round(data.percent);
                
                progressContainer.style.display = 'block';
                progressBar.style.width = `${percent}%`;
                statusText.textContent = data.message;
                percentText.textContent = `${percent}%`;

                if (data.status === 'completed' && data.filename) {
                    // Notificar al AI de forma invisible para que dé el aviso final
                    triggerAIDownloadReady(data.filename);
                    
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        progressBar.style.width = '0%';
                    }, 5000);
                } else if (data.status === 'error') {
                    statusText.style.color = 'var(--error)';
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        statusText.style.color = '';
                    }, 8000);
                }
            }
        } catch (err) {
            console.error("Error procesando evento SSE:", err);
        }
    };

    eventSource.onerror = (err) => {
        console.warn("Conexión SSE perdida o fallida. Reintentando en 5s...", err);
        document.getElementById('sse-dot').style.background = 'var(--error)';
        document.getElementById('sse-text').textContent = 'Panel: Error';
        eventSource.close();
        setTimeout(setupEventSource, 5000);
    };
}

/**
 * Activa una respuesta del AI cuando la descarga está lista
 */
async function triggerAIDownloadReady(filename) {
    if (isTyping) return;

    // Instrucciones para que el AI genere los enlaces con formato amigable
    const downloadUrl = `${API_BASE_URL}/downloads/${encodeURIComponent(filename)}`;
    const openFolderUrl = `${API_BASE_URL}/api/open-downloads`;
    
    const message = `La descarga del archivo "${filename}" ha finalizado con éxito. 
Infórmame de que ya está lista y utiliza EXACTAMENTE este formato para los enlaces al final de tu respuesta:

[📥 Descargar Archivo](${downloadUrl}) | [📂 Abrir Carpeta de Descargas](${openFolderUrl})`;
    
    isTyping = true;
    typingIndicator.style.display = 'block';

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: message,
                model: currentModel,
                system_prompt: localStorage.getItem('systemPrompt') || systemPromptInput.value.trim(),
                history: [] // No hace falta contexto para este aviso
            }),
        });

        typingIndicator.style.display = 'none';

        if (!response.ok) throw new Error("Error en aviso final");

        const messageId = Date.now().toString();
        addStreamingMessage('ai', '', messageId);

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;
        let fullText = "";

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            done = readerDone;
            if (value) {
                const chunk = decoder.decode(value, {stream: true});
                fullText += chunk;
                updateStreamingMessage(messageId, fullText);
            }
        }
        saveMessageToCurrentChat('ai', fullText);

    } catch (error) {
        console.error("Error en triggerAIDownloadReady:", error);
    } finally {
        isTyping = false;
        typingIndicator.style.display = 'none';
    }
}

// Tipo de archivo para mostrar
function getFileTypeLabel(file) {
    const name = file.name.toLowerCase();
    if (name.endsWith('.pdf')) return 'pdf';
    if (name.endsWith('.docx') || name.endsWith('.doc')) return 'word';
    if (name.endsWith('.txt')) return 'txt';
    return 'archivo';
}

function getDocIcon(label) {
    const icons = { pdf: '📄', word: '📝', txt: '📃', archivo: '📎' };
    return icons[label] || '📎';
}

// Escape HTML para prevenir XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Renderizador Markdown para respuestas del AI ───────────────
function formatResponse(text) {
    if (!text) return '';

    // 0. Ocultar bloques de generación de Word (Modo Silencioso)
    // Oculta bloques completos y también bloques que se están generando (desde el inicio hasta el final o hasta el final del texto actual)
    text = text.replace(/<word_document\s*[^>]*>[\s\S]*?(<\/word_document>|$)/g, '');
    
    // Ocultar etiquetas de memoria a largo plazo (Patrones)
    text = text.replace(/<pattern>[\s\S]*?(<\/pattern>|$)/gi, '');
    
    // Ocultar bloques de código de automatización de Python (Modo Silencioso)
    text = text.replace(/<run_python>[\s\S]*?(<\/run_python>|$)/gi, '');

    // 1. Extraer y proteger bloques de código
    const codeBlocks = [];
    text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
        const idx = codeBlocks.length;
        const safeCode = code.trim()
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const langLabel = lang ? `<div class="md-lang">${lang}</div>` : '';
        codeBlocks.push(`<div class="md-code-block">${langLabel}<pre><code>${safeCode}</code></pre></div>`);
        return `@@CODE${idx}@@`;
    });

    // 2. Extraer código inline
    const inlineCodes = [];
    text = text.replace(/`([^`\n]+)`/g, (_, code) => {
        const idx = inlineCodes.length;
        const safeCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        inlineCodes.push(`<code class="md-inline">${safeCode}</code>`);
        return `@@INLINE${idx}@@`;
    });

    // 2.5. Extraer tablas Markdown
    const tables = [];
    text = text.replace(/((?:\|[^\n]+\|\n?)+)/g, (match) => {
        if (!/\|[-\s:]+\|/.test(match)) return match;
        const idx = tables.length;
        let tableHtml = '<div class="table-container"><table class="md-table">';
        const rows = match.trim().split('\n');
        let inBody = false;
        rows.forEach(row => {
            if (/^\|[-\s:|]+\|$/.test(row.trim())) {
                inBody = true;
                return;
            }
            tableHtml += '<tr>';
            let cells = row.split('|');
            if (cells.length > 0 && cells[0].trim() === '') cells.shift();
            if (cells.length > 0 && cells[cells.length - 1].trim() === '') cells.pop();
            cells.forEach(cell => {
                const tag = inBody ? 'td' : 'th';
                tableHtml += `<${tag}>${cell.trim()}</${tag}>`;
            });
            tableHtml += '</tr>';
        });
        tableHtml += '</table></div>';
        tables.push(tableHtml);
        return `\n@@TABLE${idx}@@\n`;
    });

    // 3. Procesar línea a línea
    const lines = text.split('\n');
    const out = [];
    let ulOpen = false, olOpen = false;

    const closeList = () => {
        if (ulOpen) { out.push('</ul>'); ulOpen = false; }
        if (olOpen) { out.push('</ol>'); olOpen = false; }
    };

    for (const line of lines) {
        if (/^### /.test(line))      { closeList(); out.push(`<h3 class="md-h3">${line.slice(4)}</h3>`); }
        else if (/^## /.test(line)) { closeList(); out.push(`<h2 class="md-h2">${line.slice(3)}</h2>`); }
        else if (/^# /.test(line))  { closeList(); out.push(`<h1 class="md-h1">${line.slice(2)}</h1>`); }
        else if (/^[-*] /.test(line)) {
            if (olOpen) { out.push('</ol>'); olOpen = false; }
            if (!ulOpen) { out.push('<ul class="md-ul">'); ulOpen = true; }
            out.push(`<li>${line.slice(2)}</li>`);
        } else if (/^\d+\. /.test(line)) {
            if (ulOpen) { out.push('</ul>'); ulOpen = false; }
            if (!olOpen) { out.push('<ol class="md-ol">'); olOpen = true; }
            out.push(`<li>${line.replace(/^\d+\.\s*/, '')}</li>`);
        } else if (/^-{3,}$/.test(line.trim())) {
            closeList();
            out.push('<hr class="md-hr">');
        } else {
            closeList();
            out.push(line);
        }
    }
    closeList();

    // 4. Enlaces, Negritas, cursiva, HR
    let html = out.join('\n');
    html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="md-link" target="_blank">$1</a>');
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // 5. Agrupar en párrafos
    const blocks = html.split(/\n\n+/);
    html = blocks.map(block => {
        block = block.trim();
        if (!block) return '';
        if (/^<(ul|ol|h[1-6]|hr|div)/.test(block) || /^@@CODE/.test(block) || /^@@TABLE/.test(block)) return block;
        const inner = block.replace(/\n/g, '<br>');
        return `<p class="md-p">${inner}</p>`;
    }).filter(Boolean).join('\n');

    // 6. Restaurar código y tablas
    inlineCodes.forEach((v, i) => { html = html.split(`@@INLINE${i}@@`).join(v); });
    codeBlocks.forEach((v, i) => { html = html.split(`@@CODE${i}@@`).join(v); });
    tables.forEach((v, i) => { html = html.split(`@@TABLE${i}@@`).join(v); });

    return html;
}

// Refrescar modelos
async function refreshModels() {
    await loadModels();
}

// ── Gestión de Créditos ──────────────────────────
function openCredits() {
    document.getElementById('credits-modal').style.display = 'flex';
}

function closeCredits() {
    document.getElementById('credits-modal').style.display = 'none';
}