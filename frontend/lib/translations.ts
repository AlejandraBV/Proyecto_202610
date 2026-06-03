/**
 * UI translations — English (en) and Spanish (es).
 * Access via the `useT()` hook  →  const T = useT();  T(tr.sidebar.newChat)
 */

export type Lang = 'en' | 'es';

export const translations = {

  // ── Auth pages ────────────────────────────────────────────────────────────
  auth: {
    appTitle:       { en: 'Academic Content Generator', es: 'Generador de contenido académico' },
    email:          { en: 'Email',               es: 'Correo electrónico'  },
    password:       { en: 'Password',            es: 'Contraseña'          },
    fullName:       { en: 'Full Name',           es: 'Nombre completo'     },
    login:          { en: 'Login',               es: 'Iniciar sesión'      },
    loggingIn:      { en: 'Logging in…',         es: 'Iniciando sesión…'   },
    loginSuccess:   { en: 'Login successful',    es: 'Sesión iniciada correctamente' },
    loginError:     { en: 'Invalid email or password', es: 'Correo o contraseña incorrectos' },
    noAccount:      { en: "Don't have an account?", es: '¿No tienes cuenta?' },
    signUp:         { en: 'Sign up',             es: 'Regístrate'          },
    createAccount:  { en: 'Create Account',      es: 'Crear cuenta'        },
    creatingAccount:{ en: 'Creating account…',   es: 'Creando cuenta…'     },
    registerSuccess:{ en: 'Registration successful! Please login.', es: '¡Registro exitoso! Por favor inicia sesión.' },
    registerError:  { en: 'Registration failed. Try another email.', es: 'Error al registrarse. Intenta con otro correo.' },
    alreadyAccount: { en: 'Already have an account?', es: '¿Ya tienes cuenta?' },
    namePlaceholder:{ en: 'John Doe',            es: 'Nombre Apellido'      },
  },

  // ── Sidebar ───────────────────────────────────────────────────────────────
  sidebar: {
    newChat:          { en: 'New Chat',           es: 'Nueva conversación'  },
    newFolder:        { en: 'New Folder',         es: 'Nueva carpeta'       },
    noConversations:  { en: 'No conversations yet.', es: 'Sin conversaciones aún.' },
    noConvsHint:      { en: 'Just start typing to begin!', es: '¡Solo escribe para comenzar!' },
    loggedIn:         { en: 'Logged in',          es: 'Sesión activa'       },
    toDarkMode:       { en: 'Switch to dark mode', es: 'Cambiar a modo oscuro' },
    toLightMode:      { en: 'Switch to light mode', es: 'Cambiar a modo claro' },
    language:         { en: 'Language',           es: 'Idioma'              },
    logOut:           { en: 'Log out',            es: 'Cerrar sesión'       },
    uncategorized:    { en: 'Uncategorized',      es: 'Sin categoría'       },
    moveTo:           { en: 'Move to',            es: 'Mover a'             },
    deleteChat:       { en: 'Delete chat',        es: 'Eliminar chat'       },
    noChats:          { en: 'No chats yet',       es: 'Sin chats aún'       },
    chooseColor:      { en: 'Choose color',       es: 'Elige color'         },
    creating:         { en: 'Creating…',          es: 'Creando…'            },
    create:           { en: 'Create',             es: 'Crear'               },
    cancel:           { en: 'Cancel',             es: 'Cancelar'            },
    folderNamePlaceholder: { en: 'Folder name…',  es: 'Nombre de carpeta…'  },
    deleteFolder:     { en: 'Delete folder',      es: 'Eliminar carpeta'    },
    deleteFolderConfirm: { en: "Delete folder? Chats will be moved to Uncategorized.", es: "¿Eliminar carpeta? Los chats pasarán a Sin categoría." },
    delete:           { en: 'Delete',             es: 'Eliminar'            },
    correctSubject:   { en: 'Correct subject',    es: 'Corregir asignatura' },
  },

  // ── Chat input ────────────────────────────────────────────────────────────
  chatInput: {
    placeholder:    { en: 'Ask me to generate exams, slideshows, guides… (Enter to send · Shift+Enter for new line)',
                      es: 'Pídeme generar exámenes, diapositivas, guías… (Enter para enviar · Shift+Enter para nueva línea)' },
    placeholderDoc: { en: '(Enter to send · Shift+Enter for new line)',
                      es: '(Enter para enviar · Shift+Enter para nueva línea)' },
    placeholderDocPrefix: { en: 'Ask me to generate content from', es: 'Pídeme generar contenido de' },
    uploadHint:     { en: 'Upload a document first, then describe what to generate from it.',
                      es: 'Sube un documento primero, luego describe qué generar con él.' },
    attachedNow:    { en: 'attached — now type your prompt and send!', es: 'adjuntado — ¡escribe tu solicitud y envía!' },
    urlAttached:    { en: 'URL document attached — now type your prompt and send!',
                      es: 'Documento URL adjunto — ¡escribe tu solicitud y envía!' },
  },

  // ── Upload modal ──────────────────────────────────────────────────────────
  uploadModal: {
    title:        { en: 'Upload Document',   es: 'Subir documento'     },
    file:         { en: 'File',              es: 'Archivo'             },
    url:          { en: 'URL',               es: 'URL'                 },
    selectFile:   { en: 'Select File',       es: 'Seleccionar archivo' },
    subject:      { en: 'Subject',           es: 'Materia'             },
    subjectHint:  { en: '(optional — AI will infer if blank)', es: '(opcional — la IA lo detectará si se deja vacío)' },
    subjectPlaceholder: { en: 'e.g. Mathematics, History, Computer Science…',
                          es: 'p. ej. Matemáticas, Historia, Informática…' },
    cancel:       { en: 'Cancel',            es: 'Cancelar'            },
    upload:       { en: 'Upload',            es: 'Subir'               },
    uploading:    { en: 'Uploading…',        es: 'Subiendo…'           },
  },

  // ── Chat window (empty state) ─────────────────────────────────────────────
  chatWindow: {
    title:        { en: 'Academic Content Generator', es: 'Generador de contenido académico' },
    subtitle:     { en: 'Generate exams, slideshows, guides, and more with AI',
                    es: 'Genera exámenes, diapositivas, guías y más con IA' },
    noMessages:   { en: 'No messages yet. Start a conversation!',
                    es: 'Sin mensajes aún. ¡Inicia una conversación!' },
    card1Title:   { en: '📝 Generate Exams',      es: '📝 Generar exámenes'       },
    card1Body:    { en: 'Create customized exams with multiple question types',
                    es: 'Crea exámenes personalizados con varios tipos de preguntas' },
    card2Title:   { en: '🎬 Create Slideshows',   es: '🎬 Crear diapositivas'     },
    card2Body:    { en: 'Design engaging presentations on any topic',
                    es: 'Diseña presentaciones atractivas sobre cualquier tema' },
    card3Title:   { en: '📚 Write Guides',        es: '📚 Escribir guías'         },
    card3Body:    { en: 'Produce comprehensive study and teaching guides',
                    es: 'Produce guías de estudio y enseñanza completas' },
    card4Title:   { en: '✏️ Refine with Feedback', es: '✏️ Mejorar con comentarios' },
    card4Body:    { en: 'Iteratively improve content with human input',
                    es: 'Mejora el contenido de forma iterativa con retroalimentación' },
  },

  // ── Message item ──────────────────────────────────────────────────────────
  message: {
    you:            { en: 'You',                 es: 'Tú'                  },
    assistant:      { en: 'Academic Generator',  es: 'Generador académico' },
    generating:     { en: 'Generating response with RAG…', es: 'Generando respuesta con RAG…' },
    copy:           { en: 'Copy',                es: 'Copiar'              },
    copied:         { en: 'Copied to clipboard', es: 'Copiado al portapapeles' },
    docAttached:    { en: 'Document attached',   es: 'Documento adjunto'   },
    sourceChunk:    { en: 'source chunk',        es: 'fragmento fuente'    },
    sourceChunks:   { en: 'source chunks',       es: 'fragmentos fuente'   },
    retrieved:      { en: 'Retrieved',           es: 'Recuperado'          },
    chunk:          { en: 'Chunk',               es: 'Fragmento'           },
    from:           { en: 'from',                es: 'de'                  },
    similarity:     { en: 'Similarity:',         es: 'Similitud:'          },
    agentDecisions: { en: 'Agent Decisions',     es: 'Decisiones del agente' },
    showMetadata:   { en: 'Show metadata',       es: 'Mostrar metadatos'   },
  },

  // ── Dashboard stats bar ───────────────────────────────────────────────────
  dashboard: {
    conversation:   { en: 'conversation',        es: 'conversación'        },
    conversations:  { en: 'conversations',       es: 'conversaciones'      },
    contentItem:    { en: 'content item',        es: 'contenido'           },
    contentItems:   { en: 'content items',       es: 'contenidos'          },
    document:       { en: 'document',            es: 'documento'           },
    documents:      { en: 'documents',           es: 'documentos'          },
    topicChanged:   { en: 'Topic changed → new chat:', es: 'Tema cambiado → nuevo chat:' },
    // toasts
    folderCreated:  { en: 'Folder created',      es: 'Carpeta creada'      },
    folderCreateErr:{ en: 'Failed to create folder', es: 'Error al crear carpeta' },
    folderDeleted:  { en: 'Folder deleted',      es: 'Carpeta eliminada'   },
    folderDeleteErr:{ en: 'Failed to delete folder', es: 'Error al eliminar carpeta' },
    movedTo:        { en: 'Moved to',            es: 'Movido a'            },
    moveErr:        { en: 'Failed to move chat', es: 'Error al mover el chat' },
    chatDeleted:    { en: 'Chat deleted',        es: 'Chat eliminado'      },
    chatDeleteErr:  { en: 'Failed to delete chat', es: 'Error al eliminar el chat' },
    sendErr:        { en: 'Failed to send message', es: 'Error al enviar el mensaje' },
  },

  // ── Documents page ────────────────────────────────────────────────────────
  docs: {
    title:          { en: 'Documents',           es: 'Documentos'          },
    upload:         { en: '+ Upload Document',   es: '+ Subir documento'   },
    uploadNew:      { en: 'Upload a new document', es: 'Subir un nuevo documento' },
    subject:        { en: 'Subject',             es: 'Materia'             },
    subjectHint:    { en: '(optional — AI will infer if left blank)', es: '(opcional — la IA lo detectará si se deja vacío)' },
    subjectPlaceholder: { en: 'e.g. Mathematics, History, Computer Science…',
                          es: 'p. ej. Matemáticas, Historia, Informática…' },
    chunksTitle:    { en: 'Document Chunks',     es: 'Fragmentos del documento' },
    noDocuments:    { en: 'No documents uploaded yet.', es: 'Aún no hay documentos subidos.' },
    chunks:         { en: 'Chunks',              es: 'Fragmentos'          },
    autoDetected:   { en: 'Auto-detected',       es: 'Detectado automáticamente' },
    processed:      { en: 'chunks indexed',      es: 'fragmentos indexados' },
    processedPrefix:{ en: 'Document processed:', es: 'Documento procesado:' },
    chunkFetchErr:  { en: 'Failed to fetch document chunks', es: 'Error al cargar los fragmentos' },
    convDeleted:    { en: 'Conversation deleted', es: 'Conversación eliminada' },
    convDeleteErr:  { en: 'Failed to delete conversation', es: 'Error al eliminar la conversación' },
  },

  // ── Settings page ─────────────────────────────────────────────────────────
  settings: {
    title:        { en: 'Settings',          es: 'Configuración'       },
    profile:      { en: 'Profile',           es: 'Perfil'              },
    fullName:     { en: 'Full Name',         es: 'Nombre completo'     },
    institution:  { en: 'Institution',       es: 'Institución'         },
    defaultSubject: { en: 'Default Subject', es: 'Materia predeterminada' },
    subjectPlaceholder: { en: 'e.g. Biology, Mathematics', es: 'p. ej. Biología, Matemáticas' },
    defaultLevel: { en: 'Default Level',     es: 'Nivel predeterminado' },
    elementary:   { en: 'Elementary',        es: 'Primaria'            },
    secondary:    { en: 'Secondary',         es: 'Secundaria'          },
    university:   { en: 'University',        es: 'Universidad'         },
    professional: { en: 'Professional',      es: 'Profesional'         },
    saveChanges:  { en: 'Save Changes',      es: 'Guardar cambios'     },
    saving:       { en: 'Saving…',           es: 'Guardando…'          },
    savedOk:      { en: 'Settings saved',    es: 'Configuración guardada' },
    savedErr:     { en: 'Failed to save settings', es: 'Error al guardar configuración' },
    logout:       { en: 'Log Out',           es: 'Cerrar sesión'       },
    convDeleted:  { en: 'Conversation deleted', es: 'Conversación eliminada' },
    convDeleteErr:{ en: 'Failed to delete conversation', es: 'Error al eliminar la conversación' },
    // Preferences section
    preferences:  { en: 'Preferences',       es: 'Preferencias'        },
    darkMode:     { en: 'Dark mode',          es: 'Modo oscuro'         },
    lightMode:    { en: 'Light mode',         es: 'Modo claro'          },
    language:     { en: 'Interface Language', es: 'Idioma de la interfaz' },
    langEn:       { en: 'English',            es: 'Inglés'              },
    langEs:       { en: 'Spanish',            es: 'Español'             },
  },

  // ── Common ────────────────────────────────────────────────────────────────
  common: {
    loading:  { en: 'Loading…',          es: 'Cargando…'            },
    error:    { en: 'An error occurred', es: 'Ocurrió un error'      },
    via:      { en: 'via',               es: 'vía'                   },
  },

  // ── HITL feedback (rating + edit-and-refine) ──────────────────────────────
  feedback: {
    helpful:          { en: 'Helpful',              es: 'Útil'                           },
    thanks:           { en: 'Thanks!',              es: '¡Gracias!'                      },
    ratingError:      { en: 'Could not save rating', es: 'No se pudo guardar la valoración' },

    // Edit-and-refine panel
    editOutput:       { en: 'Edit output',          es: 'Editar respuesta'               },
    editHint:         { en: 'Edit the content below, then let the AI refine it using your changes as guidance.',
                        es: 'Edita el contenido, luego la IA lo refinará usando tus cambios como guía.' },
    refineWithAI:     { en: 'Refine with AI ✨',    es: 'Refinar con IA ✨'              },
    refining:         { en: 'Refining…',            es: 'Refinando…'                     },
    cancel:           { en: 'Cancel',               es: 'Cancelar'                       },
    refinedLabel:     { en: 'Refined version added to the chat.',
                        es: 'Versión refinada añadida al chat.'                          },
    refineError:      { en: 'Refinement failed. Try again.',
                        es: 'Error al refinar. Inténtalo de nuevo.'                      },
  },

  // ── HITL classification correction ────────────────────────────────────────
  hitl: {
    reclassify:       { en: 'Correct subject',      es: 'Corregir asignatura'            },
    reclassifyTitle:  { en: 'Correct classification', es: 'Corregir clasificación'       },
    reclassifyHint:   { en: 'The AI misclassified this chat. Enter the correct subject:',
                        es: 'La IA clasificó mal este chat. Indica la asignatura correcta:' },
    subjectPlaceholder: { en: 'e.g. Biology, Mathematics, History…',
                          es: 'p. ej. Biología, Matemáticas, Historia…'                  },
    saved:            { en: 'Classification corrected — AI will learn from this.',
                        es: 'Clasificación corregida — la IA aprenderá de esto.'         },
    error:            { en: 'Could not reclassify', es: 'No se pudo reclasificar'        },
    save:             { en: 'Save',                 es: 'Guardar'                        },
    cancel:           { en: 'Cancel',               es: 'Cancelar'                       },
    wasClassifiedAs:  { en: 'Currently classified as:',
                        es: 'Clasificado actualmente como:'                              },
  },

} as const;

