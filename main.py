"""
Chatbot API con FastAPI
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import asyncio
import json
from typing import Optional, List, Dict
from models import OllamaManager
from config import HOST, PORT

app = FastAPI(
    title="Chatbot API",
    description="API para chatbot con modelos locales de Ollama",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"GLOBAL ERROR: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
    )

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Ollama Manager
ollama_manager = OllamaManager()

# Lista de colas para eventos SSE (soporta múltiples clientes)
event_listeners: List[asyncio.Queue] = []

# Queue para eventos de progreso desde threads externos
progress_queue: asyncio.Queue = asyncio.Queue()

async def progress_event_processor():
    """Procesa eventos de progreso desde el queue y los envía a los clientes SSE."""
    while True:
        try:
            percent, message, status, filename = await progress_queue.get()
            data = {
                "type": "download_progress",
                "percent": percent,
                "message": message,
                "status": status,
                "filename": filename
            }
            print(f"[PROGRESS] Enviando: {percent}% - {message} - Clientes: {len(event_listeners)}")
            for queue in event_listeners:
                try:
                    await queue.put(data)
                except:
                    pass
        except Exception as e:
            print(f"Error en progress_event_processor: {e}")

# Iniciar el procesador de eventos al inicio
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(progress_event_processor())

@app.get("/api/events")
async def events():
    """Endpoint de Server-Sent Events para progreso y notificaciones."""
    queue = asyncio.Queue()
    event_listeners.append(queue)
    print(f"DEBUG: Nuevo cliente SSE conectado. Total: {len(event_listeners)}")
    
    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            print("DEBUG: Cliente SSE desconectado (cancelado).")
            if queue in event_listeners:
                event_listeners.remove(queue)
            raise
        except Exception as e:
            print(f"DEBUG: Error en generador SSE: {e}")
        finally:
            if queue in event_listeners:
                event_listeners.remove(queue)
            print(f"DEBUG: Cliente SSE finalizado. Total: {len(event_listeners)}")
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

# Crear carpeta de descargas si no existe
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Servir archivos estáticos de descargas
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

@app.get("/api/open-downloads")
async def open_downloads_folder():
    """Abre la carpeta de descargas en el explorador de archivos."""
    try:
        abs_path = os.path.abspath("downloads")
        if not os.path.exists(abs_path):
            os.makedirs(abs_path)
        os.startfile(abs_path)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Modelos Pydantic
class Message(BaseModel):
    role: str
    content: str

class ToolSettings(BaseModel):
    web_search: bool = True
    youtube: bool = True
    word: bool = True
    patterns: bool = True
    automator: bool = True

class ChatRequest(BaseModel):
    prompt: str = ""
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = []
    tool_settings: Optional[ToolSettings] = ToolSettings()

class ModelInfo(BaseModel):
    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None

class ModelResponse(BaseModel):
    success: bool
    models: List[str]
    current_model: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    response: str
    model: Optional[str] = None
    error: Optional[str] = None

class SwitchModelResponse(BaseModel):
    success: bool
    model: Optional[str] = None
    message: Optional[str] = None

class SwitchModelRequest(BaseModel):
    model: str

# Rutas de la API

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "name": "Chatbot API",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/api/models", response_model=ModelResponse)
async def get_models():
    """Obtener lista de modelos disponibles"""
    models = ollama_manager.get_available_models()
    return ModelResponse(
        success=True,
        models=models,
        current_model=ollama_manager.current_model
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Enviar mensaje al chatbot"""
    result = ollama_manager.chat(
        prompt=request.prompt,
        model=request.model,
        system_prompt=request.system_prompt
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error', 'Error desconocido'))
    
    return ChatResponse(
        success=True,
        response=result['response'],
        model=result.get('model')
    )

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Enviar mensaje al chatbot y obtener respuesta en tiempo real (stream)"""

    main_loop = asyncio.get_event_loop()

    def sync_callback(percent, message, status="downloading", filename=None):
        """Callback que pone eventos en el queue de forma thread-safe."""
        print(f"[CALLBACK] {percent}% - {message}")
        # Usar call_soon_threadsafe para poner en el queue sin bloquear
        asyncio.run_coroutine_threadsafe(
            progress_queue.put((percent, message, status, filename)),
            main_loop
        )

    try:
        print(f"DEBUG: Iniciando stream para prompt: {request.prompt[:50]}...")
        return StreamingResponse(
            ollama_manager.chat_stream_generator(
                prompt=request.prompt,
                model=request.model,
                system_prompt=request.system_prompt,
                history=request.history,
                progress_callback=sync_callback,
                tool_settings=request.tool_settings.dict() if request.tool_settings else None
            ),
            media_type="text/plain"
        )
    except Exception as e:
        print(f"Error en endpoint chat_stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        print("DEBUG: Stream finalizado o cerrado.")

@app.post("/api/chat/upload")
async def chat_upload(
    prompt: str = Form(""),
    model: str = Form(None),
    system_prompt: str = Form(None),
    history: str = Form("[]"),
    tool_settings: str = Form("{}"),
    file: UploadFile = File(None)
):
    """Enviar mensaje con archivo adjunto (imagen, PDF, DOCX, TXT) en streaming"""
    file_bytes = None
    file_type = None
    file_name = None

    if file and file.filename:
        file_bytes = await file.read()
        file_name = file.filename
        ct = file.content_type or ''
        fname_lower = file.filename.lower()

        if ct.startswith('image/') or fname_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            file_type = 'image'
        elif fname_lower.endswith('.pdf') or ct == 'application/pdf':
            file_type = 'pdf'
        elif fname_lower.endswith('.docx'):
            file_type = 'docx'
        elif fname_lower.endswith('.txt') or ct.startswith('text/'):
            file_type = 'txt'

    current_model = model or ollama_manager.current_model

    try:
        import json
        history_list = json.loads(history)
    except:
        history_list = []
        
    try:
        import json
        ts_dict = json.loads(tool_settings)
    except:
        ts_dict = {}

    main_loop = asyncio.get_event_loop()

    def sync_callback(percent, message, status="downloading", filename=None):
        """Callback que pone eventos en el queue de forma thread-safe."""
        print(f"[CALLBACK] {percent}% - {message}")
        # Usar call_soon_threadsafe para poner en el queue sin bloquear
        asyncio.run_coroutine_threadsafe(
            progress_queue.put((percent, message, status, filename)),
            main_loop
        )

    try:
        return StreamingResponse(
            ollama_manager.chat_stream_with_file_generator(
                prompt=prompt,
                model=current_model,
                system_prompt=system_prompt,
                file_bytes=file_bytes,
                file_type=file_type,
                file_name=file_name,
                history=history_list,
                progress_callback=sync_callback,
                tool_settings=ts_dict
            ),
            media_type="text/plain"
        )
    except Exception as e:
        print(f"Error en endpoint chat_upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/model/switch", response_model=SwitchModelResponse)
async def switch_model(request: SwitchModelRequest):
    """Cambiar al modelo especificado"""
    success = ollama_manager.switch_model(request.model)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Error al cambiar al modelo: {request.model}")
    
    return SwitchModelResponse(
        success=True,
        model=request.model,
        message=f"Modelo cambiado a: {request.model}"
    )

@app.get("/api/model/info/{model_name}")
async def get_model_info(model_name: str):
    """Obtener información de un modelo"""
    info = ollama_manager.get_model_info(model_name)
    
    if 'error' in info:
        raise HTTPException(status_code=404, detail=info['error'])
    
    return {
        "name": model_name,
        "info": info
    }

@app.post("/api/memory/clear")
async def clear_memory():
    """Borrar la memoria a largo plazo (user profile)"""
    import tools
    success = tools.clear_user_memory()
    if not success:
        raise HTTPException(status_code=500, detail="Error al borrar la memoria")
    return {"success": True, "message": "Memoria borrada correctamente"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)