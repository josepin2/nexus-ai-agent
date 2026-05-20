# Nexus AI Local Agent 🤖🧠

Nexus AI es un asistente inteligente autónomo de vanguardia diseñado para ejecutarse **100% en local** en tu ordenador utilizando modelos de Ollama. No es un simple chatbot: es un Agente capaz de usar herramientas, interactuar con tu sistema de archivos, buscar en internet y aprender de ti, todo bajo un entorno de privacidad absoluta.

![Licencia](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

---

## ✨ Características Principales

Tu Agente cuenta con una "Caja de Herramientas" (Toolbox) modular que puedes activar o desactivar en cualquier momento desde los Ajustes de la interfaz web:

### 🤖 Herramientas del Agente

- 🧠 **Memoria a Largo Plazo Persistente:** El agente recuerda tu nombre, profesión, gustos y preferencias de sesiones anteriores gracias a una base de datos SQLite integrada (`user_profile.db`). ¡Tu IA evoluciona y se adapta a ti con el tiempo!
- 💻 **Automatizador Local (Intérprete de Código Python):** Nexus puede escribir y ejecutar scripts de Python silenciosamente en tu ordenador para organizar tus carpetas, convertir archivos, hacer cálculos masivos y auto-instalarse librerías (como `Pillow` o `pandas`) si lo necesita.
- 🌐 **Búsqueda Web en Tiempo Real:** Si le haces una pregunta sobre un evento actual que el modelo desconoce, el agente rastrea internet, lee las páginas web y te hace un resumen estructurado.
- 🎬 **Gestor de YouTube Integrado:** Proporciónale una URL de YouTube y te descargará el vídeo (mp4) o el audio (mp3) usando `yt-dlp` en calidad óptima, guardándolo en tu carpeta local.
- 🎥 **Resumen de Videos con Whisper:** Envía cualquier URL de YouTube y el agente generará automáticamente un resumen estructurado usando Whisper (transcripción con IA) cuando no haya subtítulos disponibles. Si mencionas "Word" o "documento", te descargará el resumen en formato `.docx` formateado profesionalmente.
- 📄 **Generador de Documentos Word:** Pídele que te redacte un informe formal y el agente creará mágicamente un archivo `.docx` formateado profesionalmente y te dará un enlace directo para descargarlo o abrirlo.
- 🖼️ **Generador de Videos con Fotos:** Indica una carpeta con imágenes y un archivo MP3, y el agente creará automáticamente un video MP4 profesional con transiciones suaves, sincronización de audio y efectos fade.
- 📎 **Lector de Documentos:** Adjunta archivos PDF, DOCX o TXT y el agente podrá leerlos, resumirlos, extraer información o responder preguntas sobre su contenido.
- 👁️ **Análisis de Imágenes:** Sube imágenes y el agente las describirá, analizará o extraerá información de ellas usando visión por computadora.

### 💻 Características de la Interfaz

- 🎨 **Diseño Glassmorphism Premium:** Interfaz moderna y elegante con efectos de vidrio esmerilado, renderizado de Markdown, tablas, código con sintaxis resaltada y modo oscuro.
- 🔄 **Streaming en Tiempo Real:** Respuestas fluidas que aparecen progresivamente mientras el agente genera el contenido, sin esperas.
- 📜 **Historial de Chat:** El sistema guarda automáticamente tus conversaciones para que puedas volver a ellas en cualquier momento desde la barra lateral.
- 🔀 **Multi-Modelo:** Cambia entre diferentes modelos de Ollama (Llama 3, Mistral, Gemma, etc.) en tiempo real según tus necesidades.
- ⚙️ **Ajustes Configurables:** Activa o desactiva individualmente cada herramienta (búsqueda web, YouTube, Word, Python, etc.) según tus preferencias.
- 📊 **Barra de Progreso:** Visualiza el progreso de descargas de YouTube y otras tareas largas directamente en la interfaz.
- 📂 **Acceso Rápido a Archivos:** Botón integrado para abrir directamente la carpeta de descargas desde el navegador.

---

## 🚀 Requisitos Previos

- Python 3.8 o superior.
- [Ollama](https://ollama.ai/) instalado y en ejecución en tu ordenador (`http://localhost:11434`).
- FFmpeg (opcional, pero fuertemente recomendado para que funcione correctamente la descarga de audios de YouTube).

---

## 🛠️ Instalación y Uso

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/TU_USUARIO/nexus-ai-agent.git
   cd nexus-ai-agent
   ```

2. **Iniciar el Servidor Mágico**
   Haz doble clic en el archivo `start.bat` o ejecútalo en la terminal:
   ```bash
   start.bat
   ```
   > Este script creará automáticamente el entorno virtual (`venv`), instalará todos los paquetes de `requirements.txt` e iniciará tanto el servidor API (FastAPI) como el servidor de interfaz web de inmediato.

3. **Acceder al Chat**
   Abre tu navegador web favorito y entra en:
   ```text
   http://127.0.0.1:3000
   ```

4. **Descargar un Modelo de Ollama (Si es la primera vez)**
   Si no tienes ningún modelo descargado en Ollama, la interfaz te avisará. Simplemente abre tu terminal y ejecuta:
   ```bash
   ollama run llama3
   ```

---

## 💡 Ejemplos de Uso

Aquí tienes algunos ejemplos de cómo interactuar con Nexus AI:

### Automatización y Sistema
- "¿Qué recursos está consumiendo mi PC ahora mismo?"
- "Organiza mi carpeta de Descargas moviendo los archivos PDF a una subcarpeta llamada Documentos"
- "Haz un cálculo del interés compuesto para 1000€ al 5% durante 10 años"

### Documentos y Archivos
- [Adjunta un PDF] "Resume este documento en 5 puntos clave"
- "Escribe un informe formal sobre cambio climático en formato Word"
- [Adjunta una imagen] "Describe qué ves en esta imagen en detalle"

### YouTube y Videos
- "Resume este video de YouTube: https://youtube.com/watch?v=..."
- "Descárgame este video en MP4: https://youtube.com/watch?v=..."
- "Descárgame solo el audio de este video: [URL]"

### Creación de Contenido
- "Crea un video con las fotos de la carpeta 'Vacaciones' y el audio 'musica.mp3'"
- "Escribe un artículo sobre inteligencia artificial en formato Word"

### Búsqueda Web
- "Busca las últimas noticias sobre tecnología"
- "¿Qué ha pasado esta semana en el mundo?"

---

## 📂 Estructura del Proyecto

```text
nexus-ai-agent/
├── main.py              # Backend FastAPI (Gestión de Endpoints)
├── models.py            # Motor de IA: Inyección de Prompts y Lógica de Herramientas
├── tools.py             # Herramientas físicas (YouTube, Web, DB, Python Exec)
├── user_profile.db      # Base de Datos SQLite (Memoria del Usuario)
├── config.py            # Puertos y variables de entorno
├── requirements.txt     # Dependencias del proyecto
├── start.bat            # Instalador y Lanzador Automático
├── index.html           # Interfaz Gráfica (Frontend HTML)
├── styles.css           # Diseño Premium Glassmorphic
├── app.js               # Lógica del cliente y renderizado en streaming
└── web/                 # Landing Page promocional del Agente
```

---

## 🔒 Privacidad y Seguridad

Este proyecto fue concebido bajo el principio de **Soberanía de Datos**. Nada de lo que hables, preguntes o subas a Nexus AI sale de tu ordenador. Todo el procesamiento de los modelos de Lenguaje y las acciones sobre el sistema de archivos ocurren única y exclusivamente en tu procesador/tarjeta gráfica local. 

---

## 📜 Licencia y Copyright

Copyright © 2026 **José Milán Carrasco (JosePin2)**.

Este proyecto se distribuye bajo la licencia **Apache License 2.0**. Eres libre de utilizarlo, modificarlo y distribuirlo, tanto para fines personales como comerciales, siempre que se mantenga el aviso de copyright y se otorgue el crédito correspondiente al autor original.

Para más información, consulta el archivo `LICENSE` adjunto o visita el perfil del autor en [GitHub](https://github.com/josepin2).