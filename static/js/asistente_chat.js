/**
 * Funcionalidad del Chat Conversacional con el Asistente IA
 * Incluye integración con RIVE para avatar animado
 */

// Prevenir carga múltiple del script
if (typeof window.ASISTENTE_CHAT_LOADED !== 'undefined') {
    console.warn('⚠️ asistente_chat.js ya está cargado, evitando carga duplicada');
} else {
    window.ASISTENTE_CHAT_LOADED = true;

let historialChatIds = [];
let protocoloIdActual = null;
let paginaActual = '';
let riveInstance = null;
let riveStateMachine = null;
let riveButtonInstance = null; // Instancia RIVE para el botón flotante
let riveButtonStateMachine = null;
let riveButtonContent = null; // Guardar el content del botón RIVE
let riveContent = null; // Guardar el content del avatar RIVE
let procesandoMensaje = false; // Flag para evitar múltiples llamadas simultáneas a activarInputMensaje
let ultimoMensajeProcesado = ''; // Para evitar procesar el mismo mensaje múltiples veces
let timeoutProcesandoMensaje = null; // Timeout para resetear el flag si se queda bloqueado
let reintentosMensajeAvatar = 0; // Contador de reintentos para el avatar
const MAX_REINTENTOS_MENSAJE_AVATAR = 5; // Máximo 5 reintentos (5 segundos)

// Flags para evitar procesar notificaciones múltiples veces
let notificacionBienvenidaProcesada = false; // Flag para evitar procesar la notificación de bienvenida múltiples veces
let notificacionBienvenidaObserver = null; // Observer de la notificación de bienvenida para poder desconectarlo
let notificacionBienvenidaEventListener = null; // Event listener del botón de cerrar para poder removerlo
let procesandoMensajesFlash = false; // Flag para evitar que procesarMensajesFlashExistentes se ejecute múltiples veces simultáneamente

// Flags de control para evitar múltiples inicializaciones simultáneas
let inicializandoRIVEBoton = false; // Flag para evitar múltiples inicializaciones del botón
let inicializandoRIVE = false; // Flag para evitar múltiples inicializaciones del avatar
let riveBotonInicializado = false; // Flag para indicar que el botón ya fue inicializado
let riveInicializado = false; // Flag para indicar que el avatar ya fue inicializado

// Intentar recuperar instancias persistentes desde window (entre navegaciones)
// Esto permite que RIVE persista entre páginas sin reinicializarse
if (typeof window.riveButtonInstance !== 'undefined' && window.riveButtonInstance) {
    try {
        const content = window.riveButtonInstance.content || window.riveButtonInstance._content;
        if (content) {
            riveButtonInstance = window.riveButtonInstance;
            // Recuperar también los state machines y content guardados si están disponibles
            if (typeof window.riveButtonStateMachine !== 'undefined' && window.riveButtonStateMachine) {
                riveButtonStateMachine = window.riveButtonStateMachine;
            }
            if (typeof window.riveButtonContent !== 'undefined' && window.riveButtonContent) {
                riveButtonContent = window.riveButtonContent;
            }
            console.log('✅ Recuperada instancia RIVE del botón desde navegación anterior');
        }
    } catch (e) {
        console.warn('⚠️ No se pudo recuperar instancia RIVE del botón:', e);
    }
}

if (typeof window.riveInstance !== 'undefined' && window.riveInstance) {
    try {
        const content = window.riveInstance.content || window.riveInstance._content;
        if (content) {
            riveInstance = window.riveInstance;
            // Recuperar también los state machines y content guardados si están disponibles
            if (typeof window.riveStateMachine !== 'undefined' && window.riveStateMachine) {
                riveStateMachine = window.riveStateMachine;
            }
            if (typeof window.riveContent !== 'undefined' && window.riveContent) {
                riveContent = window.riveContent;
            }
            console.log('✅ Recuperada instancia RIVE del avatar desde navegación anterior');
        }
    } catch (e) {
        console.warn('⚠️ No se pudo recuperar instancia RIVE del avatar:', e);
    }
}

// Inicializar variables globales si no existen (para persistencia entre páginas)
if (typeof window.riveButtonInstance === 'undefined') {
    window.riveButtonInstance = riveButtonInstance || null;
}
if (typeof window.riveInstance === 'undefined') {
    window.riveInstance = riveInstance || null;
}

// Rutas de archivos .riv según contexto
const RIVE_FILE_PATH_LOGIN = '/static/Asistente_masculino.riv';
const RIVE_FILE_PATH_AUTH = '/static/Asistente_femenino.riv';

// Función para obtener la ruta correcta del archivo RIVE según el contexto
function obtenerRutaRIVE() {
    // Si el usuario está autenticado, usar el avatar femenino
    if (window.ASISTENTE_AUTH === true) {
        return RIVE_FILE_PATH_AUTH;
    }
    // Si no está autenticado (login), usar el avatar masculino
    return RIVE_FILE_PATH_LOGIN;
}

// Función de inicialización que se puede llamar en cualquier momento
function inicializarAsistenteChat() {
    const url = window.location.href;
    const match = url.match(/protocolo[\/_]?(\d+)/i);
    if (match) {
        protocoloIdActual = parseInt(match[1]);
    }
    
    const path = window.location.pathname;
    if (path.includes('editor_pap')) {
        paginaActual = 'Editor PAP';
    } else if (path.includes('editor_biopsias')) {
        paginaActual = 'Editor Biopsias';
    } else if (path.includes('editor_citologia')) {
        paginaActual = 'Editor Citología';
    } else if (path.includes('protocolos')) {
        paginaActual = 'Protocolos';
    } else if (path.includes('dashboard')) {
        paginaActual = 'Dashboard';
    }
    
    // Inicializar RIVE cuando el panel esté abierto y haya un canvas disponible
    const initRiveIfVisible = () => {
        const asistentePanel = document.getElementById('asistente-panel');
        if (!asistentePanel) return;
        
        const isPanelVisible = asistentePanel.style.display !== 'none' && asistentePanel.classList.contains('show');
        if (!isPanelVisible) return;
        
        // Buscar canvas en tab-chat o tab-mensajes
        const chatTab = document.getElementById('tab-chat');
        const mensajesTab = document.getElementById('tab-mensajes');
        const chatCanvas = document.getElementById('chat-avatar-rive');
        const mensajesCanvas = document.getElementById('chat-avatar-rive-mensajes');
        
        const isChatActive = chatTab && (chatTab.classList.contains('active') || chatTab.classList.contains('show'));
        const isMensajesActive = mensajesTab && (mensajesTab.classList.contains('active') || mensajesTab.classList.contains('show'));
        
        // Si hay un canvas disponible, inicializar RIVE
        // En login, el tab "Mensajes" es el activo por defecto
        const targetCanvas = chatCanvas || mensajesCanvas;
        
        if (targetCanvas) {
            // Verificar si ya hay una instancia para este canvas específico
            if (riveInstance && riveInstance.canvas === targetCanvas) {
                console.log('✅ RIVE ya está inicializado para este canvas');
                return; // Ya está inicializado para este canvas
            }
            
            console.log('Inicializando RIVE en panel...', {
                chatTab: chatTab ? chatTab.id : null,
                mensajesTab: mensajesTab ? mensajesTab.id : null,
                isChatActive,
                isMensajesActive,
                chatCanvas: !!chatCanvas,
                mensajesCanvas: !!mensajesCanvas,
                targetCanvas: targetCanvas ? targetCanvas.id : null
            });
            inicializarRIVE();
        } else {
            console.log('⚠️ No se encontró ningún canvas para inicializar RIVE');
        }
    };
    
    // Observar cambios en los tabs - pero con debounce para evitar loops infinitos
    const chatTab = document.getElementById('tab-chat');
    const mensajesTab = document.getElementById('tab-mensajes');
    
    let tabChangeTimeout = null;
    const handleTabChange = () => {
        if (tabChangeTimeout) {
            clearTimeout(tabChangeTimeout);
        }
        // Esperar un poco antes de inicializar RIVE para evitar loops
        tabChangeTimeout = setTimeout(() => {
            // Solo inicializar si el tab está activo (no forzar activación) y no está inicializado
            if (riveInicializado || inicializandoRIVE) {
                return; // Ya está inicializado o en proceso, no hacer nada
            }
            const isMensajesActive = mensajesTab && (mensajesTab.classList.contains('active') || mensajesTab.classList.contains('show'));
            const isChatActive = chatTab && (chatTab.classList.contains('active') || chatTab.classList.contains('show'));
            
            if (isMensajesActive || isChatActive) {
                initRiveIfVisible();
            }
        }, 500); // Delay más largo para evitar loops
    };
    
    [chatTab, mensajesTab].forEach(tab => {
        if (tab) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.attributeName === 'class') {
                        handleTabChange();
                    }
                });
            });
            
            observer.observe(tab, {
                attributes: true,
                attributeFilter: ['class']
            });
        }
    });
    
    // Observar cuando se abre el panel
    const asistentePanel = document.getElementById('asistente-panel');
    if (asistentePanel) {
            const panelObserver = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.attributeName === 'style' || mutation.attributeName === 'class') {
                        // Solo inicializar si no está inicializado y no se está inicializando
                        setTimeout(() => {
                            if (!riveInicializado && !inicializandoRIVE) {
                                initRiveIfVisible();
                            }
                        }, 300);
                    }
                });
            });
        
        panelObserver.observe(asistentePanel, {
            attributes: true,
            attributeFilter: ['style', 'class']
        });
    }
    
    // Intentos iniciales (solo si no está inicializado y no se está inicializando)
    setTimeout(() => {
        if (!riveInicializado && !inicializandoRIVE) {
            initRiveIfVisible();
        }
    }, 500);
    setTimeout(() => {
        if (!riveInicializado && !inicializandoRIVE) {
            initRiveIfVisible();
        }
    }, 1500);
    
    cargarHistorialChat();
    verificarEstadoClaude();
    
    // Configurar event listeners para los botones del chat
    setTimeout(() => {
        const btnEnviar = document.querySelector('button[onclick="enviarMensajeChat()"]');
        const btnLimpiar = document.querySelector('button[onclick="limpiarChat()"]');
        const inputChat = document.getElementById('chat-input');
        
        if (btnEnviar) {
            btnEnviar.addEventListener('click', () => {
                if (typeof window.enviarMensajeChat === 'function') {
                    window.enviarMensajeChat();
                } else {
                    console.error('❌ enviarMensajeChat no está disponible');
                }
            });
        }
        
        if (btnLimpiar) {
            btnLimpiar.addEventListener('click', () => {
                if (typeof window.limpiarChat === 'function') {
                    window.limpiarChat();
                } else {
                    console.error('❌ limpiarChat no está disponible');
                }
            });
        }
        
        if (inputChat) {
            inputChat.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (typeof window.enviarMensajeChat === 'function') {
                        window.enviarMensajeChat();
                    }
                }
            });
        }
    }, 100);
    
    // Inicializar RIVE en el botón flotante
    // Esperar un momento para asegurar que el DOM esté completamente cargado
    setTimeout(() => {
        console.log('🔍 Intentando inicializar RIVE después de DOMContentLoaded...');
        inicializarRIVEBoton();
    }, 500);
    
    // También intentar después de un delay adicional por si acaso (solo si no se inicializó)
    setTimeout(() => {
        const canvas = document.getElementById('btn-asistente-avatar-rive');
        if (canvas && !riveBotonInicializado && !inicializandoRIVEBoton && !riveButtonInstance) {
            console.log('🔍 Canvas existe pero RIVE no está inicializado, reintentando...');
            inicializarRIVEBoton();
        }
    }, 2000);
    
    // Si el usuario está autenticado, desactivar "Sin Permiso" (login exitoso)
    if (window.ASISTENTE_AUTH === true) {
        setTimeout(function() {
            if (typeof activarInputSinPermiso === 'function') {
                console.log('✅ Usuario autenticado, desactivando input "Sin Permiso"');
                activarInputSinPermiso(false);
            }
        }, 1500); // Esperar a que RIVE se cargue completamente
    }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    // DOM aún no está listo, esperar
    document.addEventListener('DOMContentLoaded', inicializarAsistenteChat);
} else {
    // DOM ya está listo, ejecutar inmediatamente
    console.log('✅ DOM ya está listo, inicializando asistente chat inmediatamente...');
    inicializarAsistenteChat();
}

/**
 * Inicializar RIVE en el botón flotante
 */