// Shorthand alias used in imports
export const tr = translations;

/**
 * Returns the translation string for the given language.
 * Use the `useT()` hook inside React components instead of calling this directly.
 */
export function t(entry: { en: string; es: string }, lang: Lang): string {
  return entry[lang] ?? entry.en;
}

// ---------------------------------------------------------------------------
// Subject-name translations
// Covers every subject the backend MetadataAnalyzer can return.
// Keys are always the English canonical name (as stored in the DB).
// Unknown subjects fall back to the original name unchanged.
// ---------------------------------------------------------------------------
export const subjectNames: Record<string, { en: string; es: string }> = {
  // Core sciences
  'Biology':         { en: 'Biology',          es: 'Biología'              },
  'Chemistry':       { en: 'Chemistry',         es: 'Química'               },
  'Physics':         { en: 'Physics',           es: 'Física'                },
  'Mathematics':     { en: 'Mathematics',       es: 'Matemáticas'           },
  // Humanities
  'History':         { en: 'History',           es: 'Historia'              },
  'Literature':      { en: 'Literature',        es: 'Literatura'            },
  'Geography':       { en: 'Geography',         es: 'Geografía'             },
  'Philosophy':      { en: 'Philosophy',        es: 'Filosofía'             },
  'Art':             { en: 'Art',               es: 'Arte'                  },
  'Music':           { en: 'Music',             es: 'Música'                },
  // Social sciences
  'Economics':       { en: 'Economics',         es: 'Economía'              },
  'Social Sciences': { en: 'Social Sciences',   es: 'Ciencias Sociales'     },
  'Political Science':{ en: 'Political Science', es: 'Ciencias Políticas'   },
  'Psychology':      { en: 'Psychology',        es: 'Psicología'            },
  'Sociology':       { en: 'Sociology',         es: 'Sociología'            },
  // STEM
  'Astronomy':       { en: 'Astronomy',         es: 'Astronomía'            },
  'Earth Sciences':  { en: 'Earth Sciences',    es: 'Ciencias de la Tierra' },
  'Computer Science':{ en: 'Computer Science',  es: 'Informática'           },
  'Engineering':     { en: 'Engineering',       es: 'Ingeniería'            },
  'Health':          { en: 'Health',            es: 'Salud'                 },
  // Business
  'Business':        { en: 'Business',          es: 'Administración'        },
  'Marketing':       { en: 'Marketing',         es: 'Mercadotecnia'         },
  'Finance':         { en: 'Finance',           es: 'Finanzas'              },
  // Misc
  'Language':        { en: 'Language',          es: 'Lenguaje'              },
  'Environmental Science': { en: 'Environmental Science', es: 'Ciencias Ambientales' },
  'General':         { en: 'General',           es: 'General'               },
};

/**
 * Translate a subject name returned by the backend.
 * Falls back to the original string if the subject is not in the map.
 */
export function translateSubject(name: string, lang: Lang): string {
  if (!name) return name;
  const entry = subjectNames[name];
  if (!entry) return name;          // unknown subject → show as-is
  return entry[lang] ?? entry.en;
}

/**
 * Hook version — binds to the active language automatically.
 * Usage:  const ts = useTranslateSubject();  ts('Biology') → "Biología"
 */
export { translateSubject as _translateSubject }; // re-exported for hook below
