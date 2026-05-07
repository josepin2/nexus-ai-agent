# Nexus AI Local Agent 🤖🧠

Nexus AI es un asistente inteligente autónomo de vanguardia diseñado para ejecutarse **100% en local** en tu ordenador utilizando modelos de Ollama. No es un simple chatbot: es un Agente capaz de usar herramientas, interactuar con tu sistema de archivos, buscar en internet y aprender de ti, todo bajo un entorno de privacidad absoluta.

![Licencia](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

---

## ✨ Características Principales

Tu Agente cuenta con una "Caja de Herramientas" (Toolbox) modular que puedes activar o desactivar en cualquier momento desde los Ajustes de la interfaz web:

- 🧠 **Memoria a Largo Plazo Persistente:** El agente recuerda tu nombre, profesión, gustos y preferencias de sesiones anteriores gracias a una base de datos SQLite integrada (`user_profile.db`). ¡Tu IA evoluciona y se adapta a ti con el tiempo!
- 💻 **Automatizador Local (Intérprete de Código Python):** Nexus puede escribir y ejecutar scripts de Python silenciosamente en tu ordenador para organizar tus carpetas, convertir archivos, hacer cálculos masivos y auto-instalarse librerías (como `Pillow` o `pandas`) si lo necesita.
- 🌐 **Búsqueda Web en Tiempo Real:** Si le haces una pregunta sobre un evento actual que el modelo desconoce, el agente rastrea internet, lee las páginas web y te hace un resumen estructurado.
- 🎬 **Gestor de YouTube Integrado:** Proporciónale una URL de YouTube y te descargará el vídeo (mp4) o el audio (mp3) usando `yt-dlp` en calidad óptima, guardándolo en tu carpeta local.
- 📄 **Generador de Documentos Word:** Pídele que te redacte un informe formal y el agente creará mágicamente un archivo `.docx` formateado profesionalmente y te dará un enlace directo para descargarlo o abrirlo.
- 🗣️ **Interfaz de Streaming y Markdown:** Diseño Glassmorphism premium. Disfruta de respuestas fluidas en tiempo real, renderizado de tablas, fragmentos de código con sintaxis resaltada y modo oscuro.

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

## 📜 Licencia

Este proyecto se distribuye bajo la licencia **Apache License 2.0**. Eres libre de utilizarlo, modificarlo y distribuirlo, tanto para fines personales como comerciales. Para más información, consulta el archivo `LICENSE` adjunto.