async function inicializarRIVEBoton() {
    // VERIFICACIÓN INICIAL: Evitar múltiples inicializaciones simultáneas
    if (inicializandoRIVEBoton) {
        console.log('⚠️ inicializarRIVEBoton ya está en proceso, ignorando llamada duplicada');
        return;
    }
    
    // Verificar si ya fue inicializado y la instancia existe
    if (riveBotonInicializado && riveButtonInstance && window.riveButtonInstance) {
        const canvas = document.getElementById('btn-asistente-avatar-rive');
        if (canvas && riveButtonInstance.canvas === canvas) {
            console.log('✅ RIVE botón ya está inicializado, ignorando llamada');
            return;
        }
    }
    
    inicializandoRIVEBoton = true;
    console.log('🔍 Iniciando inicializarRIVEBoton()...');
    
    // Verificar si ya hay una instancia activa (persistente entre páginas)
    // NOTA: En navegaciones tradicionales, el canvas cambia, por lo que necesitamos crear una nueva instancia
    // pero podemos restaurar rápidamente el estado desde las variables globales guardadas
    const instanciaAnteriorExiste = (window.riveButtonInstance && window.riveButtonInstance) || riveButtonInstance;
    const canvas = document.getElementById('btn-asistente-avatar-rive');
    
    if (instanciaAnteriorExiste && canvas) {
        // Verificar si el canvas es el mismo (misma página/navegación SPA)
        const canvasAnterior = instanciaAnteriorExiste.canvas;
        if (canvasAnterior && canvasAnterior === canvas) {
            // El canvas es el mismo, podemos reutilizar la instancia
            try {
                const content = instanciaAnteriorExiste.content || instanciaAnteriorExiste._content;
                if (content) {
                    riveButtonInstance = instanciaAnteriorExiste;
                    window.riveButtonInstance = riveButtonInstance;
                    // Restaurar variables guardadas
                    if (typeof window.riveButtonStateMachine !== 'undefined' && window.riveButtonStateMachine) {
                        riveButtonStateMachine = window.riveButtonStateMachine;
                    }
                    if (typeof window.riveButtonContent !== 'undefined' && window.riveButtonContent) {
                        riveButtonContent = window.riveButtonContent;
                    }
                    console.log('✅ RIVE ya está inicializado en el botón, reutilizando instancia existente');
                    riveBotonInicializado = true;
                    inicializandoRIVEBoton = false;
                    return;
                }
            } catch (e) {
                console.warn('⚠️ Instancia RIVE guardada pero puede tener problemas, continuando inicialización...');
            }
        } else {
            // El canvas cambió (nueva página), pero mantenemos las variables globales para restaurar estado
            console.log('📝 Canvas cambió en nueva página, creando nueva instancia pero restaurando estado');
            // Limpiar la instancia anterior del canvas anterior (si existe)
            if (instanciaAnteriorExiste.cleanup && canvasAnterior && canvasAnterior !== canvas) {
                try {
                    instanciaAnteriorExiste.cleanup();
                } catch (e) {
                    console.warn('⚠️ Error al limpiar instancia anterior:', e);
                }
            }
        }
    }
    
    // Si la instancia local existe y el canvas es el mismo, reutilizar
    if (riveButtonInstance && canvas && riveButtonInstance.canvas === canvas) {
        console.log('✅ RIVE ya está inicializado en el botón (variable local)');
        riveBotonInicializado = true;
        inicializandoRIVEBoton = false;
        return;
    }
    
    if (typeof rive === 'undefined') {
        console.warn('⚠️ RIVE no está cargado. Cargando librería...');
        try {
            await cargarLibreriaRIVE();
            
                // Verificar que RIVE se cargó correctamente
            if (typeof rive === 'undefined') {
                console.error('❌ RIVE no se pudo cargar después de intentar cargar la librería');
                inicializandoRIVEBoton = false;
                return;
            }
            console.log('✅ Librería RIVE cargada correctamente');
        } catch (error) {
            console.error('❌ Error al cargar librería RIVE:', error);
            inicializandoRIVEBoton = false;
            return;
        }
    } else {
        console.log('✅ RIVE ya está cargado');
    }
    
    if (!canvas) {
        console.warn('⚠️ Canvas para botón RIVE no encontrado. El botón puede no estar en esta página.');
        inicializandoRIVEBoton = false;
        return;
    }
    console.log('✅ Canvas encontrado:', canvas);
    
    const esLoginContext = typeof window.ASISTENTE_AUTH === 'undefined' || window.ASISTENTE_AUTH !== true;
    const avatarMaxSize = esLoginContext ? 360 : 480;
    
    try {
        // Verificar si hay una instancia anterior del canvas anterior que necesite limpieza
        if (instanciaAnteriorExiste && instanciaAnteriorExiste.canvas && instanciaAnteriorExiste.canvas !== canvas) {
            // La instancia anterior está en un canvas diferente, hacer cleanup
            try {
                if (instanciaAnteriorExiste.cleanup) {
                    instanciaAnteriorExiste.cleanup();
                }
            } catch (e) {
                console.warn('⚠️ Error al limpiar instancia anterior:', e);
            }
        }
        
        // Limpiar y ocultar canvas inicialmente
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.clearRect(0, 0, canvas.width || 312, canvas.height || 312);
        }
        canvas.style.display = 'none';
        canvas.style.visibility = 'hidden';
        canvas.style.opacity = '0';
        
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Configurar canvas para el botón - doble del tamaño original (312px)
        canvas.width = 312;
        canvas.height = 312;
        canvas.style.maxWidth = '312px';
        canvas.style.maxHeight = '312px';
        canvas.style.width = '312px';
        canvas.style.height = '312px';
        canvas.style.background = 'transparent';
        
        const rivePath = obtenerRutaRIVE();
        console.log('Cargando RIVE en botón flotante desde:', rivePath);
        
        riveButtonInstance = new rive.Rive({
            src: rivePath,
            canvas: canvas,
            autoplay: false, // NO autoplay, reproduciremos explícitamente la state machine
            stateMachines: ['State Machine 1'], // pedir explícitamente la state machine
            onLoad: () => {
                console.log('✅ RIVE cargado en botón flotante');
                // Marcar como inicializado
                riveBotonInicializado = true;
                inicializandoRIVEBoton = false;
                // Hacer la instancia accesible globalmente para persistir entre páginas
                window.riveButtonInstance = riveButtonInstance;
                // También guardar en sessionStorage para detectar entre navegaciones
                try {
                    sessionStorage.setItem('rive_button_initialized', 'true');
                } catch (e) {
                    console.warn('⚠️ No se pudo guardar en sessionStorage:', e);
                }
                
                // Esperar un momento para que content y state machines estén disponibles
                setTimeout(() => {
                    // Guardar el content cuando esté disponible (después de un delay)
                    if (riveButtonInstance && riveButtonInstance.content) {
                        riveButtonContent = riveButtonInstance.content;
                        window.riveButtonContent = riveButtonContent; // Guardar globalmente para persistir
                        console.log('✅ [BOTÓN] Content guardado');
                    } else {
                        // Intentar guardar el content después de otro delay
                        setTimeout(() => {
                            if (riveButtonInstance && riveButtonInstance.content) {
                                riveButtonContent = riveButtonInstance.content;
                                window.riveButtonContent = riveButtonContent; // Guardar globalmente para persistir
                                console.log('✅ [BOTÓN] Content guardado (segundo intento)');
                            }
                        }, 500);
                    }
                    
                    try {
                        // Primero, intentar listar todas las state machines disponibles
                        let stateMachineName = null;
                        
                        try {
                            if (typeof riveButtonInstance.stateMachineNames === 'function') {
                                const allMachines = riveButtonInstance.stateMachineNames();
                                console.log('📋 State machines disponibles:', allMachines);
                                if (allMachines && allMachines.length > 0) {
                                    // Buscar "State Machine 1" primero
                                    stateMachineName = allMachines.find(name => name === 'State Machine 1') || allMachines[0];
                                    console.log(`✅ Usando state machine: "${stateMachineName}"`);
                                }
                            }
                        } catch (e) {
                            console.warn('No se pudieron listar las state machines del botón:', e);
                        }
                        
                        // Intentar obtener los inputs de la state machine y reproducir SOLO esa state machine
                        if (stateMachineName) {
                            try {
                                // Primero obtener los inputs
                                if (typeof riveButtonInstance.stateMachineInputs === 'function') {
                                    riveButtonStateMachine = riveButtonInstance.stateMachineInputs(stateMachineName);
                                    // Guardar también globalmente para persistir entre páginas
                                    window.riveButtonStateMachine = riveButtonStateMachine;
                                    if (riveButtonStateMachine && riveButtonStateMachine.length > 0) {
                                        console.log(`✅ State Machine "${stateMachineName}" activada con ${riveButtonStateMachine.length} inputs`);
                                        
                                        // Si estamos en login (panel cerrado), asegurar que "Mensaje" esté en false
                                        const esLoginContext = typeof window.ASISTENTE_AUTH === 'undefined' || window.ASISTENTE_AUTH !== true;
                                        if (esLoginContext) {
                                            const inputMensaje = riveButtonStateMachine.find(input => 
                                                input.name === 'Mensaje' || 
                                                input.name === 'mensaje' || 
                                                input.name === 'message'
                                            );
                                            if (inputMensaje && typeof inputMensaje.value !== 'undefined') {
                                                inputMensaje.value = false;
                                                console.log('✅ [BOTÓN] Input "Mensaje" establecido a false al cargar login');
                                            }
                                        }
                                    } else {
                                        console.log(`✅ State Machine "${stateMachineName}" activada (sin inputs)`);
                                    }
                                    
                                }
                                
                                // Esperar un momento antes de reproducir para asegurar que todo esté listo
                                setTimeout(() => {
                                    // Reproducir explícitamente la state machine DESPUÉS de obtener los inputs
                                    if (typeof riveButtonInstance.play === 'function') {
                                        console.log(`▶️ Reproduciendo state machine "${stateMachineName}" en botón`);
                                        try {
                                            riveButtonInstance.play(stateMachineName);
                                            console.log(`✅ State machine "${stateMachineName}" reproducida exitosamente`);
                                        } catch (playError) {
                                            console.error('❌ Error al reproducir state machine:', playError);
                                        }
                                    } else {
                                        console.warn('⚠️ Método play() no disponible en riveButtonInstance');
                                    }
                                }, 100); // Pequeño delay para asegurar que todo esté listo
                            } catch (e) {
                                console.warn(`No se pudieron obtener inputs de "${stateMachineName}":`, e);
                                // Intentar reproducir de todas formas después de un delay
                                setTimeout(() => {
                                    try {
                                        if (typeof riveButtonInstance.play === 'function') {
                                            riveButtonInstance.play(stateMachineName);
                                            console.log(`✅ State machine "${stateMachineName}" reproducida (sin inputs)`);
                                        }
                                    } catch (e2) {
                                        console.error('❌ Error al reproducir state machine:', e2);
                                    }
                                }, 200);
                            }
                        } else {
                            console.warn('⚠️ No se encontró ninguna state machine para reproducir');
                            // Intentar usar "State Machine 1" directamente como fallback
                            setTimeout(() => {
                                try {
                                    if (typeof riveButtonInstance.play === 'function') {
                                        console.log('⚠️ Intentando reproducir "State Machine 1" directamente...');
                                        riveButtonInstance.play('State Machine 1');
                                        console.log('✅ State machine "State Machine 1" reproducida (fallback)');
                                        
                                        // Intentar obtener inputs después del fallback y establecer "Mensaje" en false si estamos en login
                                        setTimeout(() => {
                                            try {
                                                if (typeof riveButtonInstance.stateMachineInputs === 'function') {
                                                    const inputs = riveButtonInstance.stateMachineInputs('State Machine 1');
                                                    if (inputs && Array.isArray(inputs)) {
                                                        riveButtonStateMachine = inputs;
                                                        window.riveButtonStateMachine = inputs;
                                                        
                                                        const esLoginContext = typeof window.ASISTENTE_AUTH === 'undefined' || window.ASISTENTE_AUTH !== true;
                                                        if (esLoginContext) {
                                                            const inputMensaje = inputs.find(input => 
                                                                input.name === 'Mensaje' || 
                                                                input.name === 'mensaje' || 
                                                                input.name === 'message'
                                                            );
                                                            if (inputMensaje && typeof inputMensaje.value !== 'undefined') {
                                                                inputMensaje.value = false;
                                                                console.log('✅ [BOTÓN] Input "Mensaje" establecido a false al cargar login (fallback)');
                                                            }
                                                        }
                                                    }
                                                }
                                            } catch (e) {
                                                console.warn('⚠️ Error al obtener inputs después del fallback:', e);
                                            }
                                        }, 200);
                                    }
                                } catch (e) {
                                    console.error('❌ Error al reproducir state machine (fallback):', e);
                                }
                            }, 300);
                        }
                        
                        // Ajustar proporciones del canvas - esperar a que content esté disponible
                        try {
                            const content = riveButtonInstance.content || riveButtonInstance._content;
                            if (content && typeof content.defaultArtboard === 'function') {
                                const artboard = content.defaultArtboard();
                                if (artboard && artboard.width && artboard.height) {
                                    const width = artboard.width;
                                    const height = artboard.height;
                                    const aspectRatio = width / height;
                                    const maxSize = 312; // Doble del tamaño original (156px * 2)
                                    
                                    let canvasWidth, canvasHeight;
                                    if (aspectRatio > 1) {
                                        canvasWidth = maxSize;
                                        canvasHeight = maxSize / aspectRatio;
                                    } else {
                                        canvasHeight = maxSize;
                                        canvasWidth = maxSize * aspectRatio;
                                    }
                                    
                                    canvas.width = width;
                                    canvas.height = height;
                                    canvas.style.width = canvasWidth + 'px';
                                    canvas.style.height = canvasHeight + 'px';
                                    canvas.style.maxWidth = maxSize + 'px';
                                    canvas.style.maxHeight = maxSize + 'px';
                                    canvas.style.objectFit = 'contain';
                                }
                            } else {
                                // Usar tamaño fijo si no se puede acceder al artboard
                                canvas.style.width = '312px';
                                canvas.style.height = '312px';
                                canvas.style.maxWidth = '312px';
                                canvas.style.maxHeight = '312px';
                            }
                        } catch (e) {
                            console.warn('No se pudo ajustar proporciones del botón:', e);
                            // Usar tamaño fijo como fallback
                            canvas.style.width = '312px';
                            canvas.style.height = '312px';
                            canvas.style.maxWidth = '312px';
                            canvas.style.maxHeight = '312px';
                        }
                        
                        // Mostrar canvas RIVE (el icono ya está oculto por defecto)
                        canvas.style.setProperty('display', 'block', 'important');
                        canvas.style.setProperty('visibility', 'visible', 'important');
                        canvas.style.setProperty('opacity', '1', 'important');
                        canvas.style.zIndex = '2';
                        const fallbackIcon = document.querySelector('.btn-asistente-icono-fallback');
                        if (fallbackIcon) {
                            fallbackIcon.style.display = 'none';
                        }
                        
                        // Asegurar que el botón también sea visible
                        const boton = document.getElementById('btn-abrir-asistente');
                        if (boton) {
                            boton.style.display = 'block';
                            boton.style.visibility = 'visible';
                            boton.style.opacity = '1';
                        }
                        
                        console.log('✅ Canvas RIVE mostrado y visible');
                        
                        // Después de que RIVE esté completamente cargado, revisar mensajes flash existentes
                        // Solo procesar si no está siendo procesado actualmente
                        setTimeout(() => {
                            if (typeof procesarMensajesFlashExistentes === 'function' && typeof procesandoMensajesFlash !== 'undefined' && !procesandoMensajesFlash) {
                                procesarMensajesFlashExistentes();
                            }
                        }, 500);
                    } catch (e) {
                        console.error('Error procesando RIVE:', e);
                    }
                }, 200);
            },
            onLoadError: (error) => {
                console.error('❌ Error cargando RIVE en botón:', error);
                console.error('Error details:', {
                    type: error?.type,
                    data: error?.data,
                    message: error?.message
                });
                
                // Si el error es sobre state machine o animations, puede ser normal si usamos state machines
                if (error?.data && (
                    error.data.includes('State Machine') || 
                    error.data.includes('no animations') ||
                    error.data.includes('Animation with name')
                )) {
                    console.log('⚠️ Error de state machine/animations ignorado (se activará después):', error.data);
                    // Esperar y mostrar el canvas de todas formas - la state machine se activará en onLoad
                    setTimeout(() => {
                        const canvasEl = document.getElementById('btn-asistente-avatar-rive');
                        const fallbackIcon = document.querySelector('.btn-asistente-icono-fallback');
                        const boton = document.getElementById('btn-abrir-asistente');
                        if (canvasEl) {
                            canvasEl.style.display = 'block';
                            canvasEl.style.visibility = 'visible';
                            canvasEl.style.opacity = '1';
                            canvasEl.style.zIndex = '2';
                        }
                        if (fallbackIcon) {
                            fallbackIcon.style.display = 'none';
                        }
                        if (boton) {
                            boton.style.display = 'block';
                            boton.style.visibility = 'visible';
                            boton.style.opacity = '1';
                        }
                        console.log('✅ Canvas RIVE mostrado después de error (ignorado)');
                    }, 500);
                    return;
                }
                
                // Asegurar que el icono fallback sea visible para otros errores
                const fallbackIcon = document.querySelector('.btn-asistente-icono-fallback');
                const canvas = document.getElementById('btn-asistente-avatar-rive');
                if (fallbackIcon) {
                    fallbackIcon.style.display = 'block';
                }
                if (canvas) {
                    canvas.style.display = 'none';
                }
            }
        });
        
    } catch (error) {
        console.error('Error inicializando RIVE en botón:', error);
        inicializandoRIVEBoton = false;
        // Asegurar que el icono fallback sea visible
        const fallbackIcon = document.querySelector('.btn-asistente-icono-fallback');
        const canvas = document.getElementById('btn-asistente-avatar-rive');
        if (fallbackIcon) {
            fallbackIcon.style.display = 'block';
        }
        if (canvas) {
            canvas.style.display = 'none';
        }
    }
}

/**
 * Inicializar RIVE para el avatar
 */
