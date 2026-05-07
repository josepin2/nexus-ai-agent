# Chatbot con Ollama

Un chatbot moderno y minimalista que utiliza modelos locales de Ollama.

## Características

- 🎨 Interfaz moderna y minimalista con diseño oscuro
- 🤖 Soporte para múltiples modelos de Ollama
- 💬 Chat en tiempo real con streaming
- ⚙️ Personalización con prompts del sistema
- 📱 Diseño responsivo para móviles y escritorio

## Requisitos

- Python 3.8 o superior
- Ollama instalado y corriendo (http://localhost:11434)
- Al menos un modelo de Ollama instalado (ej: llama2, mistral, etc.)

## Instalación

### 1. Instalar Ollama

Descarga e instala Ollama desde: https://ollama.ai

### 2. Descargar un modelo

Ejecuta en tu terminal:

```bash
ollama pull llama2
```

O puedes probar con otros modelos como:
- `mistral`
- `gemma`
- `codellama`
- `llama3`

### 3. Iniciar el proyecto

Ejecuta el script de inicio:

```bash
start.bat
```

Esto creará automáticamente el entorno virtual e instalará todas las dependencias necesarias.

## Uso

### Iniciar el servidor

Después de ejecutar `start.bat`, inicia el servidor:

```bash
python main.py
```

El servidor se ejecutará en `http://127.0.0.1:8000`

### Abrir la interfaz web

Abre tu navegador y ve a:

```
http://127.0.0.1:3000
```

### Usar el chatbot

1. **Selecciona un modelo** del menú desplegable en la barra lateral
2. **Escribe tu mensaje** en el campo de entrada
3. **Presiona Enter** o haz clic en el botón de enviar
4. **Personaliza el comportamiento** usando el "Prompt del Sistema"

## Estructura del Proyecto

```
boot/
├── main.py              # API FastAPI
├── models.py            # Manejo de Ollama
├── config.py            # Configuración
├── index.html           # Interfaz web
├── styles.css           # Estilos
├── app.js               # Lógica frontend
├── requirements.txt     # Dependencias Python
├── start.bat            # Script de inicio
└── README.md            # Este archivo
```

## API Endpoints

- `GET /` - Estado del servidor
- `GET /api/models` - Listar modelos disponibles
- `POST /api/chat` - Enviar mensaje al chatbot
- `POST /api/model/switch` - Cambiar de modelo
- `GET /api/model/info/{model_name}` - Información de un modelo

## Personalización

### Cambiar el puerto del servidor

Edita `config.py`:

```python
PORT = 8000  # Cambia este valor
```

### Cambiar el puerto de la interfaz web

Edita `config.py`:

```python
INTERFACE_PORT = 3000  # Cambia este valor
```

## Licencia

Este proyecto es de código abierto.