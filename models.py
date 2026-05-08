# Copyright 2026 José Milán Carrasco
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Manejo de modelos de Ollama
"""
import json
import httpx
import re
import threading
from typing import List, Dict, Any
from config import OLLAMA_BASE_URL, HOST, PORT
import tools
import logging

# Configurar logging
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class OllamaManager:
    """Clase para gestionar la comunicación con Ollama"""
    
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.current_model = None
    
    def get_available_models(self) -> List[str]:
        """Obtener lista de modelos disponibles en Ollama"""
        try:
            url = f"{OLLAMA_BASE_URL}/api/tags"
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
            
            models = []
            for model in data.get('models', []):
                models.append(model.get('name', ''))
            return models
        except Exception as e:
            print(f"Error obteniendo modelos: {e}")
            return []
    
    def switch_model(self, model_name: str) -> bool:
        """Cambiar al modelo especificado (sin descargarlo si ya existe)"""
        try:
            # Verificar si el modelo existe
            models = self.get_available_models()
            if model_name not in models:
                return False
            
            self.current_model = model_name
            return True
        except Exception as e:
            print(f"Error cambiando modelo: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """Obtener lista de modelos disponibles en Ollama"""
        return self.get_available_models()
    
    def chat(self, prompt: str, model: str = None, system_prompt: str = None) -> Dict[str, Any]:
        """
        Enviar prompt a Ollama y obtener respuesta

        Args:
            prompt: El mensaje del usuario
            model: Nombre del modelo a usar (si None, usa el actual)
            system_prompt: Prompt del sistema para configurar el comportamiento

        Returns:
            Diccionario con la respuesta y metadatos
        """
        try:
            if model is None:
                model = self.current_model

            if not model:
                return {
                    'success': False,
                    'error': 'No se ha seleccionado ningún modelo',
                    'response': ''
                }

            # Construir mensajes
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})

            # Construir URL
            url = f"{OLLAMA_BASE_URL}/api/chat"

            # Obtener respuesta (sin streaming para simplificar)
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url,
                    json={
                        'model': model,
                        'messages': messages,
                        'stream': False
                    }
                )
                response.raise_for_status()
                data = response.json()
                content = data.get('message', {}).get('content', '')

                if content:
                    return {
                        'success': True,
                        'response': content,
                        'model': model
                    }
                else:
                    return {
                        'success': False,
                        'error': 'El modelo no respondió a tu mensaje',
                        'response': ''
                    }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error de conexión con Ollama: {str(e)}',
                'response': ''
            }
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Obtener información sobre un modelo específico"""
        try:
            url = f"{OLLAMA_BASE_URL}/api/show"
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json={'name': model_name})
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {'error': str(e)}

    async def chat_stream_generator(self, prompt: str, model: str = None, system_prompt: str = None, history: List[Dict[str, str]] = None, progress_callback=None, tool_settings: Dict[str, bool] = None):
        """Generador para respuesta en streaming desde Ollama."""
        if not tool_settings:
            tool_settings = {"web_search": True, "youtube": True, "word": True, "patterns": True}
        if model is None:
            model = self.current_model

        if not model:
            yield "Error: No se ha seleccionado ningún modelo."
            return

        # Detectar descargas de YouTube
        yt_match = re.search(r'(https?://(?:www\.)?youtube\.com/[^\s<>"]+|https?://youtu\.be/[^\s<>"]+)', prompt)
        is_download_request = any(word in prompt.lower() for word in ['descarga', 'bájame', 'bajar', 'download'])
        
        # Detectar descargas de YouTube
        if prompt and tool_settings.get("youtube", True):
            # Regex mejorada para limpiar puntos finales o caracteres raros al final de la URL
            yt_match = re.search(r'(https?://(?:www\.)?youtube\.com/watch\?v=[^\s&<>"]+|https?://(?:www\.)?youtube\.com/embed/[^\s&<>"]+|https?://youtu\.be/[^\s&<>"]+)', prompt)
            is_download_request = any(word in prompt.lower() for word in ['descarga', 'bájame', 'bajar', 'download'])
            
            if yt_match and is_download_request:
                url = yt_match.group(1).rstrip('.') # Limpiar punto final si existe
                mode = 'audio' if any(word in prompt.lower() for word in ['audio', 'mp3', 'sonido', 'música']) else 'video'
                
                logging.info(f"Iniciando descarga de YouTube (Background): {url} en modo {mode}")
                print(f"DEBUG: Iniciando tarea de descarga para {url}")
                yield f"Entendido. Voy a descargar ese {mode} de YouTube para ti. Puedes ver el progreso en la barra lateral izquierda. Te avisaré por aquí en cuanto esté listo.\n\n"
                
                # Función para ejecutar en segundo plano
                def run_download_task():
                    try:
                        print(f"DEBUG: Thread de descarga ejecutando tools.download_youtube_media...")
                        filename = tools.download_youtube_media(url, mode, progress_callback)
                        print(f"DEBUG: Resultado de descarga en thread: {filename}")
                        if "Error" in filename:
                            progress_callback(0, f"Error: {filename}", status="error")
                        else:
                            # Notificar éxito con el nombre del archivo
                            progress_callback(100, "¡Descarga lista!", status="completed", filename=filename)
                    except Exception as e:
                        print(f"DEBUG: Error crítico en thread de descarga: {e}")
                        logging.error(f"Error en tarea de descarga bg: {e}")
                        progress_callback(0, f"Error crítico: {str(e)}", status="error")

                # Lanzar en un hilo separado para no bloquear nada
                threading.Thread(target=run_download_task, daemon=True).start()
                return

        # Detección de intención de búsqueda y extracción de URLs
        if prompt and tool_settings.get("web_search", True):
            urls_in_prompt = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', prompt)
            
            if not urls_in_prompt:
                search_keywords = ['busca', 'búscame', 'buscar', 'búsqueda', 'noticia', 'noticias', 'internet', 'web', 'investiga', 'últimos días', 'qué ha pasado']
                prompt_lower = prompt.lower()
                is_search_request = False
                for kw in search_keywords:
                    if re.search(rf'\b{kw}\b', prompt_lower):
                        is_search_request = True
                        break
                        
                if is_search_request:
                    yield f"\n[Buscando información en internet...]\n"
                    
                    # Limpiar el prompt para una mejor búsqueda
                    query = prompt.replace('\n', ' ')
                    stop_words = ['busca', 'búscame', 'buscar', 'búsqueda', 'quiero', 'que', 'me', 'un', 'una', 'el', 'la', 'los', 'las', 'por favor', 'pero', 'al menos']
                    for w in stop_words:
                        query = re.sub(rf'\b{w}\b', '', query, flags=re.IGNORECASE)
                    
                    if re.search(r'\b(días|hoy|reciente|última hora|últimas)\b', prompt_lower):
                        query += " noticias actuales"
                        
                    query = re.sub(r'\s+', ' ', query).strip()
                    if len(query) < 3:
                        query = prompt
                        
                    search_results = await tools.async_search_web(query)
                    prompt = (
                        f"Resultados de la búsqueda en internet:\n\n"
                        f"{search_results}\n\n"
                        f"--- INSTRUCCIONES DE RESPUESTA ---\n"
                        f"1. Ve directo al grano. NO hagas introducciones largas ni des opiniones. (IGNORA LA REGLA DE CREAR WORD a menos que se pida explícitamente).\n"
                        f"2. Proporciona una respuesta muy estructurada, objetiva y directa. Usa listas con viñetas y negritas para resaltar puntos clave.\n"
                        f"3. Lee el contenido extraído y responde detalladamente a lo que pide el usuario basándote SOLO en los resultados.\n"
                        f"4. Cita las fuentes (Enlaces) al final si es relevante.\n\n"
                        f"Petición original del usuario: {prompt}"
                    )
            
            # Detectar y extraer contenido de URLs (resto de webs)
            urls = [u for u in urls_in_prompt if 'youtube.com' not in u and 'youtu.be' not in u and '127.0.0.1' not in u and 'localhost' not in u]
            
            if urls:
                yield f"\n[Accediendo a la(s) web(s)...]\n"
                url_context = ""
                for url in urls:
                    content = await tools.async_extract_url_content(url)
                    url_context += f"\n--- CONTENIDO DE LA WEB ({url}) ---\n{content}\n--- FIN DE LA WEB ---\n"
                
                prompt = (
                    f"{url_context}\n"
                    f"--- INSTRUCCIONES DE RESPUESTA ---\n"
                    f"1. Ve directo al grano. NO hagas introducciones largas, saludos ni des tu opinión personal.\n"
                    f"2. Proporciona un resumen muy estructurado, claro y conciso de la información de la web.\n"
                    f"3. Utiliza listas con viñetas y negritas para resaltar y estructurar los puntos clave.\n"
                    f"4. Responde exactamente a lo que pide el usuario basándote ÚNICAMENTE en el contenido proporcionado.\n\n"
                    f"Petición del usuario: {prompt}"
                )

        # PROTOCOLO DE RESPUESTA (Equilibrio entre amigable y profesional)
        word_instruction = ""
        if tool_settings.get("word", True):
            word_instruction = (
                "\n\n--- REGLA DE ACTIVACIÓN DE WORD (CRÍTICA) ---\n"
                "SOLO si el usuario pide EXPLÍCITAMENTE crear un 'Word', 'Documento' o 'Artículo', DEBES generar tu respuesta envolviéndola en etiquetas XML.\n"
                "NUNCA generes <word_document> si el usuario NO ha pedido un documento. Si te piden ejecutar código, ver recursos del PC, o cualquier otra cosa que NO sea un documento, NO uses esta herramienta.\n"
                "Formato EXACTO que debes usar:\n"
                "<word_document filename=\"nombre_descriptivo.docx\">\n"
                "# Título Principal\n"
                "Contenido del documento...\n"
                "</word_document>\n\n"
                "--- INSTRUCCIONES DE FORMATO ---\n"
                "1. CHAT: Fuera de las etiquetas XML escribe ÚNICAMENTE 'Aquí tienes el resumen' y nada más.\n"
                "2. NOMBRE DEL ARCHIVO: Debe estar en el atributo filename.\n"
                "3. FORMATO INTERNO DEL WORD: Usa Markdown profesional (#, ##, **, y tablas si corresponde).\n"
                "4. TONO: Usa un tono amigable, cercano y servicial. Utiliza EMOJIS relevantes en tus respuestas de chat para que la conversación sea más humana y agradable (al estilo de ChatGPT).\n"
            )
        
        table_instruction = (
            "\n\n--- INSTRUCCIÓN SOBRE TABLAS ---\n"
            "El sistema SOPORTA tablas en formato Markdown (ej: | Col 1 | Col 2 |). Úsalas si el usuario te lo pide explícitamente o si la información es claramente tabular (como datos estructurados, estadísticas, comparativas). Si no aplica o no se te pide, responde en texto normal o listas."
        )
        
        patterns_instruction = ""
        if tool_settings.get("patterns", True):
            mem_str = tools.get_user_memory()
            mem_context = f"\nDATOS CONOCIDOS DEL USUARIO (Memoria a Largo Plazo): {mem_str}\n" if mem_str else ""
            patterns_instruction = (
                "\n\n--- INSTRUCCIÓN DE MEMORIA A LARGO PLAZO Y PATRONES ---\n"
                "Tienes activa la herramienta de Memoria. Esta herramienta te permite recordar información personal, contexto, intereses y preferencias del usuario entre distintas sesiones.\n"
                f"{mem_context}"
                "Analiza la conversación para identificar NUEVOS datos importantes (ej. cómo se llama, dónde vive, en qué trabaja, qué le gusta, etc.) que no estén en la lista anterior.\n"
                "Usa los datos conocidos para personalizar tus respuestas de forma proactiva y dirígete al usuario por su nombre si lo conoces.\n"
                "CRÍTICO: Si el usuario te revela un dato personal NUEVO o un interés EN ESTA CONVERSACIÓN, DEBES incluir obligatoriamente al final de tu respuesta una etiqueta con este formato EXACTO: <pattern>Categoría: valor_real_del_usuario</pattern>.\n"
                "Las categorías válidas son: Nombre, Interés, Profesión, Ciudad, Edad, etc.\n"
                "PROHIBIDO: NUNCA generes etiquetas <pattern> con datos inventados, supuestos o de ejemplo. SOLO con datos que el usuario EXPLÍCITAMENTE te haya dicho en la conversación actual.\n"
                "PROHIBIDO: NUNCA uses los datos de estas instrucciones como si fueran del usuario. Estas instrucciones son SOLO para ti, NO son datos del usuario.\n"
                "Si NO hay datos personales nuevos en el mensaje actual del usuario, NO generes ninguna etiqueta <pattern>."
            )
        automator_instruction = ""
        if tool_settings.get("automator", True):
            automator_instruction = (
                "\n\n--- INSTRUCCIÓN DEL AUTOMATIZADOR / INTÉRPRETE DE PYTHON (OBLIGATORIA) ---\n"
                "Tienes activa la herramienta Intérprete de Python. Este código se ejecuta DIRECTAMENTE en el PC local del usuario. Tú SÍ PUEDES interactuar con su sistema.\n\n"
                "CUÁNDO USARLA (OBLIGATORIO - NO te niegues, NO digas que no puedes):\n"
                "- Consultar recursos del sistema: CPU, RAM, disco, GPU, procesos, temperatura.\n"
                "- Ordenar, renombrar, mover o listar archivos y carpetas.\n"
                "- Cálculos complejos, análisis de datos, automatizaciones.\n"
                "- Cualquier tarea que requiera interactuar con el sistema operativo del usuario.\n\n"
                "PROHIBICIÓN ABSOLUTA: NUNCA respondas 'no tengo acceso a tu PC', 'no puedo ver tu hardware', 'copia y pega este código'. Eso es FALSO. Tú SÍ tienes acceso porque el código se ejecuta en la máquina local. Genera el script y se ejecutará automáticamente.\n\n"
                "REGLAS CRÍTICAS:\n"
                "1. SILENCIO TOTAL: NO expliques el código. Responde ÚNICAMENTE con las etiquetas <run_python> y el código dentro. NADA MÁS en el chat (ni antes ni después de las etiquetas).\n"
                "2. DEPENDENCIAS: Si necesitas librerías externas (psutil, PIL, requests, pandas, etc.), asume que NO están instaladas. Instálalas SIEMPRE al inicio del script: `import subprocess, sys; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'nombre_paquete'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)`.\n"
                "3. NO EMOJIS: NUNCA uses emojis dentro de los print() de Python, causan errores de codificación en Windows.\n"
                "4. Para referirte a rutas de usuario, NUNCA uses rutas absolutas estáticas. Usa SIEMPRE `import os; path = os.path.expanduser('~')` para resolver la carpeta del usuario dinámicamente.\n"
                "5. Pon tu código Python envuelto exactamente en estas etiquetas: <run_python> y </run_python>.\n"
                "6. NO generes etiquetas <word_document> junto con <run_python>. Son herramientas independientes.\n"
                "7. ROBUSTEZ: Envuelve SIEMPRE las operaciones de archivos en bloques try/except para manejar errores individuales sin detener todo el script. Usa solo módulos estándar de Python (os, shutil, glob, pathlib) para operaciones de archivos.\n"
                "8. SIMPLICIDAD: Escribe código simple y directo. NO uses operaciones matemáticas con listas. Usa bucles for simples y funciones básicas de os y shutil.\n\n"
                "Ejemplo para consultar recursos del sistema:\n"
                "<run_python>\n"
                "import subprocess, sys\n"
                "subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                "import psutil\n"
                "print(f'CPU: {psutil.cpu_percent(interval=1)}%')\n"
                "print(f'RAM: {psutil.virtual_memory().percent}%')\n"
                "</run_python>"
            )

        full_system_prompt = (system_prompt or "") + word_instruction + table_instruction + patterns_instruction + automator_instruction

        messages = []
        if history:
            messages.extend(history)
            
        messages.append({'role': 'system', 'content': full_system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        url = f"{self.base_url}/api/chat"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    json={
                        'model': model,
                        'messages': messages,
                        'stream': True
                    }
                ) as response:
                    response.raise_for_status()
                    full_response_text = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    chunk = data["message"]["content"]
                                    full_response_text += chunk
                                    yield chunk
                            except json.JSONDecodeError:
                                pass
                    
                    # Al finalizar, extraer nuevos patrones si existen
                    if tool_settings.get("patterns", True):
                        new_patterns = re.findall(r'<pattern>(.*?)</pattern>', full_response_text, flags=re.IGNORECASE)
                        if new_patterns:
                            tools.update_user_memory(new_patterns)
                            
                    # Al finalizar, ejecutar automator si existe
                    if tool_settings.get("automator", True):
                        python_blocks = re.findall(r'<run_python>(.*?)</run_python>', full_response_text, flags=re.IGNORECASE | re.DOTALL)
                        for code_block in python_blocks:
                            result = tools.execute_python_code(code_block)
                            if result["success"]:
                                display = result["stdout"] or "El script se ejecutó correctamente."
                                yield f"\n\n✅ **Tarea completada con éxito.**\n```\n{display}\n```"
                            else:
                                error_msg = result["stderr"]
                                if result["stdout"]:
                                    yield f"\n\n⚠️ **El script se ejecutó parcialmente:**\n```\n{result['stdout']}\n```\n**Error encontrado:**\n```text\n{error_msg}\n```"
                                else:
                                    yield f"\n\n❌ **La automatización encontró un problema:**\n```text\n{error_msg}\n```"
                            
                    # Al finalizar, verificar si hay que generar Word (Detección más robusta)
                    has_start = "<word_document" in full_response_text
                    has_end = "</word_document>" in full_response_text
                    
                    if has_start:
                        # Extraer nombre de archivo si existe: <word_document filename="xxx.docx">
                        fname_match = re.search(r'<word_document\s+filename=["\']([^"\']+)["\']>', full_response_text)
                        suggested_filename = fname_match.group(1) if fname_match else None
                        
                        # Buscar el contenido real
                        tag_start = full_response_text.find("<word_document")
                        content_start = full_response_text.find(">", tag_start) + 1
                        
                        if has_end:
                            end = full_response_text.find("</word_document>")
                        else:
                            # Si olvidó cerrar la etiqueta, tomamos hasta el final
                            end = len(full_response_text)
                            
                        word_content = full_response_text[content_start:end].strip()
                        
                        if word_content:
                            fname = tools.generate_word_file(word_content, suggested_filename)
                            yield f"\n\n--- \n✅ **Aquí tienes el resumen**\n\n[📥 Descargar Word](http://{HOST}:{PORT}/downloads/{fname}) | [📂 Abrir Carpeta](http://{HOST}:{PORT}/api/open-downloads)"
        except Exception as e:
            yield f"\n\n[Error de conexión: {str(e)}]"

    async def chat_stream_with_file_generator(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = None,
        file_bytes: bytes = None,
        file_type: str = None,   # 'image' | 'pdf' | 'docx' | 'txt'
        file_name: str = None,
        history: List[Dict[str, str]] = None,
        progress_callback=None,
        tool_settings: Dict[str, bool] = None
    ):
        """Streaming con soporte de archivos e imágenes."""
        if not tool_settings:
            tool_settings = {"web_search": True, "youtube": True, "word": True, "patterns": True}
        if model is None:
            model = self.current_model

        if not model:
            yield "Error: No se ha seleccionado ningún modelo."
            return

        # Detectar descargas de YouTube
        if prompt and tool_settings.get("youtube", True):
            yt_match = re.search(r'(https?://(?:www\.)?youtube\.com/[^\s<>"]+|https?://youtu\.be/[^\s<>"]+)', prompt)
            is_download_request = any(word in prompt.lower() for word in ['descarga', 'bájame', 'bajar', 'download'])
            
            if yt_match and is_download_request:
                url = yt_match.group(1)
                mode = 'audio' if any(word in prompt.lower() for word in ['audio', 'mp3', 'sonido', 'música']) else 'video'
                
                logging.info(f"Iniciando descarga de YouTube (Background with file): {url} en modo {mode}")
                yield f"Entendido. Voy a descargar ese {mode} de YouTube para ti. Puedes ver el progreso en la barra lateral izquierda. Te avisaré por aquí en cuanto esté listo.\n\n"
                
                def run_download_task():
                    try:
                        filename = tools.download_youtube_media(url, mode, progress_callback)
                        if "Error" in filename:
                            progress_callback(0, f"Error: {filename}", status="error")
                        else:
                            progress_callback(100, "¡Descarga lista!", status="completed", filename=filename)
                    except Exception as e:
                        logging.error(f"Error en tarea de descarga bg: {e}")
                        progress_callback(0, f"Error crítico: {str(e)}", status="error")

                import threading
                threading.Thread(target=run_download_task, daemon=True).start()
                return

        # Detección de intención de búsqueda y extracción de URLs
        if prompt and tool_settings.get("web_search", True):
            urls_in_prompt = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', prompt)
            
            if not urls_in_prompt:
                search_keywords = ['busca', 'búscame', 'buscar', 'búsqueda', 'noticia', 'noticias', 'internet', 'web', 'investiga', 'últimos días', 'qué ha pasado']
                prompt_lower = prompt.lower()
                is_search_request = False
                for kw in search_keywords:
                    if re.search(rf'\b{kw}\b', prompt_lower):
                        is_search_request = True
                        break
                        
                if is_search_request:
                    yield f"\n[Buscando información en internet...]\n"
                    
                    # Limpiar el prompt para una mejor búsqueda
                    query = prompt.replace('\n', ' ')
                    stop_words = ['busca', 'búscame', 'buscar', 'búsqueda', 'quiero', 'que', 'me', 'un', 'una', 'el', 'la', 'los', 'las', 'por favor', 'pero', 'al menos']
                    for w in stop_words:
                        query = re.sub(rf'\b{w}\b', '', query, flags=re.IGNORECASE)
                    
                    if re.search(r'\b(días|hoy|reciente|última hora|últimas)\b', prompt_lower):
                        query += " noticias actuales"
                        
                    query = re.sub(r'\s+', ' ', query).strip()
                    if len(query) < 3:
                        query = prompt
                        
                    search_results = await tools.async_search_web(query)
                    prompt = (
                        f"Resultados de la búsqueda en internet:\n\n"
                        f"{search_results}\n\n"
                        f"--- INSTRUCCIONES DE RESPUESTA ---\n"
                        f"1. Ve directo al grano. NO hagas introducciones largas ni des opiniones. (IGNORA LA REGLA DE CREAR WORD a menos que se pida explícitamente).\n"
                        f"2. Proporciona una respuesta muy estructurada, objetiva y directa. Usa listas con viñetas y negritas para resaltar puntos clave.\n"
                        f"3. Lee el contenido extraído y responde detalladamente a lo que pide el usuario basándote SOLO en los resultados.\n"
                        f"4. Cita las fuentes (Enlaces) al final si es relevante.\n\n"
                        f"Petición original del usuario: {prompt}"
                    )
            
            # Detectar y extraer contenido de URLs (resto de webs)
            urls = [u for u in urls_in_prompt if 'youtube.com' not in u and 'youtu.be' not in u and '127.0.0.1' not in u and 'localhost' not in u]
            
            if urls:
                yield f"\n[Accediendo a la(s) web(s)...]\n"
                url_context = ""
                for url in urls:
                    content = await tools.async_extract_url_content(url)
                    url_context += f"\n--- CONTENIDO DE LA WEB ({url}) ---\n{content}\n--- FIN DE LA WEB ---\n"
                
                prompt = (
                    f"{url_context}\n"
                    f"--- INSTRUCCIONES DE RESPUESTA ---\n"
                    f"1. Ve directo al grano. NO hagas introducciones largas, saludos ni des tu opinión personal.\n"
                    f"2. Proporciona un resumen muy estructurado, claro y conciso de la información de la web.\n"
                    f"3. Utiliza listas con viñetas y negritas para resaltar y estructurar los puntos clave.\n"
                    f"4. Responde exactamente a lo que pide el usuario basándote ÚNICAMENTE en el contenido proporcionado.\n\n"
                    f"Petición del usuario: {prompt}"
                )

        # PROTOCOLO DE RESPUESTA (Equilibrio entre amigable y profesional)
        word_instruction = ""
        if tool_settings.get("word", True):
            word_instruction = (
                "\n\n--- REGLA DE ACTIVACIÓN DE WORD (CRÍTICA) ---\n"
                "SOLO si el usuario pide EXPLÍCITAMENTE crear un 'Word', 'Documento' o 'Artículo', DEBES generar tu respuesta envolviéndola en etiquetas XML.\n"
                "NUNCA generes <word_document> si el usuario NO ha pedido un documento. Si te piden ejecutar código, ver recursos del PC, o cualquier otra cosa que NO sea un documento, NO uses esta herramienta.\n"
                "Formato EXACTO que debes usar:\n"
                "<word_document filename=\"nombre_descriptivo.docx\">\n"
                "# Título Principal\n"
                "Contenido del documento...\n"
                "</word_document>\n\n"
                "--- INSTRUCCIONES DE FORMATO ---\n"
                "1. CHAT: Fuera de las etiquetas XML escribe ÚNICAMENTE 'Aquí tienes el resumen' y nada más.\n"
                "2. NOMBRE DEL ARCHIVO: Debe estar en el atributo filename.\n"
                "3. FORMATO INTERNO DEL WORD: Usa Markdown profesional (#, ##, **, y tablas si corresponde).\n"
                "4. TONO: Usa un tono amigable, cercano y servicial. Utiliza EMOJIS relevantes en tus respuestas de chat para que la conversación sea más humana y agradable (al estilo de ChatGPT).\n"
            )
        
        table_instruction = (
            "\n\n--- INSTRUCCIÓN SOBRE TABLAS ---\n"
            "El sistema SOPORTA tablas en formato Markdown (ej: | Col 1 | Col 2 |). Úsalas si el usuario te lo pide explícitamente o si la información es claramente tabular (como datos estructurados, estadísticas, comparativas). Si no aplica o no se te pide, responde en texto normal o listas."
        )
        
        patterns_instruction = ""
        if tool_settings.get("patterns", True):
            mem_str = tools.get_user_memory()
            mem_context = f"\nDATOS CONOCIDOS DEL USUARIO (Memoria a Largo Plazo): {mem_str}\n" if mem_str else ""
            patterns_instruction = (
                "\n\n--- INSTRUCCIÓN DE MEMORIA A LARGO PLAZO Y PATRONES ---\n"
                "Tienes activa la herramienta de Memoria. Esta herramienta te permite recordar información personal, contexto, intereses y preferencias del usuario entre distintas sesiones.\n"
                f"{mem_context}"
                "Analiza la conversación para identificar NUEVOS datos importantes (ej. cómo se llama, dónde vive, en qué trabaja, qué le gusta, etc.) que no estén en la lista anterior.\n"
                "Usa los datos conocidos para personalizar tus respuestas de forma proactiva y dirígete al usuario por su nombre si lo conoces.\n"
                "CRÍTICO: Si el usuario te revela un dato personal NUEVO o un interés EN ESTA CONVERSACIÓN, DEBES incluir obligatoriamente al final de tu respuesta una etiqueta con este formato EXACTO: <pattern>Categoría: valor_real_del_usuario</pattern>.\n"
                "Las categorías válidas son: Nombre, Interés, Profesión, Ciudad, Edad, etc.\n"
                "PROHIBIDO: NUNCA generes etiquetas <pattern> con datos inventados, supuestos o de ejemplo. SOLO con datos que el usuario EXPLÍCITAMENTE te haya dicho en la conversación actual.\n"
                "PROHIBIDO: NUNCA uses los datos de estas instrucciones como si fueran del usuario. Estas instrucciones son SOLO para ti, NO son datos del usuario.\n"
                "Si NO hay datos personales nuevos en el mensaje actual del usuario, NO generes ninguna etiqueta <pattern>."
            )
        automator_instruction = ""
        if tool_settings.get("automator", True):
            automator_instruction = (
                "\n\n--- INSTRUCCIÓN DEL AUTOMATIZADOR / INTÉRPRETE DE PYTHON (OBLIGATORIA) ---\n"
                "Tienes activa la herramienta Intérprete de Python. Este código se ejecuta DIRECTAMENTE en el PC local del usuario. Tú SÍ PUEDES interactuar con su sistema.\n\n"
                "CUÁNDO USARLA (OBLIGATORIO - NO te niegues, NO digas que no puedes):\n"
                "- Consultar recursos del sistema: CPU, RAM, disco, GPU, procesos, temperatura.\n"
                "- Ordenar, renombrar, mover o listar archivos y carpetas.\n"
                "- Cálculos complejos, análisis de datos, automatizaciones.\n"
                "- Cualquier tarea que requiera interactuar con el sistema operativo del usuario.\n\n"
                "PROHIBICIÓN ABSOLUTA: NUNCA respondas 'no tengo acceso a tu PC', 'no puedo ver tu hardware', 'copia y pega este código'. Eso es FALSO. Tú SÍ tienes acceso porque el código se ejecuta en la máquina local. Genera el script y se ejecutará automáticamente.\n\n"
                "REGLAS CRÍTICAS:\n"
                "1. SILENCIO TOTAL: NO expliques el código. Responde ÚNICAMENTE con las etiquetas <run_python> y el código dentro. NADA MÁS en el chat (ni antes ni después de las etiquetas).\n"
                "2. DEPENDENCIAS: Si necesitas librerías externas (psutil, PIL, requests, pandas, etc.), asume que NO están instaladas. Instálalas SIEMPRE al inicio del script: `import subprocess, sys; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'nombre_paquete'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)`.\n"
                "3. NO EMOJIS: NUNCA uses emojis dentro de los print() de Python, causan errores de codificación en Windows.\n"
                "4. Para referirte a rutas de usuario, NUNCA uses rutas absolutas estáticas. Usa SIEMPRE `import os; path = os.path.expanduser('~')` para resolver la carpeta del usuario dinámicamente.\n"
                "5. Pon tu código Python envuelto exactamente en estas etiquetas: <run_python> y </run_python>.\n"
                "6. NO generes etiquetas <word_document> junto con <run_python>. Son herramientas independientes.\n"
                "7. ROBUSTEZ: Envuelve SIEMPRE las operaciones de archivos en bloques try/except para manejar errores individuales sin detener todo el script. Usa solo módulos estándar de Python (os, shutil, glob, pathlib) para operaciones de archivos.\n"
                "8. SIMPLICIDAD: Escribe código simple y directo. NO uses operaciones matemáticas con listas. Usa bucles for simples y funciones básicas de os y shutil.\n\n"
                "Ejemplo para consultar recursos del sistema:\n"
                "<run_python>\n"
                "import subprocess, sys\n"
                "subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                "import psutil\n"
                "print(f'CPU: {psutil.cpu_percent(interval=1)}%')\n"
                "print(f'RAM: {psutil.virtual_memory().percent}%')\n"
                "</run_python>"
            )

        full_system_prompt = (system_prompt or "") + word_instruction + table_instruction + patterns_instruction + automator_instruction

        messages = []
        if history:
            messages.extend(history)
            
        messages.append({'role': 'system', 'content': full_system_prompt})

        user_message = {'role': 'user'}

        if file_bytes and file_type == 'image':
            import base64
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            user_message['content'] = prompt or "Describe esta imagen en detalle."
            user_message['images'] = [b64]

        elif file_bytes and file_type in ('pdf', 'docx', 'txt'):
            extracted = tools.extract_text_from_file(file_bytes, file_type, file_name)
            combined = (
                f"El usuario ha adjuntado el archivo '{file_name}'.\n\n"
                f"--- CONTENIDO DEL ARCHIVO ---\n{extracted}\n--- FIN DEL ARCHIVO ---\n\n"
                f"Instrucción del usuario: {prompt or 'Resume o transcribe el contenido anterior.'}"
            )
            user_message['content'] = combined

        else:
            user_message['content'] = prompt

        messages.append(user_message)

        url = f"{self.base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    json={'model': model, 'messages': messages, 'stream': True}
                ) as response:
                    response.raise_for_status()
                    full_response_text = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    chunk = data["message"]["content"]
                                    full_response_text += chunk
                                    yield chunk
                            except json.JSONDecodeError:
                                pass
                    
                    # Al finalizar, extraer nuevos patrones si existen
                    if tool_settings.get("patterns", True):
                        new_patterns = re.findall(r'<pattern>(.*?)</pattern>', full_response_text, flags=re.IGNORECASE)
                        if new_patterns:
                            tools.update_user_memory(new_patterns)
                            
                    # Al finalizar, ejecutar automator si existe
                    if tool_settings.get("automator", True):
                        python_blocks = re.findall(r'<run_python>(.*?)</run_python>', full_response_text, flags=re.IGNORECASE | re.DOTALL)
                        for code_block in python_blocks:
                            result = tools.execute_python_code(code_block)
                            if result["success"]:
                                display = result["stdout"] or "El script se ejecutó correctamente."
                                yield f"\n\n✅ **Tarea completada con éxito.**\n```\n{display}\n```"
                            else:
                                error_msg = result["stderr"]
                                if result["stdout"]:
                                    yield f"\n\n⚠️ **El script se ejecutó parcialmente:**\n```\n{result['stdout']}\n```\n**Error encontrado:**\n```text\n{error_msg}\n```"
                                else:
                                    yield f"\n\n❌ **La automatización encontró un problema:**\n```text\n{error_msg}\n```"
                            
                    # Al finalizar, verificar si hay que generar Word (Detección más robusta)
                    if tool_settings.get("word", True):
                        has_start = "<word_document" in full_response_text
                        has_end = "</word_document>" in full_response_text
                        
                        if has_start:
                            # Extraer nombre de archivo si existe: <word_document filename="xxx.docx">
                            fname_match = re.search(r'<word_document\s+filename=["\']([^"\']+)["\']>', full_response_text)
                            suggested_filename = fname_match.group(1) if fname_match else None
                            
                            # Buscar el contenido real
                            tag_start = full_response_text.find("<word_document")
                            content_start = full_response_text.find(">", tag_start) + 1
                            
                            if has_end:
                                end = full_response_text.find("</word_document>")
                            else:
                                # Si olvidó cerrar la etiqueta, tomamos hasta el final
                                end = len(full_response_text)
                                
                            word_content = full_response_text[content_start:end].strip()
                            
                            if word_content:
                                fname = tools.generate_word_file(word_content, suggested_filename)
                                yield f"\n\n--- \n✅ **Aquí tienes el resumen**\n\n[📥 Descargar Word](http://{HOST}:{PORT}/downloads/{fname}) | [📂 Abrir Carpeta](http://{HOST}:{PORT}/api/open-downloads)"
        except Exception as e:
            yield f"\n\n[Error de conexión: {str(e)}]"