async function inicializarRIVE() {
    // VERIFICACIÓN INICIAL: Evitar múltiples inicializaciones simultáneas
    if (inicializandoRIVE) {
        console.log('⚠️ inicializarRIVE ya está en proceso, ignorando llamada duplicada');
        return;
    }
    
    // Verificar si ya fue inicializado y la instancia existe
    if (riveInicializado && riveInstance && window.riveInstance) {
        const canvasChat = document.getElementById('chat-avatar-rive');
        const canvasMensajes = document.getElementById('chat-avatar-rive-mensajes');
        const canvas = canvasChat || canvasMensajes;
        if (canvas && riveInstance.canvas === canvas) {
            console.log('✅ RIVE avatar ya está inicializado, ignorando llamada');
            return;
        }
    }
    
    inicializandoRIVE = true;
    
    // Verificar si ya hay una instancia activa (persistente entre páginas)
    // NOTA: En navegaciones tradicionales, el canvas cambia, por lo que necesitamos crear una nueva instancia
    // pero podemos restaurar rápidamente el estado desde las variables globales guardadas
    const instanciaAnteriorExiste = (window.riveInstance && window.riveInstance) || riveInstance;
    
    // Calcular el tamaño del avatar según el contexto
    const esLoginContext = typeof window.ASISTENTE_AUTH === 'undefined' || window.ASISTENTE_AUTH !== true;
    // En login, usar 75% del tamaño (360 * 0.75 = 270px)
    // Para usuarios autenticados, usar 60% del tamaño original (480 * 0.6 = 288px)
    const avatarMaxSize = esLoginContext ? 270 : 288;
    
    // Buscar el canvas según el contexto y el tab activo
    let canvas = null;
    
    // En login, priorizar el canvas de "Mensajes"
    if (esLoginContext) {
        canvas = document.getElementById('chat-avatar-rive-mensajes');
        if (!canvas) {
            canvas = document.getElementById('chat-avatar-rive');
        }
    } else {
        // Si está autenticado, priorizar el canvas de "Chat"
        canvas = document.getElementById('chat-avatar-rive');
        if (!canvas) {
            canvas = document.getElementById('chat-avatar-rive-mensajes');
        }
    }
    
    // Si aún no hay canvas, buscar cualquier canvas disponible
    if (!canvas) {
        canvas = document.getElementById('chat-avatar-rive') || document.getElementById('chat-avatar-rive-mensajes');
    }
    
    console.log('🔍 Canvas seleccionado:', canvas ? {
        id: canvas.id,
        visible: canvas.offsetParent !== null,
        display: window.getComputedStyle(canvas).display,
        visibility: window.getComputedStyle(canvas).visibility,
        opacity: window.getComputedStyle(canvas).opacity,
        parentVisible: canvas.parentElement ? window.getComputedStyle(canvas.parentElement).display !== 'none' : false
    } : 'No encontrado');
    
    // NO activar automáticamente el tab - esto causa loops infinitos cuando el usuario intenta cambiar de tab
    // El tab debe ser activado por el usuario o por la función abrirAsistente(), no por inicializarRIVE()
    // Solo verificar si el canvas es visible, pero NO activar el tab automáticamente
    if (canvas) {
        const tabMensajes = document.getElementById('tab-mensajes');
        const tabChat = document.getElementById('tab-chat');
        
        const isMensajesActive = tabMensajes && (tabMensajes.classList.contains('active') || tabMensajes.classList.contains('show'));
        const isChatActive = tabChat && (tabChat.classList.contains('active') || tabChat.classList.contains('show'));
        
        // Solo loggear si el canvas no es visible, pero NO activar el tab
        if (canvas.id === 'chat-avatar-rive-mensajes' && !isMensajesActive) {
            console.log('⚠️ Canvas está en tab "Mensajes" que no está activo, pero NO se activará automáticamente para evitar loops');
        }
        
        if (canvas.id === 'chat-avatar-rive' && !isChatActive) {
            console.log('⚠️ Canvas está en tab "Chat" que no está activo, pero NO se activará automáticamente para evitar loops');
        }
    }
    
    if (instanciaAnteriorExiste && canvas) {
        // Verificar si el canvas es el mismo (misma página/navegación SPA)
        const canvasAnterior = instanciaAnteriorExiste.canvas;
        if (canvasAnterior && canvasAnterior === canvas) {
            // El canvas es el mismo, podemos reutilizar la instancia
            try {
                const content = instanciaAnteriorExiste.content || instanciaAnteriorExiste._content;
                if (content) {
                    riveInstance = instanciaAnteriorExiste;
                    window.riveInstance = riveInstance;
                    // Restaurar variables guardadas
                    if (typeof window.riveStateMachine !== 'undefined' && window.riveStateMachine) {
                        riveStateMachine = window.riveStateMachine;
                    }
                    if (typeof window.riveContent !== 'undefined' && window.riveContent) {
                        riveContent = window.riveContent;
                    }
                    console.log('✅ RIVE ya está inicializado en el avatar del chat, reutilizando instancia existente');
                    riveInicializado = true;
                    inicializandoRIVE = false;
                    return;
                }
            } catch (e) {
                console.warn('⚠️ Instancia RIVE guardada pero puede tener problemas, continuando inicialización...');
            }
        } else {
            // El canvas cambió (nueva página), pero mantenemos las variables globales para restaurar estado
            console.log('📝 Canvas cambió en nueva página, creando nueva instancia pero restaurando estado');
            // Limpiar la instancia anterior del canvas anterior (si existe)
            if (instanciaAnteriorExiste.cleanup && canvasAnterior && canvasAnterior !== canvas) {
                try {
                    instanciaAnteriorExiste.cleanup();
                } catch (e) {
                    console.warn('⚠️ Error al limpiar instancia anterior:', e);
                }
            }
        }
    }
    
    // Si la instancia local existe y el canvas es el mismo, reutilizar
    if (riveInstance && canvas && riveInstance.canvas === canvas) {
        console.log('✅ RIVE ya está inicializado en el avatar del chat (variable local)');
        riveInicializado = true;
        inicializandoRIVE = false;
        return;
    }
    
    if (typeof rive === 'undefined') {
        console.warn('RIVE no está cargado. Cargando librería...');
        await cargarLibreriaRIVE();
    }
    
    if (!canvas) {
        console.warn('Canvas para RIVE no encontrado');
        inicializandoRIVE = false;
        return;
    }
    
    try {
        // Verificar si hay una instancia anterior del canvas anterior que necesite limpieza
        if (instanciaAnteriorExiste && instanciaAnteriorExiste.canvas && instanciaAnteriorExiste.canvas !== canvas) {
            // La instancia anterior está en un canvas diferente, hacer cleanup
            try {
                if (instanciaAnteriorExiste.cleanup) {
                    instanciaAnteriorExiste.cleanup();
                }
            } catch (e) {
                console.warn('⚠️ Error al limpiar instancia anterior:', e);
            }
        }
        
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Configurar canvas y asegurar que sea visible
        canvas.width = avatarMaxSize;
        canvas.height = avatarMaxSize;
        canvas.style.maxWidth = avatarMaxSize + 'px';
        canvas.style.maxHeight = avatarMaxSize + 'px';
        canvas.style.width = avatarMaxSize + 'px';
        canvas.style.height = avatarMaxSize + 'px';
        canvas.style.background = 'transparent';
        canvas.style.display = 'block';
        canvas.style.visibility = 'visible';
        canvas.style.opacity = '1';
        console.log('✅ Canvas configurado y visible:', {
            id: canvas.id,
            width: canvas.width,
            height: canvas.height,
            display: canvas.style.display,
            visibility: canvas.style.visibility,
            opacity: canvas.style.opacity
        });
        
        const rivePath = obtenerRutaRIVE();
        console.log('Cargando RIVE desde:', rivePath);
        
        riveInstance = new rive.Rive({
            src: rivePath,
            canvas: canvas,
            autoplay: false, // NO autoplay, reproduciremos explícitamente la state machine
            stateMachines: ['State Machine 1'], // pedir explícitamente la state machine
            onLoad: () => {
                console.log('✅ RIVE cargado correctamente');
                // Marcar como inicializado
                riveInicializado = true;
                inicializandoRIVE = false;
                // Hacer la instancia accesible globalmente para persistir entre páginas
                window.riveInstance = riveInstance;
                // También guardar en sessionStorage para detectar entre navegaciones
                try {
                    sessionStorage.setItem('rive_avatar_initialized', 'true');
                } catch (e) {
                    console.warn('⚠️ No se pudo guardar en sessionStorage:', e);
                }
                
                // Esperar un momento para que content y state machines estén disponibles
                setTimeout(() => {
                                    // Guardar el content cuando esté disponible (después de un delay)
                                    if (riveInstance && riveInstance.content) {
                                        riveContent = riveInstance.content;
                                        window.riveContent = riveContent; // Guardar globalmente para persistir
                                        console.log('✅ [AVATAR] Content guardado');
                                    } else {
                                        // Intentar guardar el content después de otro delay
                                        setTimeout(() => {
                                            if (riveInstance && riveInstance.content) {
                                                riveContent = riveInstance.content;
                                                window.riveContent = riveContent; // Guardar globalmente para persistir
                                                console.log('✅ [AVATAR] Content guardado (segundo intento)');
                                            }
                                        }, 500);
                                    }
                    
                    try {
                        // Primero, intentar listar todas las state machines disponibles
                        let stateMachineName = null;
                        
                        try {
                            if (typeof riveInstance.stateMachineNames === 'function') {
                                const allMachines = riveInstance.stateMachineNames();
                                console.log('📋 State machines disponibles:', allMachines);
                                if (allMachines && allMachines.length > 0) {
                                    // Buscar "State Machine 1" primero
                                    stateMachineName = allMachines.find(name => name === 'State Machine 1') || allMachines[0];
                                    console.log(`✅ Usando state machine: "${stateMachineName}"`);
                                }
                            }
                        } catch (e) {
                            console.warn('No se pudieron listar las state machines:', e);
                        }
                        
                        // Intentar obtener los inputs de la state machine y reproducir SOLO esa state machine
                        if (stateMachineName) {
                            try {
                                // Primero obtener los inputs
                                if (typeof riveInstance.stateMachineInputs === 'function') {
                                    riveStateMachine = riveInstance.stateMachineInputs(stateMachineName);
                                    // Guardar también globalmente para persistir entre páginas
                                    window.riveStateMachine = riveStateMachine;
                                    if (riveStateMachine && riveStateMachine.length > 0) {
                                        console.log(`✅ State Machine "${stateMachineName}" activada con ${riveStateMachine.length} inputs`);
                                        
                                        // Si hay un mensaje pendiente de mostrar, intentar establecerlo ahora
                                        if (typeof window.mensajePendienteAvatar !== 'undefined' && window.mensajePendienteAvatar) {
                                            console.log('📢 Estableciendo mensaje pendiente en el avatar:', window.mensajePendienteAvatar);
                                            setTimeout(() => {
                                                activarInputMensaje(true, window.mensajePendienteAvatar);
                                                window.mensajePendienteAvatar = null; // Limpiar mensaje pendiente
                                            }, 500);
                                        }
                                    } else {
                                        console.log(`✅ State Machine "${stateMachineName}" activada (sin inputs)`);
                                    }
                                    
                                }
                                
                                // Esperar un momento antes de reproducir para asegurar que todo esté listo
                                setTimeout(() => {
                                    // Reproducir explícitamente la state machine DESPUÉS de obtener los inputs
                                    if (typeof riveInstance.play === 'function') {
                                        console.log(`▶️ Reproduciendo state machine "${stateMachineName}" en avatar principal`);
                                        try {
                                            riveInstance.play(stateMachineName);
                                            console.log(`✅ State machine "${stateMachineName}" reproducida exitosamente`);
                                        } catch (playError) {
                                            console.error('❌ Error al reproducir state machine:', playError);
                                        }
                                    } else {
                                        console.warn('⚠️ Método play() no disponible en riveInstance');
                                    }
                                }, 100); // Pequeño delay para asegurar que todo esté listo
                                
                                // Después de que RIVE esté completamente cargado, revisar mensajes flash existentes
                                // Solo procesar si no está siendo procesado actualmente
                                setTimeout(() => {
                                    if (typeof procesarMensajesFlashExistentes === 'function' && typeof procesandoMensajesFlash !== 'undefined' && !procesandoMensajesFlash) {
                                        procesarMensajesFlashExistentes();
                                    }
                                }, 600);
                            } catch (e) {
                                console.warn(`No se pudieron obtener inputs de "${stateMachineName}":`, e);
                                // Intentar reproducir de todas formas después de un delay
                                setTimeout(() => {
                                    try {
                                        if (typeof riveInstance.play === 'function') {
                                            riveInstance.play(stateMachineName);
                                            console.log(`✅ State machine "${stateMachineName}" reproducida (sin inputs)`);
                                        }
                                    } catch (e2) {
                                        console.error('❌ Error al reproducir state machine:', e2);
                                    }
                                }, 200);
                            }
                        } else {
                            console.warn('⚠️ No se encontró ninguna state machine para reproducir');
                            // Intentar usar "State Machine 1" directamente como fallback
                            setTimeout(() => {
                                try {
                                    if (typeof riveInstance.play === 'function') {
                                        console.log('⚠️ Intentando reproducir "State Machine 1" directamente...');
                                        riveInstance.play('State Machine 1');
                                        console.log('✅ State machine "State Machine 1" reproducida (fallback)');
                                        
                                        // Intentar obtener los inputs después de reproducir
                                        setTimeout(() => {
                                            try {
                                                if (typeof riveInstance.stateMachineInputs === 'function') {
                                                    const inputs = riveInstance.stateMachineInputs('State Machine 1');
                                                    if (inputs && Array.isArray(inputs)) {
                                                        riveStateMachine = inputs;
                                                        window.riveStateMachine = riveStateMachine;
                                                        console.log(`✅ [AVATAR] State Machine inputs obtenidos después del fallback: ${inputs.length} inputs`);
                                                        
                                                        // Si hay un mensaje pendiente, intentar establecerlo
                                                        if (typeof window.mensajePendienteAvatar !== 'undefined' && window.mensajePendienteAvatar) {
                                                            console.log('📢 Estableciendo mensaje pendiente en el avatar (fallback):', window.mensajePendienteAvatar);
                                                            setTimeout(() => {
                                                                activarInputMensaje(true, window.mensajePendienteAvatar);
                                                                window.mensajePendienteAvatar = null;
                                                            }, 500);
                                                        }
                                                    }
                                                }
                                            } catch (e) {
                                                console.warn('⚠️ Error al obtener inputs después del fallback:', e);
                                            }
                                        }, 500);
                                    }
                                } catch (e) {
                                    console.error('❌ Error al reproducir state machine (fallback):', e);
                                }
                            }, 300);
                        }
                        
                        // Asegurar que el canvas sea visible después de cargar RIVE
                        if (canvas) {
                            canvas.style.display = 'block';
                            canvas.style.visibility = 'visible';
                            canvas.style.opacity = '1';
                            console.log('✅ Canvas del avatar mostrado y visible');
                        }
                        
                        // Después de que RIVE esté completamente cargado, revisar mensajes flash existentes
                        // Solo procesar si no está siendo procesado actualmente
                        setTimeout(() => {
                            if (typeof procesarMensajesFlashExistentes === 'function' && typeof procesandoMensajesFlash !== 'undefined' && !procesandoMensajesFlash) {
                                procesarMensajesFlashExistentes();
                            }
                        }, 800);
                        
                        // Ajustar proporciones del canvas - esperar a que content esté disponible
                        try {
                            const content = riveInstance.content || riveInstance._content;
                            if (content && typeof content.defaultArtboard === 'function') {
                                const artboard = content.defaultArtboard();
                                if (artboard && artboard.width && artboard.height) {
                                    const width = artboard.width;
                                    const height = artboard.height;
                                    const aspectRatio = width / height;
                                    const maxSize = avatarMaxSize;
                                    
                                    let canvasWidth, canvasHeight;
                                    if (aspectRatio > 1) {
                                        canvasWidth = maxSize;
                                        canvasHeight = maxSize / aspectRatio;
                                    } else {
                                        canvasHeight = maxSize;
                                        canvasWidth = maxSize * aspectRatio;
                                    }
                                    
                                    canvas.width = width;
                                    canvas.height = height;
                                    canvas.style.width = canvasWidth + 'px';
                                    canvas.style.height = canvasHeight + 'px';
                                    canvas.style.maxWidth = maxSize + 'px';
                                    canvas.style.maxHeight = maxSize + 'px';
                                    canvas.style.objectFit = 'contain';
                                }
                            } else {
                                // Usar tamaño fijo si no se puede acceder al artboard
                                    canvas.style.width = avatarMaxSize + 'px';
                                    canvas.style.height = avatarMaxSize + 'px';
                                    canvas.style.maxWidth = avatarMaxSize + 'px';
                                    canvas.style.maxHeight = avatarMaxSize + 'px';
                            }
                        } catch (e) {
                            console.warn('No se pudo ajustar proporciones:', e);
                            // Usar tamaño fijo como fallback
                            canvas.style.width = avatarMaxSize + 'px';
                            canvas.style.height = avatarMaxSize + 'px';
                            canvas.style.maxWidth = avatarMaxSize + 'px';
                            canvas.style.maxHeight = avatarMaxSize + 'px';
                        }
                    } catch (e) {
                        console.error('Error procesando RIVE:', e);
                    }
                }, 200);
            },
            onLoadError: (error) => {
                console.error('❌ Error cargando RIVE:', error);
                console.error('Error details:', {
                    type: error?.type,
                    data: error?.data,
                    message: error?.message
                });
                
                // Si el error es sobre state machine o animations, puede ser normal si usamos state machines
                if (error?.data && (
                    error.data.includes('State Machine') || 
                    error.data.includes('no animations') ||
                    error.data.includes('Animation with name')
                )) {
                    console.log('⚠️ Error de state machine/animations ignorado (se activará después):', error.data);
                    // No mostrar avatar por defecto, esperar a que la state machine se active en onLoad
                    return;
                }
                
                mostrarAvatarPorDefecto();
            }
        });
        
    } catch (error) {
        console.error('Error inicializando RIVE:', error);
        inicializandoRIVE = false;
        mostrarAvatarPorDefecto();
    }
}

/**
 * Activar/desactivar el input "Sin Permiso" en la state machine de RIVE
 * @param {boolean} valor - true para activar (sin permiso), false para desactivar (con permiso)
 */
// Variable para evitar múltiples llamadas simultáneas
let procesandoSinPermiso = false;
let reintentosSinPermiso = 0;
const MAX_REINTENTOS_SIN_PERMISO = 10; // Máximo 10 reintentos (10 segundos)

/**
 * Activar/desactivar el input "Escuchando" en la state machine de RIVE
 * @param {boolean} valor - true para activar (panel abierto), false para desactivar (panel cerrado)
 */
function activarInputError(activar, textoError = '') {
    /**
     * Activar/desactivar el input "ERROR" en RIVE y establecer el texto del error
     * @param {boolean} activar - true para activar el error, false para desactivarlo
     * @param {string} textoError - Texto del error a mostrar en "Mensaje_error"
     */
    console.log(`📝 activarInputError llamado: activar=${activar}, textoError="${textoError}"`);
    
    // Si se activa un error, desactivar los otros inputs primero
    if (activar) {
        console.log('📝 [ERROR] Desactivando otros inputs antes de activar el error');
        if (typeof activarInputMensaje === 'function') {
            activarInputMensaje(false);
        }
        if (typeof activarInputSinPermiso === 'function') {
            activarInputSinPermiso(false);
        }
    }
    
    if (typeof rive === 'undefined') {
        console.warn('⚠️ RIVE no está cargado aún para activar input ERROR');
        return;
    }
    
    try {
        // Intentar con el avatar del panel primero si el panel está abierto
        let stateMachineInputs = null;
        let riveInstance = null;
        
        // Si el panel está abierto, SIEMPRE priorizar el avatar del panel para mostrar el error
        const panelAbierto = typeof asistenteAbierto !== 'undefined' && asistenteAbierto === true;
        
        // IMPORTANTE: Cuando el panel está abierto, siempre usar el avatar del panel para mostrar el error
        // NO verificar si el panel está cerrado para enviar mensajes, los errores SIEMPRE deben mostrarse
        if (panelAbierto && window.riveInstance && window.riveStateMachine && Array.isArray(window.riveStateMachine)) {
            stateMachineInputs = window.riveStateMachine;
            riveInstance = window.riveInstance;
            console.log('🔍 [ERROR] Panel abierto - Usando inputs del avatar del panel para mostrar error');
        }
        // Si el panel está cerrado, buscar en el botón flotante primero
        else if (!panelAbierto && window.riveButtonStateMachine && Array.isArray(window.riveButtonStateMachine)) {
            stateMachineInputs = window.riveButtonStateMachine;
            riveInstance = window.riveButtonInstance;
            console.log('🔍 [ERROR] Panel cerrado - Usando inputs del botón flotante');
        }
        // Si aún no está disponible, buscar en el avatar del panel
        else if (window.riveStateMachine && Array.isArray(window.riveStateMachine)) {
            stateMachineInputs = window.riveStateMachine;
            riveInstance = window.riveInstance;
            console.log('🔍 [ERROR] Usando inputs del avatar del panel (fallback)');
        }
        // Si aún no está disponible, buscar en el botón flotante como último recurso
        else if (window.riveButtonStateMachine && Array.isArray(window.riveButtonStateMachine)) {
            stateMachineInputs = window.riveButtonStateMachine;
            riveInstance = window.riveButtonInstance;
            console.log('🔍 [ERROR] Usando inputs del botón flotante (fallback)');
        }
        
        // Si aún no hay inputs, intentar obtenerlos directamente
        // Priorizar el avatar del panel si está abierto
        if (!stateMachineInputs) {
            // PRIORIDAD 1: Si el panel está abierto, SIEMPRE intentar obtener del avatar del panel primero
            if (panelAbierto && window.riveInstance) {
                try {
                    const inputs = window.riveInstance.stateMachineInputs('State Machine 1');
                    if (inputs && Array.isArray(inputs)) {
                        stateMachineInputs = inputs;
                        riveInstance = window.riveInstance;
                        console.log('🔍 [ERROR] Inputs obtenidos directamente del avatar del panel (panel abierto)');
                    }
                } catch (e) {
                    console.warn('⚠️ [ERROR] No se pudieron obtener inputs directamente del avatar del panel:', e);
                }
            }
            
            // PRIORIDAD 2: Si no se obtuvieron y el panel está cerrado, intentar con el botón
            if (!stateMachineInputs && !panelAbierto && window.riveButtonInstance) {
                try {
                    const inputs = window.riveButtonInstance.stateMachineInputs('State Machine 1');
                    if (inputs && Array.isArray(inputs)) {
                        stateMachineInputs = inputs;
                        riveInstance = window.riveButtonInstance;
                        console.log('🔍 [ERROR] Inputs obtenidos directamente del botón (panel cerrado)');
                    }
                } catch (e) {
                    console.warn('⚠️ [ERROR] No se pudieron obtener inputs directamente del botón:', e);
                }
            }
            
            // PRIORIDAD 3: Si aún no se obtuvieron, intentar con el avatar del panel (fallback)
            if (!stateMachineInputs && window.riveInstance) {
                try {
                    const inputs = window.riveInstance.stateMachineInputs('State Machine 1');
                    if (inputs && Array.isArray(inputs)) {
                        stateMachineInputs = inputs;
                        riveInstance = window.riveInstance;
                        console.log('🔍 [ERROR] Inputs obtenidos directamente del avatar (fallback)');
                    }
                } catch (e) {
                    console.warn('⚠️ [ERROR] No se pudieron obtener inputs directamente del avatar:', e);
                }
            }
            
            // PRIORIDAD 4: Como último recurso, intentar con el botón
            if (!stateMachineInputs && window.riveButtonInstance) {
                try {
                    const inputs = window.riveButtonInstance.stateMachineInputs('State Machine 1');
                    if (inputs && Array.isArray(inputs)) {
                        stateMachineInputs = inputs;
                        riveInstance = window.riveButtonInstance;
                        console.log('🔍 [ERROR] Inputs obtenidos directamente del botón (fallback final)');
                    }
                } catch (e) {
                    console.warn('⚠️ [ERROR] No se pudieron obtener inputs directamente del botón (fallback final):', e);
                }
            }
        }
        
        if (stateMachineInputs && riveInstance) {
            console.log(`🔍 [ERROR] Total inputs disponibles: ${stateMachineInputs.length}`);
            console.log(`🔍 [ERROR] Nombres de inputs:`, stateMachineInputs.map(input => input.name || 'sin nombre'));
            
            // Buscar el input "ERROR"
            const inputError = stateMachineInputs.find(input => {
                const name = input.name || '';
                return name.toLowerCase() === 'error';
            });
            
            // Buscar el input "atencion" o "Atencion"
            const inputAtencion = stateMachineInputs.find(input => {
                const name = input.name || '';
                return name.toLowerCase() === 'atencion' || name.toLowerCase() === 'atención';
            });
            
            if (inputError) {
                console.log(`🔍 [ERROR] Input "ERROR" encontrado: type=${inputError.type}, hasValue=${typeof inputError.value !== 'undefined'}, hasFire=${typeof inputError.fire === 'function'}, currentValue=${inputError.value}`);
                
                // Intentar establecer como boolean primero
                if (typeof inputError.value !== 'undefined') {
                    try {
                        inputError.value = activar;
                        console.log(`✅ [ERROR] Input "ERROR" (boolean) establecido a: ${activar}`);
                    } catch (e) {
                        console.warn('⚠️ [ERROR] Error al establecer input ERROR como boolean:', e);
                    }
                }
                
                // Si es un trigger, dispararlo cuando activar es true
                if (typeof inputError.fire === 'function' && activar) {
                    try {
                        inputError.fire();
                        console.log(`✅ [ERROR] Trigger "ERROR" activado`);
                    } catch (e) {
                        console.warn('⚠️ [ERROR] Error al disparar trigger ERROR:', e);
                    }
                }
                
                // Si hay texto de error y el input está activado, establecer el texto
                if (activar && textoError) {
                    // Intentar establecer el texto en "Mensaje_error" tanto en el botón como en el avatar
                    const nombresPosibles = ['Mensaje_error', 'mensaje_error', 'Mensaje Error', 'mensaje error', 'Error', 'error'];
                    let textoEstablecido = false;
                    
                    // IMPORTANTE: Si el panel está abierto, SIEMPRE establecer el texto en el avatar del panel primero
                    // Esto asegura que el error se muestre correctamente cuando el panel está abierto
                    if (panelAbierto && window.riveInstance && typeof window.riveInstance.setTextRunValue === 'function') {
                        for (const nombreTexto of nombresPosibles) {
                            try {
                                window.riveInstance.setTextRunValue(nombreTexto, textoError);
                                console.log(`✅ [ERROR] Texto del error establecido con nombre "${nombreTexto}" en avatar del panel (panel abierto): "${textoError}"`);
                                textoEstablecido = true;
                                break;
                            } catch (e) {
                                // Continuar con el siguiente nombre
                            }
                        }
                    }
                    
                    // Intentar primero con el riveInstance actual (botón o avatar)
                    if (!textoEstablecido) {
                        for (const nombreTexto of nombresPosibles) {
                            try {
                                if (typeof riveInstance.setTextRunValue === 'function') {
                                    riveInstance.setTextRunValue(nombreTexto, textoError);
                                    console.log(`✅ [ERROR] Texto del error establecido con nombre "${nombreTexto}" en ${riveInstance === window.riveButtonInstance ? 'botón' : 'avatar'}: "${textoError}"`);
                                    textoEstablecido = true;
                                    break;
                                }
                            } catch (e) {
                                // Continuar con el siguiente nombre
                            }
                        }
                    }
                    
                    // Si no se estableció, intentar también con el otro RIVE instance (botón o avatar)
                    if (!textoEstablecido) {
                        const otroRiveInstance = (riveInstance === window.riveButtonInstance) ? window.riveInstance : window.riveButtonInstance;
                        if (otroRiveInstance && typeof otroRiveInstance.setTextRunValue === 'function') {
                            for (const nombreTexto of nombresPosibles) {
                                try {
                                    otroRiveInstance.setTextRunValue(nombreTexto, textoError);
                                    console.log(`✅ [ERROR] Texto del error establecido con nombre "${nombreTexto}" en ${otroRiveInstance === window.riveButtonInstance ? 'botón' : 'avatar'}: "${textoError}"`);
                                    textoEstablecido = true;
                                    break;
                                } catch (e) {
                                    // Continuar con el siguiente nombre
                                }
                            }
                        }
                    }
                    
                    if (!textoEstablecido) {
                        console.warn('⚠️ [ERROR] No se pudo establecer el texto del error. Nombres intentados:', nombresPosibles);
                    }
                }
            } else {
                console.warn('⚠️ [ERROR] Input "ERROR" no encontrado en la state machine');
            }
            
            // Manejar el input "atencion": false cuando hay error, true cuando se sale del error
            if (inputAtencion) {
                if (inputAtencion.type === 'boolean' && typeof inputAtencion.value !== 'undefined') {
                    // Si hay error (activar = true), poner atencion en false
                    // Si se sale del error (activar = false), poner atencion en true
                    inputAtencion.value = !activar;
                    console.log(`✅ [ERROR] Input "atencion" establecido a: ${!activar} (inverso de ERROR)`);
                } else if (inputAtencion.type === 'trigger' && typeof inputAtencion.fire === 'function') {
                    // Si se sale del error, disparar el trigger
                    if (!activar) {
                        inputAtencion.fire();
                        console.log(`✅ [ERROR] Trigger "atencion" activado (error resuelto)`);
                    }
                }
            } else {
                console.warn('⚠️ [ERROR] Input "atencion" no encontrado en la state machine');
            }
            
            // Si se activó un error, programar su desactivación después de 5 segundos
            if (activar && textoError) {
                console.log('⏰ [ERROR] Programando desactivación del error después de 5 segundos');
                setTimeout(() => {
                    console.log('⏰ [ERROR] Desactivando error después del timeout');
                    // Solo desactivar ERROR (no los otros inputs)
                    activarInputError(false);
                }, 5000);
            }
        } else {
            console.warn('⚠️ [ERROR] RIVE no está disponible para activar input ERROR');
        }
    } catch (error) {
        console.error('❌ Error al activar input "ERROR":', error);
    }
}

function activarInputEscuchando(valor) {
    console.log(`📝 activarInputEscuchando llamado: valor=${valor}`);
    
    // Verificar que RIVE esté completamente cargado antes de intentar
    if (typeof rive === 'undefined') {
        console.warn('⚠️ RIVE no está cargado aún para activarInputEscuchando');
        setTimeout(() => activarInputEscuchando(valor), 1000);
        return;
    }
    
    // Esperar un momento para asegurar que RIVE esté completamente cargado
    setTimeout(function() {
        try {
            // Intentar con el botón flotante primero
            if (riveButtonInstance && riveButtonStateMachine && Array.isArray(riveButtonStateMachine)) {
                const inputEscuchando = riveButtonStateMachine.find(input => 
                    input.name === 'Escuchando' || 
                    input.name === 'escuchando' || 
                    input.name === 'listening' ||
                    input.name === 'Listening'
                );
                
                if (inputEscuchando) {
                    if (inputEscuchando.type === 'boolean' || typeof inputEscuchando.value !== 'undefined') {
                        inputEscuchando.value = valor;
                        console.log(`✅ [BOTÓN] Input "Escuchando" establecido a: ${valor}`);
                    } else if (inputEscuchando.type === 'trigger' && typeof inputEscuchando.fire === 'function') {
                        if (valor) {
                            inputEscuchando.fire();
                            console.log(`✅ [BOTÓN] Trigger "Escuchando" activado`);
                        }
                    }
                } else {
                    console.warn('⚠️ [BOTÓN] Input "Escuchando" no encontrado');
                }
            }
            
            // Intentar también con el avatar del chat
            if (riveInstance && riveStateMachine && Array.isArray(riveStateMachine)) {
                const inputEscuchando = riveStateMachine.find(input => 
                    input.name === 'Escuchando' || 
                    input.name === 'escuchando' || 
                    input.name === 'listening' ||
                    input.name === 'Listening'
                );
                
                if (inputEscuchando) {
                    if (inputEscuchando.type === 'boolean' || typeof inputEscuchando.value !== 'undefined') {
                        inputEscuchando.value = valor;
                        console.log(`✅ [AVATAR] Input "Escuchando" establecido a: ${valor}`);
                    } else if (inputEscuchando.type === 'trigger' && typeof inputEscuchando.fire === 'function') {
                        if (valor) {
                            inputEscuchando.fire();
                            console.log(`✅ [AVATAR] Trigger "Escuchando" activado`);
                        }
                    }
                } else {
                    console.warn('⚠️ [AVATAR] Input "Escuchando" no encontrado');
                }
            }
        } catch (e) {
            console.error('❌ Error al activar input "Escuchando":', e);
        }
    }, 200);
}

function activarInputSinPermiso(valor, reintento = 0) {
    // Evitar múltiples llamadas simultáneas
    if (procesandoSinPermiso) {
        console.log('⚠️ Ya se está procesando activarInputSinPermiso, ignorando llamada duplicada');
        return;
    }
    
    // Verificar límite de reintentos
    if (reintento >= MAX_REINTENTOS_SIN_PERMISO) {
        console.warn('⚠️ Se alcanzó el límite de reintentos para activarInputSinPermiso. RIVE puede no estar disponible.');
        procesandoSinPermiso = false;
        reintentosSinPermiso = 0;
        return;
    }
    
    procesandoSinPermiso = true;
    
    // Verificar que el canvas exista (puede no existir en la página de login)
    const canvas = document.getElementById('btn-asistente-avatar-rive');
    if (!canvas) {
        console.warn('⚠️ Canvas para botón RIVE no encontrado. Puede ser normal si no estamos en una página con el botón.');
        procesandoSinPermiso = false;
        reintentosSinPermiso = 0;
        return;
    }
    
    // Verificar que RIVE esté completamente cargado antes de intentar
    if (typeof rive === 'undefined') {
        console.warn(`⚠️ RIVE no está cargado aún, esperando... (reintento ${reintento + 1}/${MAX_REINTENTOS_SIN_PERMISO})`);
        setTimeout(() => {
            procesandoSinPermiso = false;
            activarInputSinPermiso(valor, reintento + 1);
        }, 1000);
        return;
    }
    
    // Verificar que la instancia RIVE esté disponible
    if (!riveButtonInstance) {
        console.warn(`⚠️ riveButtonInstance no está disponible aún, esperando... (reintento ${reintento + 1}/${MAX_REINTENTOS_SIN_PERMISO})`);
        setTimeout(() => {
            procesandoSinPermiso = false;
            activarInputSinPermiso(valor, reintento + 1);
        }, 1000);
        return;
    }
    
    // Resetear contador de reintentos si llegamos aquí
    reintentosSinPermiso = 0;
    
    // Esperar un momento para asegurar que RIVE esté completamente cargado
    setTimeout(function() {
        procesandoSinPermiso = false;
        try {
            // Verificar que las instancias estén realmente listas
            if (!riveButtonInstance) {
                console.warn('⚠️ [BOTÓN] riveButtonInstance no está disponible aún');
                return; // Salir temprano si no hay instancia
            }
            
            // Intentar con el botón flotante primero
            if (riveButtonInstance) {
                // Obtener los inputs frescos cada vez, no usar la variable guardada
                let stateMachineName = null;
                try {
                    // Intentar diferentes formas de acceder a las state machines
                    let allMachines = null;
                    
                    // Método 1: A través del animator
                    if (riveButtonInstance.animator && typeof riveButtonInstance.animator.stateMachineNames === 'function') {
                        allMachines = riveButtonInstance.animator.stateMachineNames();
                        console.log('🔍 [BOTÓN] State machines encontradas (vía animator):', allMachines);
                    }
                    // Método 2: Directamente como propiedad
                    else if (riveButtonInstance.stateMachineNames && Array.isArray(riveButtonInstance.stateMachineNames)) {
                        allMachines = riveButtonInstance.stateMachineNames;
                        console.log('🔍 [BOTÓN] State machines encontradas (como array):', allMachines);
                    }
                    // Método 3: A través del file
                    else if (riveButtonInstance.file && typeof riveButtonInstance.file.stateMachineNames === 'function') {
                        allMachines = riveButtonInstance.file.stateMachineNames();
                        console.log('🔍 [BOTÓN] State machines encontradas (vía file):', allMachines);
                    }
                    // Método 4: Usar la variable guardada si existe
                    else if (riveButtonStateMachine && Array.isArray(riveButtonStateMachine) && riveButtonStateMachine.length > 0) {
                        console.log('⚠️ [BOTÓN] Usando variable guardada como fallback');
                        // Intentar obtener el nombre desde los inputs guardados
                        const input = riveButtonStateMachine[0];
                        if (input && input.name) {
                            // Asumir "State Machine 1" si no podemos obtenerlo de otra forma
                            stateMachineName = 'State Machine 1';
                            console.log('✅ [BOTÓN] Usando "State Machine 1" como fallback');
                        }
                    }
                    
                    if (allMachines && allMachines.length > 0) {
                        stateMachineName = allMachines.find(name => name === 'State Machine 1') || allMachines[0];
                        console.log('✅ [BOTÓN] State Machine seleccionada:', stateMachineName);
                    } else if (!stateMachineName) {
                        console.warn('⚠️ [BOTÓN] No se encontraron state machines con ningún método');
                        // Intentar usar "State Machine 1" directamente
                        stateMachineName = 'State Machine 1';
                        console.log('⚠️ [BOTÓN] Intentando usar "State Machine 1" directamente');
                    }
                } catch (e) {
                    console.warn('⚠️ [BOTÓN] Error al listar state machines:', e);
                    console.error('⚠️ [BOTÓN] Detalles del error:', e.message, e.stack);
                    // Fallback: usar "State Machine 1" directamente
                    stateMachineName = 'State Machine 1';
                    console.log('⚠️ [BOTÓN] Usando "State Machine 1" como fallback después del error');
                }
                
                // Verificar que stateMachineName se obtuvo correctamente
                if (!stateMachineName) {
                    console.warn('⚠️ [BOTÓN] No se pudo obtener stateMachineName. Reintentando en 1 segundo...');
                    // Reintentar después de un segundo
                    setTimeout(() => activarInputSinPermiso(valor), 1000);
                    return; // Salir temprano si no hay state machine
                }
                
                // Usar SIEMPRE la variable guardada para evitar resetear la state machine
                let inputs = null;
                
                if (riveButtonStateMachine && Array.isArray(riveButtonStateMachine) && riveButtonStateMachine.length > 0) {
                    // Usar la variable guardada (no obtener inputs frescos para evitar resetear)
                    inputs = riveButtonStateMachine;
                    console.log('🔍 [BOTÓN] Usando inputs de variable guardada (evita resetear state machine)');
                } else if (stateMachineName) {
                    // Solo si no hay variable guardada, intentar obtener inputs (pero guardarlos después)
                    if (typeof riveButtonInstance.stateMachineInputs === 'function') {
                        inputs = riveButtonInstance.stateMachineInputs(stateMachineName);
                        // Guardar para próximas veces
                        riveButtonStateMachine = inputs;
                        console.log('🔍 [BOTÓN] Inputs obtenidos y guardados para próximas veces');
                        
                        // Verificar si existe el input "Mensaje"
                        if (inputs && Array.isArray(inputs)) {
                            const tieneMensaje = inputs.some(input => 
                                input.name === 'Mensaje' || input.name === 'mensaje' || input.name === 'message'
                            );
                            if (tieneMensaje) {
                                console.log('✅ [BOTÓN] Input "Mensaje" encontrado en la state machine');
                            } else {
                                console.warn('⚠️ [BOTÓN] Input "Mensaje" NO encontrado. Verifica que el input exista en RIVE con nombre "Mensaje".');
                            }
                        }
                    }
                    
                    if (!inputs) {
                        console.warn('⚠️ [BOTÓN] No se pudieron obtener inputs');
                        return;
                    }
                } else {
                    console.warn('⚠️ [BOTÓN] No hay stateMachineName ni variable guardada');
                    return;
                }
                
                console.log(`🔍 [BOTÓN] State Machine: "${stateMachineName || 'N/A'}"`);
                console.log(`🔍 [BOTÓN] Total inputs encontrados: ${inputs ? inputs.length : 0}`);
                
                if (inputs && Array.isArray(inputs)) {
                    // Mostrar todos los inputs disponibles para depuración
                    console.log(`🔍 [BOTÓN] Inputs disponibles:`, inputs.map(input => ({
                        name: input.name,
                        type: input.type || typeof input.value !== 'undefined' ? 'boolean' : 'trigger'
                    })));
                    
                    const inputSinPermiso = inputs.find(input => 
                        input.name === 'Sin_Permiso' || 
                        input.name === 'Sin Permiso' || 
                        input.name === 'sin_permiso' || 
                        input.name === 'sinPermiso'
                    );
                    
                    if (inputSinPermiso) {
                        console.log(`✅ [BOTÓN] Input "Sin_Permiso" ENCONTRADO:`, {
                            name: inputSinPermiso.name,
                            type: inputSinPermiso.type,
                            hasValue: typeof inputSinPermiso.value !== 'undefined',
                            hasFire: typeof inputSinPermiso.fire === 'function',
                            currentValue: inputSinPermiso.value
                        });
                        
                        // Si se activa Sin_Permiso, desactivar los otros inputs primero
                        if (valor) {
                            console.log('📝 [SIN_PERMISO] Desactivando otros inputs antes de activar Sin_Permiso');
                            if (typeof activarInputMensaje === 'function') {
                                activarInputMensaje(false);
                            }
                            if (typeof activarInputError === 'function') {
                                activarInputError(false);
                            }
                        }
                        
                        // Verificar el tipo de input y establecer el valor de forma segura
                        if (inputSinPermiso.type === 'boolean' || typeof inputSinPermiso.value !== 'undefined') {
                            inputSinPermiso.value = valor;
                            console.log(`✅ [BOTÓN] Input "Sin_Permiso" establecido a: ${valor}`);
                        } else if (inputSinPermiso.type === 'trigger' && typeof inputSinPermiso.fire === 'function') {
                            // Si es un trigger, solo dispararlo cuando valor es true
                            if (valor) {
                                inputSinPermiso.fire();
                                console.log(`✅ [BOTÓN] Trigger "Sin_Permiso" activado`);
                            }
                        }
                        
                        // Si hay texto de error y el input está activado, establecer el texto en "Mensaje_error"
                        if (valor) {
                            // Buscar el texto del error desde el mensaje flash o el contexto
                            const mensajesFlash = document.querySelectorAll('.mensaje-flash.alert-danger');
                            let textoError = '';
                            if (mensajesFlash.length > 0) {
                                const mensaje = mensajesFlash[0];
                                textoError = mensaje.getAttribute('data-message') || mensaje.textContent.trim();
                            }
                            
                            if (textoError) {
                                // Intentar establecer el texto en "Mensaje_error"
                                const nombresPosibles = ['Mensaje_error', 'mensaje_error', 'Mensaje Error', 'mensaje error', 'Error', 'error'];
                                let textoEstablecido = false;
                                
                                if (riveButtonInstance && typeof riveButtonInstance.setTextRunValue === 'function') {
                                    for (const nombreTexto of nombresPosibles) {
                                        try {
                                            riveButtonInstance.setTextRunValue(nombreTexto, textoError);
                                            console.log(`✅ [SIN_PERMISO] Texto del error establecido con nombre "${nombreTexto}": "${textoError}"`);
                                            textoEstablecido = true;
                                            break;
                                        } catch (e) {
                                            // Continuar con el siguiente nombre
                                        }
                                    }
                                }
                                
                                if (!textoEstablecido) {
                                    console.warn('⚠️ [SIN_PERMISO] No se pudo establecer el texto del error. Nombres intentados:', nombresPosibles);
                                }
                            }
                        }
                    } else {
                        console.warn('⚠️ [BOTÓN] Input "Sin_Permiso" NO encontrado. Buscando variantes...');
                        // Buscar inputs que contengan "permiso" o "Permiso"
                        const inputsSimilares = inputs.filter(input => 
                            input.name && (
                                input.name.toLowerCase().includes('permiso') ||
                                input.name.toLowerCase().includes('permission')
                            )
                        );
                        if (inputsSimilares.length > 0) {
                            console.log('🔍 [BOTÓN] Inputs similares encontrados:', inputsSimilares.map(i => i.name));
                        }
                    }
                } else {
                    console.warn('⚠️ [BOTÓN] No se pudieron obtener inputs o no es un array');
                }
            }
            
            // Intentar también con el avatar del chat
            if (riveInstance) {
                // Obtener los inputs frescos cada vez
                let stateMachineName = null;
                try {
                    // Intentar diferentes formas de acceder a las state machines
                    let allMachines = null;
                    
                    // Método 1: A través del animator
                    if (riveInstance.animator && typeof riveInstance.animator.stateMachineNames === 'function') {
                        allMachines = riveInstance.animator.stateMachineNames();
                        console.log('🔍 [AVATAR] State machines encontradas (vía animator):', allMachines);
                    }
                    // Método 2: Directamente como propiedad
                    else if (riveInstance.stateMachineNames && Array.isArray(riveInstance.stateMachineNames)) {
                        allMachines = riveInstance.stateMachineNames;
                        console.log('🔍 [AVATAR] State machines encontradas (como array):', allMachines);
                    }
                    // Método 3: A través del file
                    else if (riveInstance.file && typeof riveInstance.file.stateMachineNames === 'function') {
                        allMachines = riveInstance.file.stateMachineNames();
                        console.log('🔍 [AVATAR] State machines encontradas (vía file):', allMachines);
                    }
                    // Método 4: Usar la variable guardada si existe
                    else if (riveStateMachine && Array.isArray(riveStateMachine) && riveStateMachine.length > 0) {
                        console.log('⚠️ [AVATAR] Usando variable guardada como fallback');
                        stateMachineName = 'State Machine 1';
                        console.log('✅ [AVATAR] Usando "State Machine 1" como fallback');
                    }
                    
                    if (allMachines && allMachines.length > 0) {
                        stateMachineName = allMachines.find(name => name === 'State Machine 1') || allMachines[0];
                        console.log('✅ [AVATAR] State Machine seleccionada:', stateMachineName);
                    } else if (!stateMachineName) {
                        console.warn('⚠️ [AVATAR] No se encontraron state machines con ningún método');
                        stateMachineName = 'State Machine 1';
                        console.log('⚠️ [AVATAR] Intentando usar "State Machine 1" directamente');
                    }
                } catch (e) {
                    console.warn('⚠️ [AVATAR] Error al listar state machines:', e);
                    console.error('⚠️ [AVATAR] Detalles del error:', e.message, e.stack);
                    stateMachineName = 'State Machine 1';
                    console.log('⚠️ [AVATAR] Usando "State Machine 1" como fallback después del error');
                }
                
                // Verificar que stateMachineName se obtuvo correctamente
                if (!stateMachineName) {
                    console.warn('⚠️ [AVATAR] No se pudo obtener stateMachineName. Reintentando en 1 segundo...');
                    setTimeout(() => activarInputSinPermiso(valor), 1000);
                    return;
                }
                
                // Usar SIEMPRE la variable guardada para evitar resetear la state machine
                let inputs = null;
                
                if (riveStateMachine && Array.isArray(riveStateMachine) && riveStateMachine.length > 0) {
                    // Usar la variable guardada (no obtener inputs frescos para evitar resetear)
                    inputs = riveStateMachine;
                    console.log('🔍 [AVATAR] Usando inputs de variable guardada (evita resetear state machine)');
                } else if (stateMachineName) {
                    // Solo si no hay variable guardada, intentar obtener inputs (pero guardarlos después)
                    if (typeof riveInstance.stateMachineInputs === 'function') {
                        inputs = riveInstance.stateMachineInputs(stateMachineName);
                        // Guardar para próximas veces
                        riveStateMachine = inputs;
                        console.log('🔍 [AVATAR] Inputs obtenidos y guardados para próximas veces');
                        
                        // Verificar si existe el input "Mensaje"
                        if (inputs && Array.isArray(inputs)) {
                            const tieneMensaje = inputs.some(input => 
                                input.name === 'Mensaje' || input.name === 'mensaje' || input.name === 'message'
                            );
                            if (tieneMensaje) {
                                console.log('✅ [AVATAR] Input "Mensaje" encontrado en la state machine');
                            } else {
                                console.warn('⚠️ [AVATAR] Input "Mensaje" NO encontrado. Verifica que el input exista en RIVE con nombre "Mensaje".');
                            }
                        }
                    }
                    
                    if (!inputs) {
                        console.warn('⚠️ [AVATAR] No se pudieron obtener inputs');
                        return;
                    }
                } else {
                    console.warn('⚠️ [AVATAR] No hay stateMachineName ni variable guardada');
                    return;
                }
                
                console.log(`🔍 [AVATAR] State Machine: "${stateMachineName || 'N/A'}"`);
                console.log(`🔍 [AVATAR] Total inputs encontrados: ${inputs ? inputs.length : 0}`);
                
                if (inputs && Array.isArray(inputs)) {
                    // Mostrar todos los inputs disponibles para depuración
                    console.log(`🔍 [AVATAR] Inputs disponibles:`, inputs.map(input => ({
                        name: input.name,
                        type: input.type || typeof input.value !== 'undefined' ? 'boolean' : 'trigger'
                    })));
                    
                    const inputSinPermiso = inputs.find(input => 
                        input.name === 'Sin_Permiso' || 
                        input.name === 'Sin Permiso' || 
                        input.name === 'sin_permiso' || 
                        input.name === 'sinPermiso'
                    );
                    
                    if (inputSinPermiso) {
                        console.log(`✅ [AVATAR] Input "Sin_Permiso" ENCONTRADO:`, {
                            name: inputSinPermiso.name,
                            type: inputSinPermiso.type,
                            hasValue: typeof inputSinPermiso.value !== 'undefined',
                            hasFire: typeof inputSinPermiso.fire === 'function',
                            currentValue: inputSinPermiso.value
                        });
                        
                        // Verificar el tipo de input y establecer el valor de forma segura
                        if (inputSinPermiso.type === 'boolean' || typeof inputSinPermiso.value !== 'undefined') {
                            inputSinPermiso.value = valor;
                            console.log(`✅ [AVATAR] Input "Sin_Permiso" establecido a: ${valor}`);
                        } else if (inputSinPermiso.type === 'trigger' && typeof inputSinPermiso.fire === 'function') {
                            // Si es un trigger, solo dispararlo cuando valor es true
                            if (valor) {
                                inputSinPermiso.fire();
                                console.log(`✅ [AVATAR] Trigger "Sin_Permiso" activado`);
                            }
                        }
                    } else {
                        console.warn('⚠️ [AVATAR] Input "Sin_Permiso" NO encontrado. Buscando variantes...');
                        // Buscar inputs que contengan "permiso" o "Permiso"
                        const inputsSimilares = inputs.filter(input => 
                            input.name && (
                                input.name.toLowerCase().includes('permiso') ||
                                input.name.toLowerCase().includes('permission')
                            )
                        );
                        if (inputsSimilares.length > 0) {
                            console.log('🔍 [AVATAR] Inputs similares encontrados:', inputsSimilares.map(i => i.name));
                        }
                    }
                } else {
                    console.warn('⚠️ [AVATAR] No se pudieron obtener inputs o no es un array');
                }
            }
        } catch (error) {
            console.error('❌ Error al activar input "Sin Permiso":', error);
        }
    }, 500); // Esperar 500ms para asegurar que RIVE esté listo
}

/**
 * Procesar mensajes flash existentes cuando RIVE está listo
 */
// Variable para evitar procesar mensajes flash múltiples veces
let mensajesFlashProcesados = new Set();

function procesarMensajesFlashExistentes() {
    // VERIFICACIÓN INICIAL: Evitar múltiples ejecuciones simultáneas
    if (procesandoMensajesFlash) {
        console.log('⚠️ procesarMensajesFlashExistentes ya está en proceso, ignorando llamada duplicada');
        return;
    }
    
    procesandoMensajesFlash = true;
    
    try {
        // NO procesar mensajes flash si el panel del asistente está abierto
        if (typeof asistenteAbierto !== 'undefined' && asistenteAbierto === true) {
            console.log('📭 Panel del asistente abierto, no se procesan mensajes flash');
            procesandoMensajesFlash = false;
            return;
        }
        
        if (typeof activarInputMensaje !== 'function') {
            console.warn('⚠️ activarInputMensaje no está disponible aún');
            procesandoMensajesFlash = false;
            return;
        }
    
    // En login, no procesar mensajes flash hasta que RIVE esté completamente listo
    // y el input "Mensaje" ya esté establecido en false
    const esLoginContexto = typeof window.ASISTENTE_AUTH === 'undefined' || window.ASISTENTE_AUTH !== true;
    if (esLoginContexto) {
        // Esperar un momento para asegurar que el input "Mensaje" ya se estableció en false
        if (!window.riveButtonStateMachine || !Array.isArray(window.riveButtonStateMachine)) {
            console.log('⏳ [FLASH] Esperando a que RIVE esté completamente inicializado en login...');
            procesandoMensajesFlash = false; // Resetear antes del timeout recursivo
            setTimeout(() => {
                if (!procesandoMensajesFlash) {
                    procesarMensajesFlashExistentes();
                }
            }, 500);
            return;
        }
    }

    const loginErrorKeywords = ['incorrecta', 'no encontrado', 'inactivo', 'contraseña', 'permiso'];

    function esMensajeLoginCritico(texto) {
        if (!esLoginContexto) {
            return false;
        }
        const lower = texto.toLowerCase();
        return loginErrorKeywords.some(keyword => lower.includes(keyword));
    }
    
    // También procesar la notificación de bienvenida del dashboard (solo una vez)
    // IMPORTANTE: Verificar y marcar como procesada INMEDIATAMENTE para evitar condiciones de carrera
    // Primero verificar si ya está procesada para evitar trabajo innecesario
    if (!notificacionBienvenidaProcesada) {
        const notificacionBienvenida = document.getElementById('notificacionBienvenida');
        if (notificacionBienvenida && notificacionBienvenida.style.display !== 'none') {
            const alert = notificacionBienvenida.querySelector('.alert');
            // Verificar UNA SOLA VEZ y marcar como procesada INMEDIATAMENTE
            if (alert && alert.classList.contains('show')) {
                // VERIFICAR DOS VECES para evitar condiciones de carrera entre llamadas concurrentes
                // Esta es la segunda verificación atómica
                if (notificacionBienvenidaProcesada) {
                    console.log('⚠️ Notificación de bienvenida ya está siendo procesada por otra llamada');
                    return;
                }
                
                // Marcar como procesada INMEDIATAMENTE antes de cualquier otra operación
                notificacionBienvenidaProcesada = true;
                
                const mensajeTexto = alert.textContent.trim() || '¡Bienvenido!';
                console.log('📢 Procesando notificación de bienvenida:', mensajeTexto);
                
                // Verificar que no estemos procesando otro mensaje antes de activar
                // IMPORTANTE: Verificar TANTO el flag procesandoMensaje COMO si es el mismo mensaje
                const mensajeKeyBienvenida = `true_${mensajeTexto}`;
                if (!procesandoMensaje || mensajeKeyBienvenida !== ultimoMensajeProcesado) {
                    activarInputMensaje(true, mensajeTexto);
                } else {
                    console.log('⚠️ Ya se está procesando este mensaje de bienvenida, ignorando llamada duplicada');
                    // NO usar setTimeout aquí - simplemente ignorar
                    // El flag notificacionBienvenidaProcesada ya está en true, así que no se procesará de nuevo
                }
                
                // Desconectar observer anterior si existe
                if (notificacionBienvenidaObserver) {
                    notificacionBienvenidaObserver.disconnect();
                    notificacionBienvenidaObserver = null;
                }
                
                // Remover event listener anterior si existe
                if (notificacionBienvenidaEventListener) {
                    const btnCerrarAnterior = alert.querySelector('.btn-close');
                    if (btnCerrarAnterior) {
                        btnCerrarAnterior.removeEventListener('click', notificacionBienvenidaEventListener);
                    }
                    notificacionBienvenidaEventListener = null;
                }
                
                // Observar cuando se cierra - usar debounce para evitar múltiples llamadas
                let timeoutObserver = null;
                let ultimoEstadoShow = alert.classList.contains('show'); // Guardar estado inicial
                notificacionBienvenidaObserver = new MutationObserver(function(mutations) {
                    // Usar debounce para evitar múltiples llamadas rápidas
                    if (timeoutObserver) {
                        clearTimeout(timeoutObserver);
                    }
                    timeoutObserver = setTimeout(function() {
                        mutations.forEach(function(mutation) {
                            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                                // Solo actuar si realmente cambió de abierto a cerrado (no en cualquier cambio)
                                const estadoActualShow = alert.classList.contains('show');
                                const estadoActualDisplay = notificacionBienvenida.style.display !== 'none' && 
                                                           getComputedStyle(notificacionBienvenida).display !== 'none';
                                const estaCerrada = !estadoActualShow || !estadoActualDisplay;
                                
                                // Solo actuar si cambió de abierto a cerrado (no si ya estaba cerrada)
                                if (ultimoEstadoShow && estaCerrada && notificacionBienvenidaProcesada) {
                                    console.log('✅ Notificación de bienvenida cerrada, desactivando input "Mensaje"');
                                    activarInputMensaje(false);
                                    if (notificacionBienvenidaObserver) {
                                        notificacionBienvenidaObserver.disconnect();
                                        notificacionBienvenidaObserver = null;
                                    }
                                    notificacionBienvenidaProcesada = false; // Permitir procesar de nuevo si aparece otra vez
                                }
                                // Actualizar estado
                                ultimoEstadoShow = estadoActualShow;
                            }
                        });
                    }, 200); // Debounce de 200ms para evitar múltiples llamadas
                });
                
                notificacionBienvenidaObserver.observe(alert, {
                    attributes: true,
                    attributeFilter: ['class']
                });
                
                // También detectar cuando se hace click en el botón de cerrar
                const btnCerrar = alert.querySelector('.btn-close');
                if (btnCerrar) {
                    notificacionBienvenidaEventListener = function() {
                        setTimeout(function() {
                            console.log('✅ Notificación de bienvenida cerrada (botón), desactivando input "Mensaje"');
                            activarInputMensaje(false);
                            notificacionBienvenidaProcesada = false; // Permitir procesar de nuevo si aparece otra vez
                        }, 300);
                    };
                    btnCerrar.addEventListener('click', notificacionBienvenidaEventListener);
                }
            }
        }
    } else {
        // Ya fue procesada, NO resetear el flag hasta que realmente se cierre
        // Esto previene que se procese múltiples veces mientras está abierta
        const notificacionBienvenida = document.getElementById('notificacionBienvenida');
        if (notificacionBienvenida) {
            const alert = notificacionBienvenida.querySelector('.alert');
            const estaVisible = notificacionBienvenida.style.display !== 'none' && 
                               getComputedStyle(notificacionBienvenida).display !== 'none' &&
                               alert && alert.classList.contains('show');
            // Solo resetear si realmente está cerrada y no visible
            if (!estaVisible) {
                // La notificación ya no está visible, permitir procesarla de nuevo si aparece
                notificacionBienvenidaProcesada = false;
                if (notificacionBienvenidaObserver) {
                    notificacionBienvenidaObserver.disconnect();
                    notificacionBienvenidaObserver = null;
                }
                if (notificacionBienvenidaEventListener) {
                    notificacionBienvenidaEventListener = null;
                }
            }
        }
    }
    
        const mensajes = document.querySelectorAll('.mensaje-flash');
        if (mensajes.length === 0) {
            console.log('📭 No hay mensajes flash para procesar');
            // NO resetear flag manualmente - el finally lo hará
            return;
        }
    
    console.log(`📢 Procesando ${mensajes.length} mensaje(s) flash existente(s) después de que RIVE se cargó...`);
    
    mensajes.forEach(function(mensaje) {
        // Verificar si el mensaje aún está visible
        if (!mensaje.classList.contains('show') || mensaje.style.display === 'none') {
            return; // Saltar mensajes que ya no están visibles
        }
        
        const texto = mensaje.getAttribute('data-message') || mensaje.textContent.trim();
        const categoria = mensaje.getAttribute('data-category') || 'info';
        
        if (texto) {
            // Evitar procesar el mismo mensaje múltiples veces
            if (mensajesFlashProcesados.has(texto)) {
                console.log('ℹ️ Mensaje flash ya procesado, ignorando:', texto);
                return;
            }
            
            if (esMensajeLoginCritico(texto)) {
                console.log('ℹ️ Mensaje de error crítico detectado en login (procesarMensajesFlashExistentes):', texto);
                // Marcar como procesado para evitar intentos futuros
                mensajesFlashProcesados.add(texto);
                return;
            }
            
            // En login, no procesar mensajes flash (solo se procesan mensajes de error críticos que ya están manejados por Sin_Permiso)
            const esLoginContexto = typeof window.ASISTENTE_AUTH === 'undefined' || window.ASISTENTE_AUTH !== true;
            if (esLoginContexto) {
                console.log('ℹ️ En login, no se procesan mensajes flash normales (solo errores críticos):', texto);
                mensajesFlashProcesados.add(texto);
                return;
            }

            console.log('📢 Activando input "Mensaje" para mensaje flash existente:', texto);
            mensajesFlashProcesados.add(texto);
            activarInputMensaje(true, texto);
            
            // Observar cuando el mensaje se cierra o desaparece
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        // Verificar si el mensaje ya no está visible
                        if (!mensaje.classList.contains('show') || 
                            mensaje.style.display === 'none' || 
                            !document.body.contains(mensaje)) {
                            console.log('✅ Mensaje flash cerrado, desactivando input "Mensaje"');
                            activarInputMensaje(false);
                            observer.disconnect();
                        }
                    }
                });
            });
            
            observer.observe(mensaje, {
                attributes: true,
                attributeFilter: ['class', 'style'],
                childList: false,
                subtree: false
            });
            
            // También detectar cuando se hace click en el botón de cerrar
            const btnCerrar = mensaje.querySelector('.btn-close');
            if (btnCerrar) {
                btnCerrar.addEventListener('click', function() {
                    setTimeout(function() {
                        console.log('✅ Mensaje flash cerrado (botón), desactivando input "Mensaje"');
                        activarInputMensaje(false);
                    }, 300); // Esperar a que Bootstrap termine la animación
                });
            }
            
            // Auto-desactivar después de un tiempo (por si acaso)
            setTimeout(function() {
                if (document.body.contains(mensaje)) {
                    console.log('⏰ Timeout: desactivando input "Mensaje" después de 5 segundos');
                    activarInputMensaje(false);
                }
            }, 5000);
        }
    });
    
    } catch (error) {
        console.error('❌ Error en procesarMensajesFlashExistentes:', error);
    } finally {
        // Siempre resetear el flag al final
        procesandoMensajesFlash = false;
    }
}

/**
 * Activar/desactivar el input "Mensaje" en la state machine de RIVE y pasar el texto
 * @param {boolean} activar - true para activar (mostrar mensaje), false para desactivar
 * @param {string} textoMensaje - El texto del mensaje a mostrar (solo cuando activar es true)
 */
function activarInputMensaje(activar, textoMensaje = '', forzarMostrar = false) {
    // Log del intento de activación
    console.log(`📝 activarInputMensaje llamado: activar=${activar}, textoMensaje="${textoMensaje}", forzarMostrar=${forzarMostrar}`);
    
    // Evitar procesar el mismo mensaje múltiples veces (debounce)
    const mensajeKey = `${activar}_${textoMensaje}`;
    
    // Verificación TEMPRANA: Si es el mismo mensaje que ya se está procesando, ignorar INMEDIATAMENTE
    // IMPORTANTE: Verificar tanto el mensaje como el flag de procesamiento
    if (procesandoMensaje) {
        if (mensajeKey === ultimoMensajeProcesado) {
            console.log('⚠️ Mismo mensaje ya está siendo procesado, ignorando llamada duplicada');
            return;
        }
        // Si hay otro mensaje diferente siendo procesado, también ignorar
        console.log('⚠️ Ya se está procesando otro mensaje, ignorando esta llamada');
        return;
    }
    
    // NO enviar mensajes a RIVE si el panel del asistente está abierto
    // EXCEPTO si es un mensaje del sistema (flash messages) que deben mostrarse siempre
    // O si es un mensaje explícito del panel (como el mensaje inicial o de confirmación)
    // O si se fuerza a mostrar (forzarMostrar = true)
    const esMensajeDelPanel = textoMensaje && (
        textoMensaje.includes('Selecciona el tipo de mensaje') ||
        textoMensaje.includes('Mensaje enviado') ||
        textoMensaje.includes('Se te responderá') ||
        textoMensaje.includes('El equipo del laboratorio recibirá tu mensaje') ||
        textoMensaje.includes('Muchas Gracias')
    );
    
    if (typeof asistenteAbierto !== 'undefined' && asistenteAbierto === true && !esMensajeDelPanel && !forzarMostrar) {
        console.log('📭 Panel del asistente abierto, no se envían mensajes a RIVE (excepto mensajes del panel)');
        // NO resetear procesandoMensaje aquí porque nunca se estableció en este caso
        return;
    }
    
    // La verificación de procesandoMensaje ya se hizo al inicio de la función
    // No necesitamos verificarla de nuevo aquí
    
    // Limpiar timeout si existe
    if (timeoutProcesandoMensaje) {
        clearTimeout(timeoutProcesandoMensaje);
        timeoutProcesandoMensaje = null;
    }
    
    // ESTABLECER FLAG INMEDIATAMENTE después de todas las verificaciones tempranas
    // Esto previene que otras llamadas entren mientras se procesa
    procesandoMensaje = true;
    
    // Marcar el mensaje como procesado
    ultimoMensajeProcesado = mensajeKey;
    
    // Resetear contador de reintentos si es un nuevo mensaje (no un reintento)
    if (activar && textoMensaje && reintentosMensajeAvatar > 0 && !textoMensaje.includes('Selecciona el tipo de mensaje')) {
        // Solo resetear si no es el mensaje inicial
        reintentosMensajeAvatar = 0;
    }
    
    // Si se activa un mensaje, desactivar los otros inputs primero
    // IMPORTANTE: Solo desactivar si realmente necesitamos activar el mensaje
    // No desactivar si ya está activo el mismo mensaje para evitar bucles
    if (activar && (mensajeKey !== ultimoMensajeProcesado || !procesandoMensaje)) {
        console.log('📝 [MENSAJE] Desactivando otros inputs antes de activar Mensaje');
        // Solo desactivar ERROR si está activo, no siempre (para evitar bucles)
        if (typeof activarInputError === 'function') {
            // Verificar si ERROR está activo antes de desactivarlo
            try {
                if (riveButtonStateMachine && Array.isArray(riveButtonStateMachine)) {
                    const inputError = riveButtonStateMachine.find(input => 
                        input.name && input.name.toLowerCase() === 'error'
                    );
                    if (inputError && inputError.value === true) {
                        activarInputError(false);
                    }
                }
            } catch (e) {
                // Si hay error, simplemente no hacer nada
            }
        }
        // NO desactivar Sin_Permiso desde aquí para evitar bucles
        // activarInputSinPermiso solo debe activarse/desactivarse desde la lógica de autenticación
    }
    
    // Verificar que RIVE esté completamente cargado antes de intentar
    if (typeof rive === 'undefined') {
        console.warn('⚠️ RIVE no está cargado aún, esperando...');
        // IMPORTANTE: NO resetear el flag aquí - mantenerlo activo para prevenir otras llamadas
        // El flag se reseteará después de que se complete el reintento
        setTimeout(() => {
            // Verificar que no estemos procesando el mismo mensaje antes de reintentar
            const mensajeKeyRecursivo = `${activar}_${textoMensaje}`;
            if (mensajeKeyRecursivo === ultimoMensajeProcesado) {
                // Mismo mensaje, continuar con el reintento
                activarInputMensaje(activar, textoMensaje, forzarMostrar);
            } else {
                // Mensaje diferente o flag reseteado, resetear antes de reintentar
                procesandoMensaje = false;
                ultimoMensajeProcesado = '';
                activarInputMensaje(activar, textoMensaje, forzarMostrar);
            }
        }, 1000);
        return;
    }
    
    // Esperar un momento para asegurar que RIVE esté completamente cargado
    setTimeout(function() {
        try {
            // Intentar con el botón flotante primero
            if (riveButtonInstance && riveButtonStateMachine && Array.isArray(riveButtonStateMachine)) {
                // Log de todos los inputs disponibles para depuración
                console.log('🔍 [BOTÓN] Inputs disponibles en la state machine:', 
                    riveButtonStateMachine.map(input => ({
                        name: input.name,
                        type: input.type,
                        value: input.value
                    }))
                );
                
                const inputMensaje = riveButtonStateMachine.find(input => 
                    input.name === 'Mensaje' || 
                    input.name === 'mensaje' || 
                    input.name === 'message'
                );
                
                if (inputMensaje) {
                    // Si es un input boolean, establecer el valor
                    if (typeof inputMensaje.value !== 'undefined') {
                        inputMensaje.value = activar;
                        console.log(`✅ [BOTÓN] Input "Mensaje" establecido a: ${activar}`);
                        console.log(`📝 [BOTÓN] Texto recibido: "${textoMensaje}"`);
                        
                        // Si se desactiva el mensaje, restablecer "atencion" a true
                        if (!activar) {
                            const inputAtencion = riveButtonStateMachine.find(input => {
                                const name = input.name || '';
                                return name.toLowerCase() === 'atencion' || name.toLowerCase() === 'atención';
                            });
                            if (inputAtencion && typeof inputAtencion.value !== 'undefined') {
                                inputAtencion.value = true;
                                console.log(`✅ [BOTÓN] Input "atencion" restablecido a: true (mensaje desactivado)`);
                            }
                        }
                        
                        // Si hay texto y el input tiene una propiedad para texto (Data Binding)
                        if (activar && textoMensaje && textoMensaje.trim() !== '') {
                            console.log(`📝 [BOTÓN] Intentando establecer texto del mensaje: "${textoMensaje}"`);
                            
                            // Intentar usar setTextRunValue (método recomendado por RIVE)
                            if (riveButtonInstance && typeof riveButtonInstance.setTextRunValue === 'function') {
                                // Lista de nombres posibles a intentar
                                const nombresPosibles = [
                                    'Texto_mensaje',
                                    'texto_mensaje',
                                    'Texto Mensaje',
                                    'texto mensaje',
                                    'Mensaje',
                                    'mensaje',
                                    'Message',
                                    'message'
                                ];
                                
                                let textoEstablecido = false;
                                
                                // Intentar con cada nombre posible
                                for (const nombre of nombresPosibles) {
                                    try {
                                        // Verificar si el text run existe antes de intentar establecerlo
                                        // setTextRunValue puede no lanzar excepción pero mostrar warning
                                        const errorHandler = (error) => {
                                            console.warn(`⚠️ [BOTÓN] Error al usar setTextRunValue con nombre "${nombre}":`, error);
                                        };
                                        
                                        // Intentar establecer el valor
                                        riveButtonInstance.setTextRunValue(nombre, textoMensaje);
                                        
                                        // Verificar después de un breve delay si el valor se estableció correctamente
                                        // Esto es necesario porque setTextRunValue puede no lanzar excepción
                                        setTimeout(() => {
                                            try {
                                                const valorActual = riveButtonInstance.getTextRunValue ? riveButtonInstance.getTextRunValue(nombre) : null;
                                                if (valorActual === textoMensaje) {
                                                    console.log(`✅ [BOTÓN] Texto del mensaje establecido correctamente con nombre "${nombre}": "${textoMensaje}"`);
                                                    textoEstablecido = true;
                                                } else {
                                                    console.warn(`⚠️ [BOTÓN] El texto no se estableció correctamente con nombre "${nombre}". Valor actual: "${valorActual}"`);
                                                }
                                            } catch (e) {
                                                console.warn(`⚠️ [BOTÓN] No se pudo verificar el texto con nombre "${nombre}":`, e);
                                            }
                                        }, 100);
                                        
                                        // Asumir éxito temporalmente (se verificará después)
                                        console.log(`📝 [BOTÓN] Intentado establecer texto con nombre "${nombre}"`);
                                        break; // Intentar solo el primer nombre por ahora
                                    } catch (e) {
                                        // Continuar con el siguiente nombre
                                        console.log(`⚠️ [BOTÓN] Excepción al usar setTextRunValue con nombre "${nombre}":`, e.message || e);
                                    }
                                }
                                
                                // Esperar un poco más para verificar si se estableció
                                setTimeout(() => {
                                    if (!textoEstablecido) {
                                        console.warn('⚠️ [BOTÓN] No se pudo establecer el texto con ningún nombre. Verifica que el text run esté renombrado en RIVE.');
                                        console.warn('⚠️ [BOTÓN] IMPORTANTE: En el editor de RIVE, selecciona el text run "Texto_mensaje" y renómbralo en el panel de propiedades para que sea "queryable at runtime".');
                                        // Intentar listar los text runs disponibles si hay un método para hacerlo
                                        try {
                                            if (riveButtonContent) {
                                                const artboard = riveButtonContent.defaultArtboard();
                                                if (artboard && artboard.textRuns) {
                                                    console.log('🔍 [BOTÓN] Text runs disponibles:', artboard.textRuns.map(tr => tr.name || 'sin nombre'));
                                                }
                                            }
                                        } catch (e) {
                                            console.warn('⚠️ [BOTÓN] No se pudieron listar los text runs:', e);
                                        }
                                    }
                                }, 500);
                            } else {
                                console.warn('⚠️ [BOTÓN] setTextRunValue no está disponible en riveButtonInstance');
                            }
                        }
                    } else if (inputMensaje.type === 'trigger' && typeof inputMensaje.fire === 'function') {
                        // Si es un trigger, solo dispararlo cuando activar es true
                        if (activar) {
                            inputMensaje.fire();
                            console.log(`✅ [BOTÓN] Trigger "Mensaje" activado`);
                        }
                    }
                } else {
                    console.warn('⚠️ [BOTÓN] Input "Mensaje" no encontrado');
                }
            }
            
            // Intentar también con el avatar del chat
            // Si riveInstance no está disponible, intentar obtenerlo de window
            const avatarInstance = riveInstance || window.riveInstance;
            let avatarStateMachine = riveStateMachine || window.riveStateMachine;
            
            // Si aún no tenemos la state machine, intentar obtenerla directamente del avatarInstance
            if (avatarInstance && (!avatarStateMachine || !Array.isArray(avatarStateMachine))) {
                try {
                    if (typeof avatarInstance.stateMachineInputs === 'function') {
                        const inputs = avatarInstance.stateMachineInputs('State Machine 1');
                        if (inputs && Array.isArray(inputs)) {
                            avatarStateMachine = inputs;
                            riveStateMachine = inputs;
                            window.riveStateMachine = inputs;
                            console.log('✅ [AVATAR] State Machine inputs obtenidos directamente del avatarInstance:', inputs.length);
                        }
                    }
                } catch (e) {
                    console.warn('⚠️ [AVATAR] Error al obtener inputs directamente del avatarInstance:', e);
                }
            }
            
            if (avatarInstance && avatarStateMachine && Array.isArray(avatarStateMachine)) {
                // Log de todos los inputs disponibles para depuración
                console.log('🔍 [AVATAR] Inputs disponibles en la state machine:', 
                    avatarStateMachine.map(input => ({
                        name: input.name,
                        type: input.type,
                        value: input.value
                    }))
                );
                
                const inputMensaje = avatarStateMachine.find(input => 
                    input.name === 'Mensaje' || 
                    input.name === 'mensaje' || 
                    input.name === 'message'
                );
                
                if (inputMensaje) {
                    // Si es un input boolean, establecer el valor
                    if (typeof inputMensaje.value !== 'undefined') {
                        inputMensaje.value = activar;
                        console.log(`✅ [AVATAR] Input "Mensaje" establecido a: ${activar}`);
                        console.log(`📝 [AVATAR] Texto recibido: "${textoMensaje}"`);
                        
                        // Si se desactiva el mensaje, restablecer "atencion" a true
                        if (!activar && avatarStateMachine && Array.isArray(avatarStateMachine)) {
                            const inputAtencion = avatarStateMachine.find(input => {
                                const name = input.name || '';
                                return name.toLowerCase() === 'atencion' || name.toLowerCase() === 'atención';
                            });
                            if (inputAtencion && typeof inputAtencion.value !== 'undefined') {
                                inputAtencion.value = true;
                                console.log(`✅ [AVATAR] Input "atencion" restablecido a: true (mensaje desactivado)`);
                            }
                        }
                        
                        // Si hay texto y el input tiene una propiedad para texto
                        if (activar && textoMensaje && textoMensaje.trim() !== '') {
                            console.log(`📝 [AVATAR] Intentando establecer texto del mensaje: "${textoMensaje}"`);
                            
                            // Intentar usar setTextRunValue (método recomendado por RIVE)
                            if (avatarInstance && typeof avatarInstance.setTextRunValue === 'function') {
                                // Lista de nombres posibles a intentar
                                const nombresPosibles = [
                                    'Texto_mensaje',
                                    'texto_mensaje',
                                    'Texto Mensaje',
                                    'texto mensaje',
                                    'Mensaje',
                                    'mensaje',
                                    'Message',
                                    'message'
                                ];
                                
                                let textoEstablecido = false;
                                
                                // Intentar con cada nombre posible
                                for (const nombre of nombresPosibles) {
                                    try {
                                        // Intentar establecer el valor
                                        avatarInstance.setTextRunValue(nombre, textoMensaje);
                                        
                                        // Verificar después de un breve delay si el valor se estableció correctamente
                                        setTimeout(() => {
                                            try {
                                                const valorActual = avatarInstance.getTextRunValue ? avatarInstance.getTextRunValue(nombre) : null;
                                                if (valorActual === textoMensaje) {
                                                    console.log(`✅ [AVATAR] Texto del mensaje establecido correctamente con nombre "${nombre}": "${textoMensaje}"`);
                                                    textoEstablecido = true;
                                                } else {
                                                    console.warn(`⚠️ [AVATAR] El texto no se estableció correctamente con nombre "${nombre}". Valor actual: "${valorActual}"`);
                                                }
                                            } catch (e) {
                                                console.warn(`⚠️ [AVATAR] No se pudo verificar el texto con nombre "${nombre}":`, e);
                                            }
                                        }, 100);
                                        
                                        // Asumir éxito temporalmente (se verificará después)
                                        console.log(`📝 [AVATAR] Intentado establecer texto con nombre "${nombre}"`);
                                        break; // Intentar solo el primer nombre por ahora
                                    } catch (e) {
                                        // Continuar con el siguiente nombre
                                        console.log(`⚠️ [AVATAR] Excepción al usar setTextRunValue con nombre "${nombre}":`, e.message || e);
                                    }
                                }
                                
                                // Esperar un poco más para verificar si se estableció
                                setTimeout(() => {
                                    if (!textoEstablecido) {
                                        console.warn('⚠️ [AVATAR] No se pudo establecer el texto con ningún nombre. Verifica que el text run esté renombrado en RIVE.');
                                        console.warn('⚠️ [AVATAR] IMPORTANTE: En el editor de RIVE, selecciona el text run "Texto_mensaje" y renómbralo en el panel de propiedades para que sea "queryable at runtime".');
                                        // Intentar listar los text runs disponibles si hay un método para hacerlo
                                        try {
                                            if (riveContent) {
                                                const artboard = riveContent.defaultArtboard();
                                                if (artboard && artboard.textRuns) {
                                                    console.log('🔍 [AVATAR] Text runs disponibles:', artboard.textRuns.map(tr => tr.name || 'sin nombre'));
                                                }
                                            }
                                        } catch (e) {
                                            console.warn('⚠️ [AVATAR] No se pudieron listar los text runs:', e);
                                        }
                                    }
                                }, 500);
                            } else {
                                console.warn('⚠️ [AVATAR] setTextRunValue no está disponible en riveInstance. Estado:', {
                                    tieneRiveInstance: !!avatarInstance,
                                    tieneSetTextRunValue: avatarInstance && typeof avatarInstance.setTextRunValue === 'function'
                                });
                                
                                // Si RIVE no está listo, intentar de nuevo después de un delay
                                // IMPORTANTE: Verificar el flag antes de llamar recursivamente
                                if (!avatarInstance && activar && textoMensaje) {
                                    console.log('⏳ [AVATAR] RIVE no está listo, reintentando en 1 segundo...');
                                    setTimeout(() => {
                                        // Verificar que no estemos procesando el mismo mensaje
                                        const mensajeKeyRecursivo = `${activar}_${textoMensaje}`;
                                        if (!procesandoMensaje || mensajeKeyRecursivo !== ultimoMensajeProcesado) {
                                            activarInputMensaje(activar, textoMensaje);
                                        } else {
                                            console.log('⚠️ [AVATAR] Ya se está procesando este mensaje, no se reintentará');
                                        }
                                    }, 1000);
                                }
                            }
                        }
                    } else if (inputMensaje.type === 'trigger' && typeof inputMensaje.fire === 'function') {
                        // Si es un trigger, solo dispararlo cuando activar es true
                        if (activar) {
                            inputMensaje.fire();
                            console.log(`✅ [AVATAR] Trigger "Mensaje" activado`);
                        }
                    }
                } else {
                    console.warn('⚠️ [AVATAR] Input "Mensaje" no encontrado');
                }
            } else {
                // Si el avatar no está disponible, intentar de nuevo después de un delay
                // PERO solo si no hemos excedido el límite de reintentos
                if (activar && textoMensaje && reintentosMensajeAvatar < MAX_REINTENTOS_MENSAJE_AVATAR) {
                    reintentosMensajeAvatar++;
                    console.log(`⏳ [AVATAR] RIVE del avatar no está disponible aún, reintentando en 1 segundo... (${reintentosMensajeAvatar}/${MAX_REINTENTOS_MENSAJE_AVATAR})`, {
                        tieneRiveInstance: !!avatarInstance,
                        tieneStateMachine: !!avatarStateMachine
                    });
                    setTimeout(() => {
                        // IMPORTANTE: Verificar el flag antes de llamar recursivamente
                        const mensajeKeyRecursivo = `${activar}_${textoMensaje}`;
                        if (!procesandoMensaje || mensajeKeyRecursivo !== ultimoMensajeProcesado) {
                            activarInputMensaje(activar, textoMensaje);
                        } else {
                            console.log('⚠️ [AVATAR] Ya se está procesando este mensaje, no se reintentará');
                            reintentosMensajeAvatar = 0; // Resetear contador ya que no se reintentará
                        }
                    }, 1000);
                } else if (reintentosMensajeAvatar >= MAX_REINTENTOS_MENSAJE_AVATAR) {
                    console.warn('⚠️ [AVATAR] Se alcanzó el límite de reintentos para establecer el mensaje en el avatar. El mensaje se estableció en el botón pero no en el avatar del panel.');
                    // Guardar el mensaje como pendiente para cuando el avatar esté listo
                    if (activar && textoMensaje) {
                        window.mensajePendienteAvatar = textoMensaje;
                        console.log('💾 Mensaje guardado como pendiente para cuando el avatar esté listo:', textoMensaje);
                    }
                    reintentosMensajeAvatar = 0; // Resetear contador
                }
            }
            
            // IMPORTANTE: Resetear flag SOLO cuando todo el proceso asíncrono termine
            // Esperar más tiempo para asegurar que todos los timeouts anidados también terminen
            setTimeout(() => {
                procesandoMensaje = false;
                // NO resetear ultimoMensajeProcesado aquí para evitar procesar el mismo mensaje de nuevo
                // ultimoMensajeProcesado se resetea solo cuando se procesa un mensaje diferente
            }, 1500); // Esperar 1.5 segundos para que todos los timeouts anidados terminen
            
        } catch (error) {
            console.error('❌ Error al activar input "Mensaje":', error);
            // Resetear flag en caso de error
            setTimeout(() => {
                procesandoMensaje = false;
            }, 500);
        }
        // NO usar finally aquí - el flag se resetea dentro del setTimeout
    }, 500); // Esperar 500ms para asegurar que RIVE esté listo
}

/**
 * Cargar librería RIVE desde CDN
 */
function cargarLibreriaRIVE() {
    return new Promise((resolve, reject) => {
        if (typeof rive !== 'undefined') {
            console.log('✅ RIVE ya está cargado, no es necesario cargarlo de nuevo');
            resolve();
            return;
        }
        
        console.log('📦 Cargando librería RIVE desde CDN...');
        
        const existingScript = document.querySelector('script[src*="rive"]');
        if (existingScript) {
            console.log('⚠️ Script RIVE ya existe, esperando a que cargue...');
            existingScript.addEventListener('load', () => {
                console.log('✅ Script RIVE existente cargado');
                resolve();
            });
            existingScript.addEventListener('error', () => {
                console.error('❌ Error en script RIVE existente');
                reject(new Error('Error en script RIVE existente'));
            });
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/@rive-app/canvas@latest/rive.js';
        script.onload = () => {
            if (typeof rive !== 'undefined') {
                console.log('✅ Librería RIVE cargada correctamente');
                resolve();
            } else {
                console.error('❌ RIVE se cargó pero typeof rive es undefined');
                reject(new Error('RIVE se cargó pero no está disponible'));
            }
        };
        script.onerror = (error) => {
            console.error('❌ Error cargando librería RIVE:', error);
            mostrarAvatarPorDefecto();
            reject(new Error('No se pudo cargar la librería RIVE'));
        };
        document.head.appendChild(script);
    });
}

/**
 * Mostrar avatar por defecto (icono) si RIVE no está disponible
 */
function mostrarAvatarPorDefecto() {
    const container = document.getElementById('chat-avatar-container');
    if (container) {
        container.innerHTML = `
            <div class="chat-avatar" style="width: 120px; height: 120px; margin: 0 auto;">
                <i class="bi bi-robot" style="font-size: 4rem; color: #667eea;"></i>
            </div>
        `;
    }
}

/**
 * Cambiar el estado del avatar RIVE
 */
function cambiarEstadoAvatar(estado) {
    if (!riveStateMachine || !riveInstance) {
        return;
    }
    
    try {
        const stateInput = riveStateMachine.find(input => input.name === estado || input.name === 'Estado');
        if (stateInput) {
            if (stateInput.type === rive.StateMachineInputType.Number) {
                stateInput.value = 1;
            } else if (stateInput.type === rive.StateMachineInputType.Boolean) {
                stateInput.value = true;
            } else if (stateInput.type === rive.StateMachineInputType.Trigger) {
                stateInput.fire();
            }
        }
    } catch (error) {
        console.warn('Error cambiando estado del avatar:', error);
    }
}

/**
 * Enviar mensaje al chat
 */
// Variable global para almacenar imágenes seleccionadas
let imagenesChatSeleccionadas = [];

/**
 * Procesar imágenes seleccionadas para el chat
 */
window.procesarImagenesChat = function procesarImagenesChat(event) {
    const files = event.target.files;
    const previewContainer = document.getElementById('chat-imagenes-container');
    const previewArea = document.getElementById('chat-imagenes-preview');
    
    if (!previewContainer || !previewArea) return;
    
    // Limpiar imágenes anteriores si se selecciona nuevo set
    if (imagenesChatSeleccionadas.length === 0) {
        previewContainer.innerHTML = '';
    }
    
    // Limitar a 5 imágenes máximo
    const maxImagenes = 5;
    const totalImagenes = imagenesChatSeleccionadas.length + files.length;
    
    if (totalImagenes > maxImagenes) {
        if (typeof activarInputError === 'function') {
            activarInputError(true, `Se pueden adjuntar máximo ${maxImagenes} imágenes a la vez`);
            setTimeout(() => activarInputError(false), 3000);
        }
        return;
    }
    
    Array.from(files).forEach((file) => {
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                const imagenData = {
                    data: e.target.result, // data:image/png;base64,...
                    media_type: file.type,
                    nombre: file.name
                };
                
                imagenesChatSeleccionadas.push(imagenData);
                
                // Crear preview
                const previewDiv = document.createElement('div');
                previewDiv.className = 'chat-imagen-preview';
                previewDiv.dataset.nombre = file.name;
                
                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = file.name;
                
                const removeBtn = document.createElement('button');
                removeBtn.className = 'chat-imagen-remove';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = function() {
                    const nombre = previewDiv.dataset.nombre;
                    imagenesChatSeleccionadas = imagenesChatSeleccionadas.filter(
                        img => img.nombre !== nombre
                    );
                    previewDiv.remove();
                    
                    if (imagenesChatSeleccionadas.length === 0) {
                        previewArea.style.display = 'none';
                    }
                };
                
                previewDiv.appendChild(img);
                previewDiv.appendChild(removeBtn);
                previewContainer.appendChild(previewDiv);
                
                previewArea.style.display = 'block';
            };
            
            reader.readAsDataURL(file);
        }
    });
    
    // Limpiar el input para permitir seleccionar la misma imagen de nuevo
    event.target.value = '';
};

/**
 * Enviar mensaje al chat
 */
window.enviarMensajeChat = async function enviarMensajeChat() {
    const input = document.getElementById('chat-input');
    const mensaje = (input.value || '').trim();
    const btnEnviar = document.querySelector('button[onclick="enviarMensajeChat()"]');
    
    if (!input) {
        console.error('No se encontró el input del chat');
        if (typeof activarInputError === 'function') {
            activarInputError(true, 'Error: No se encontró el campo de entrada del chat');
        }
        return;
    }
    
    // Validar: debe haber mensaje (min 2 caracteres) o al menos una imagen
    if ((!mensaje || mensaje.length < 2) && (!imagenesChatSeleccionadas || imagenesChatSeleccionadas.length === 0)) {
        // Mostrar error a través del avatar RIVE en lugar de alert
        if (typeof activarInputError === 'function') {
            activarInputError(true, 'El mensaje debe tener al menos 2 caracteres o incluir al menos una imagen');
            // Desactivar el error después de 3 segundos
            setTimeout(() => {
                activarInputError(false);
            }, 3000);
        } else {
            // Fallback si RIVE no está disponible
            alert('El mensaje debe tener al menos 2 caracteres o incluir al menos una imagen');
        }
        return;
    }
    
    // Validar mensaje si existe (solo si no hay imágenes)
    if (mensaje && mensaje.length < 2 && (!imagenesChatSeleccionadas || imagenesChatSeleccionadas.length === 0)) {
        if (typeof activarInputError === 'function') {
            activarInputError(true, 'El mensaje debe tener al menos 2 caracteres');
            setTimeout(() => activarInputError(false), 3000);
        } else {
            alert('El mensaje debe tener al menos 2 caracteres');
        }
        return;
    }
    
    // Activar estado de escucha
    activarInputEscuchando(true);
    input.disabled = true;
    if (btnEnviar) btnEnviar.disabled = true;
    
    // Limpiar input y preview de imágenes
    const imagenesParaEnviar = [...imagenesChatSeleccionadas];
    input.value = '';
    imagenesChatSeleccionadas = [];
    const previewContainer = document.getElementById('chat-imagenes-container');
    const previewArea = document.getElementById('chat-imagenes-preview');
    if (previewContainer) previewContainer.innerHTML = '';
    if (previewArea) previewArea.style.display = 'none';
    
    // Agregar mensaje del usuario con imágenes si las hay
    agregarMensajeChat('usuario', mensaje || (imagenesParaEnviar.length > 0 ? '📷 [Imagen(es) adjunta(s)]' : ''), imagenesParaEnviar);
    
    // Mostrar que está pensando
    mostrarEscribiendo(true);
    
    try {
        const bodyData = {
            mensaje: mensaje || '',
            protocolo_id: typeof protocoloIdActual !== 'undefined' ? protocoloIdActual : null,
            historial_ids: typeof historialChatIds !== 'undefined' ? historialChatIds : [],
            tipo_estudio: typeof obtenerTipoEstudio === 'function' ? obtenerTipoEstudio() : ''
        };
        
        // Agregar imágenes si existen
        if (imagenesParaEnviar && imagenesParaEnviar.length > 0) {
            bodyData.imagenes = imagenesParaEnviar;
        }
        
        const response = await fetch('/asistente/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(bodyData)
        });
        
        const data = await response.json();
        mostrarEscribiendo(false);
        activarInputEscuchando(false);
        
        if (data.success) {
            // Desactivar cualquier error activo si hay éxito
            if (typeof activarInputError === 'function') {
                activarInputError(false);
            }
            
            agregarMensajeChat('asistente', data.respuesta);
            
            // Procesar acciones si existen
            if (data.acciones && Array.isArray(data.acciones) && data.acciones.length > 0) {
                procesarAccionesChat(data.acciones, data.intencion);
            }
            
            // Actualizar estado de Claude
            if (data.claude_disponible !== undefined) {
                actualizarEstadoClaude(data.claude_disponible);
            }
        } else {
            const mensajeError = data.error || 'No se pudo procesar el mensaje';
            const textoError = data.claude_disponible === false 
                ? `${mensajeError}. El asistente inteligente no está disponible en este momento.`
                : `Error: ${mensajeError}`;
            
            // Mostrar error a través del avatar RIVE
            if (typeof activarInputError === 'function') {
                activarInputError(true, textoError);
                // Desactivar el error después de 5 segundos
                setTimeout(() => {
                    activarInputError(false);
                }, 5000);
            }
            
            // También agregar mensaje al chat para referencia
            if (data.claude_disponible === false) {
                agregarMensajeChat('asistente', `⚠️ ${mensajeError}\n\nEl asistente inteligente no está disponible en este momento. Puedes usar las otras pestañas del asistente (Buscar, Plantillas, Frecuentes).`);
            } else {
                agregarMensajeChat('asistente', `❌ Error: ${mensajeError}`);
            }
            
            if (data.claude_disponible !== undefined) {
                actualizarEstadoClaude(data.claude_disponible);
            }
        }
        
    } catch (error) {
        console.error('Error enviando mensaje:', error);
        mostrarEscribiendo(false);
        activarInputEscuchando(false);
        
        const textoError = `Error de conexión: ${error.message}. Por favor verifica tu conexión e intenta nuevamente.`;
        
        // Mostrar error a través del avatar RIVE
        if (typeof activarInputError === 'function') {
            activarInputError(true, textoError);
            // Desactivar el error después de 5 segundos
            setTimeout(() => {
                activarInputError(false);
            }, 5000);
        }
        
        // También agregar mensaje al chat para referencia
        agregarMensajeChat('asistente', `❌ ${textoError}`);
    } finally {
        input.disabled = false;
        if (btnEnviar) btnEnviar.disabled = false;
        input.focus();
    }
}

/**
 * Agregar mensaje al chat
 */
function agregarMensajeChat(tipo, contenido, imagenes = null) {
    const contenedor = document.getElementById('chat-mensajes');
    if (!contenedor) return;
    
    const bienvenida = contenedor.querySelector('.chat-bienvenida');
    if (bienvenida) {
        bienvenida.style.display = 'none';
    }
    
    const mensajeDiv = document.createElement('div');
    mensajeDiv.className = `chat-mensaje chat-mensaje-${tipo}`;
    
    const fecha = new Date();
    const fechaTexto = fecha.toLocaleTimeString('es-AR', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    // Construir HTML de imágenes si existen
    let imagenesHTML = '';
    if (imagenes && Array.isArray(imagenes) && imagenes.length > 0) {
        imagenesHTML = '<div class="chat-mensaje-imagenes d-flex flex-wrap gap-2 mt-2">';
        imagenes.forEach((imagen) => {
            if (imagen.data) {
                imagenesHTML += `
                    <div class="chat-mensaje-imagen">
                        <img src="${imagen.data}" alt="${imagen.nombre || 'Imagen'}" style="max-width: 100%; height: auto; border-radius: 8px;">
                    </div>
                `;
            }
        });
        imagenesHTML += '</div>';
    }
    
    if (tipo === 'usuario') {
        mensajeDiv.innerHTML = `
            <div class="chat-burbuja">
                ${escapeHtml(contenido)}
                ${imagenesHTML}
            </div>
            <div class="chat-mensaje-fecha">${fechaTexto}</div>
        `;
    } else {
        mensajeDiv.innerHTML = `
            <div class="chat-avatar">
                <i class="bi bi-robot"></i>
            </div>
            <div class="chat-burbuja">
                ${formatearRespuesta(contenido)}
            </div>
            <div class="chat-mensaje-fecha">${fechaTexto}</div>
        `;
    }
    
    contenedor.appendChild(mensajeDiv);
    contenedor.scrollTop = contenedor.scrollHeight;
}

/**
 * Formatear respuesta del asistente (markdown básico)
 */
function formatearRespuesta(texto) {
    texto = escapeHtml(texto);
    texto = texto.replace(/\n/g, '<br>');
    texto = texto.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    texto = texto.replace(/\*(.*?)\*/g, '<em>$1</em>');
    texto = texto.replace(/`(.*?)`/g, '<code>$1</code>');
    return texto;
}

/**
 * Escapar HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Mostrar/ocultar indicador de escritura
 */
function mostrarEscribiendo(mostrar) {
    const indicador = document.getElementById('chat-escribiendo');
    if (indicador) {
        indicador.style.display = mostrar ? 'block' : 'none';
    }
}

/**
 * Cargar historial de chat
 */
async function cargarHistorialChat() {
    try {
        let url = '/asistente/chat/historial?limite=20';
        if (protocoloIdActual) {
            url += `&protocolo_id=${protocoloIdActual}`;
        }
        
        const response = await fetch(url);
        if (response.status === 404 || response.status === 501) {
            return;
        }
        
        const data = await response.json();
        if (data.success && data.historial && data.historial.length > 0) {
            const contenedor = document.getElementById('chat-mensajes');
            if (!contenedor) return;
            
            const bienvenida = contenedor.querySelector('.chat-bienvenida');
            if (bienvenida) {
                bienvenida.style.display = 'none';
            }
            
            data.historial.forEach(item => {
                agregarMensajeChat('usuario', item.mensaje);
                agregarMensajeChat('asistente', item.respuesta);
                if (item.historial_id) {
                    historialChatIds.push(item.historial_id);
                }
            });
            
            contenedor.scrollTop = contenedor.scrollHeight;
        }
    } catch (error) {
        console.error('Error cargando historial:', error);
    }
}

/**
 * Limpiar chat
 */
window.limpiarChat = function limpiarChat() {
    if (!confirm('¿Limpiar la conversación actual? (El historial se mantiene en el sistema)')) {
        return;
    }
    
    const contenedor = document.getElementById('chat-mensajes');
    if (!contenedor) return;
    
    contenedor.innerHTML = `
        <div id="chat-bienvenida" class="text-center text-muted">
            <p class="mb-0">Hola, ¿en qué puedo ayudarte hoy?</p>
        </div>
        <div id="chat-escribiendo" style="display: none; text-align: left; padding: 10px; color: #667eea; font-style: italic;">
            <i class="bi bi-three-dots"></i> El asistente está escribiendo...
        </div>
    `;
    
    // Limpiar imágenes seleccionadas
    imagenesChatSeleccionadas = [];
    const previewContainer = document.getElementById('chat-imagenes-container');
    const previewArea = document.getElementById('chat-imagenes-preview');
    if (previewContainer) previewContainer.innerHTML = '';
    if (previewArea) previewArea.style.display = 'none';
    
    // Limpiar acciones actuales
    if (window.accionesChatActuales) {
        window.accionesChatActuales = [];
    }
    
    if (!riveInstance) {
        setTimeout(() => inicializarRIVE(), 300);
    }
    
    historialChatIds = [];
}

/**
 * Verificar estado de Claude API
 */
async function verificarEstadoClaude() {
    try {
        const response = await fetch('/asistente/claude/estado');
        const data = await response.json();
        actualizarEstadoClaude(data.claude_disponible);
    } catch (error) {
        console.error('Error verificando estado de Claude:', error);
        actualizarEstadoClaude(false);
    }
}

/**
 * Actualizar estado visual de Claude
 */
function actualizarEstadoClaude(disponible) {
    const estadoElement = document.getElementById('chat-status');
    if (estadoElement) {
        if (disponible) {
            estadoElement.innerHTML = '<i class="bi bi-circle-fill text-success"></i> Asistente disponible';
            estadoElement.className = 'mt-2 small text-success text-center';
        } else {
            estadoElement.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> Asistente no disponible';
            estadoElement.className = 'mt-2 small text-danger text-center';
        }
    } else {
        console.warn('⚠️ No se encontró el elemento #chat-status para mostrar el estado de Claude');
    }
}

/**
 * Procesar acciones sugeridas por el asistente
 */
function procesarAccionesChat(acciones, intencion) {
    if (!acciones || !Array.isArray(acciones) || acciones.length === 0) {
        return;
    }
    
    const contenedor = document.getElementById('chat-mensajes');
    if (!contenedor) return;
    
    // Crear contenedor de acciones
    const accionesDiv = document.createElement('div');
    accionesDiv.className = 'chat-acciones';
    accionesDiv.style.marginTop = '10px';
    accionesDiv.style.padding = '10px';
    accionesDiv.style.background = '#f0f4f8';
    accionesDiv.style.borderRadius = '8px';
    
    let html = '<div style="font-weight: 600; margin-bottom: 8px; color: #667eea;">💡 Acciones sugeridas:</div>';
    
    acciones.forEach((accion, index) => {
        const btnId = `accion-chat-${Date.now()}-${index}`;
        html += `
            <button 
                id="${btnId}"
                class="btn btn-sm btn-outline-primary me-2 mb-2"
                onclick="ejecutarAccionChat(${index}, accionesChatActuales)"
                style="cursor: pointer;"
            >
                ${escapeHtml(accion.texto || accion.accion || 'Ejecutar acción')}
            </button>
        `;
    });
    
    accionesDiv.innerHTML = html;
    
    // Guardar acciones para poder ejecutarlas
    if (!window.accionesChatActuales) {
        window.accionesChatActuales = [];
    }
    window.accionesChatActuales = acciones;
    
    contenedor.appendChild(accionesDiv);
    contenedor.scrollTop = contenedor.scrollHeight;
}

/**
 * Ejecutar acción sugerida por el asistente
 */
function ejecutarAccionChat(index, acciones) {
    if (!acciones || !acciones[index]) {
        console.error('Acción no encontrada:', index);
        return;
    }
    
    const accion = acciones[index];
    
    console.log('Ejecutando acción:', accion);
    
    switch (accion.tipo) {
        case 'navegar':
            if (accion.accion === 'abrir_protocolo' && accion.protocolo_id) {
                // Navegar al protocolo
                window.location.href = `/protocolos/${accion.protocolo_id}`;
            }
            break;
            
        case 'buscar':
            if (accion.accion === 'ejecutar_busqueda' && accion.termino) {
                // Cambiar al tab de buscar y ejecutar búsqueda
                const tabBuscar = document.querySelector('a[href="#tab-buscar"]');
                if (tabBuscar) {
                    tabBuscar.click();
                    setTimeout(() => {
                        const inputBuscar = document.getElementById('asistente-buscar-input');
                        if (inputBuscar) {
                            inputBuscar.value = accion.termino;
                            if (typeof buscarCasosSimilares === 'function') {
                                buscarCasosSimilares();
                            }
                        }
                    }, 300);
                } else {
                    alert(`Búsqueda sugerida: ${accion.termino}`);
                }
            }
            break;
            
        default:
            console.log('Acción no implementada:', accion.tipo, accion.accion);
            alert(`Acción: ${accion.texto || accion.accion}`);
    }
}

/**
 * Obtener tipo de estudio actual
 */
function obtenerTipoEstudio() {
    const url = window.location.href;
    if (url.includes('pap') || url.includes('PAP')) {
        return 'PAP';
    } else if (url.includes('biopsia') || url.includes('BIOPSIA')) {
        return 'BIOPSIA';
    } else if (url.includes('citologia') || url.includes('CITOLOGIA')) {
        return 'CITOLOGIA';
    }
    return '';
}

} // Cierre del bloque if (typeof window.ASISTENTE_CHAT_LOADED === 'undefined')


