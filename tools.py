import io
import os
import re
import uuid
import httpx
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document
from docx.shared import Pt
import yt_dlp
import asyncio
import logging
import urllib.parse
import json
import subprocess
import sys

import sqlite3

DB_FILE = 'user_profile.db'

def _init_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except Exception as e:
        logging.error(f"Error inicializando BD: {e}")

# Initialize DB on load
_init_db()

def get_user_memory() -> str:
    """Lee el perfil del usuario de la base de datos."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT topic FROM interests ORDER BY added_at ASC')
            rows = c.fetchall()
            interests = [row[0] for row in rows]
            return ", ".join(interests)
    except Exception as e:
        logging.error(f"Error leyendo memoria DB: {e}")
        return ""

def update_user_memory(new_interests: list):
    """Añade nuevos intereses a la base de datos."""
    if not new_interests:
        return
    
    added = False
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            for interest in new_interests:
                clean_interest = interest.strip().title()
                if clean_interest:
                    try:
                        c.execute('INSERT INTO interests (topic) VALUES (?)', (clean_interest,))
                        added = True
                    except sqlite3.IntegrityError:
                        # Ya existe el interés
                        pass
            if added:
                conn.commit()
                logging.info(f"Memoria actualizada en DB: {new_interests}")
    except Exception as e:
        logging.error(f"Error guardando memoria DB: {e}")

def clear_user_memory() -> bool:
    """Borra el perfil de usuario (memoria a largo plazo)."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM interests')
            conn.commit()
        logging.info("Memoria a largo plazo borrada (DB).")
        return True
    except Exception as e:
        logging.error(f"Error borrando memoria DB: {e}")
        return False

def extract_url_content(url: str) -> str:
    """Extrae el contenido principal de una URL de forma limpia."""
    try:
        # Asegurar que tiene esquema
        if not url.startswith('http'):
            url = 'https://' + url

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Eliminar ruido (scripts, estilos, nav, etc)
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
                tag.decompose()
            
            # Extraer texto con separador para mantener estructura básica
            text = soup.get_text(separator='\n')
            
            # Limpiar espacios y líneas vacías
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)
            
            # Limitar tamaño para no saturar el contexto de Ollama
            return clean_text[:8000] 
    except Exception as e:
        return f"[Error al intentar acceder a la web {url}: {str(e)}]"

async def async_extract_url_content(url: str) -> str:
    """Versión asíncrona de la extracción de URL."""
    try:
        if not url.startswith('http'):
            url = 'https://' + url

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
                tag.decompose()
            
            text = soup.get_text(separator='\n')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)
            return clean_text[:8000] 
    except Exception as e:
        return f"[Error al intentar acceder a la web {url}: {str(e)}]"

async def async_search_web(query: str, max_results: int = 5) -> str:
    """Busca en internet usando DuckDuckGo (HTML) y devuelve un resumen de los resultados."""
    try:
        url = 'https://html.duckduckgo.com/html/'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        data = {'q': query}
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for result in soup.find_all('div', class_='result'):
                if len(results) >= max_results:
                    break
                
                title_a = result.find('a', class_='result__url')
                snippet_a = result.find('a', class_='result__snippet')
                
                if title_a and snippet_a:
                    title = title_a.text.strip()
                    href = title_a.get('href', '')
                    if 'uddg' in href:
                        parsed = urllib.parse.urlparse(href)
                        qs = urllib.parse.parse_qs(parsed.query)
                        if 'uddg' in qs:
                            href = qs['uddg'][0]
                    
                    snippet = snippet_a.text.strip()
                    results.append({"title": title, "href": href, "snippet": snippet})
            
            if not results:
                return "No se encontraron resultados para la búsqueda."
                
            output = "RESULTADOS DE BÚSQUEDA:\n"
            for r in results:
                output += f"Título: {r['title']}\nEnlace: {r['href']}\nResumen: {r['snippet']}\n\n"
            
            # Extraer el contenido real de los 2 primeros enlaces
            output += "--- CONTENIDO DETALLADO DE LOS PRIMEROS RESULTADOS ---\n"
            for r in results[:2]:
                try:
                    content = await async_extract_url_content(r['href'])
                    # Limitar a 3000 caracteres por enlace para no saturar
                    output += f"\n--- WEB: {r['title']} ---\n{content[:3000]}\n"
                except Exception:
                    pass
                
            return output
    except Exception as e:
        return f"[Error al buscar en internet: {str(e)}]"

def generate_word_file(markdown_text: str, filename: str = None) -> str:
    """Genera un archivo Word (.docx) a partir de texto Markdown mejorado."""
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Limpiar nombre de archivo sugerido
    if filename:
        filename = re.sub(r'[^\w\s.-]', '', filename).strip().replace(' ', '_')
        if not filename.endswith('.docx'):
            filename += '.docx'
    else:
        filename = f"doc_{uuid.uuid4().hex[:6]}.docx"
        
    filepath = os.path.join('downloads', filename)
    
    doc = Document()
    
    # Limpiar LaTeX y caracteres raros comunes de modelos AI
    clean_text = markdown_text
    clean_text = re.sub(r'\$\\text\{(.+?)\}\$', r'\1', clean_text)
    clean_text = re.sub(r'\$(.+?)\$', r'\1', clean_text)
    clean_text = re.sub(r'\\_', '_', clean_text)
    clean_text = re.sub(r'\\text\{(.+?)\}', r'\1', clean_text)
    
    lines = clean_text.splitlines()
    
    in_table = False
    table_rows = []

    def _render_table(doc_obj, rows_data):
        if not rows_data: return
        parsed_rows = []
        for r in rows_data:
            # Skip separator rows (e.g. |---|---|)
            if re.match(r'^\|[-\s:|]+\|$', r):
                continue
            cells = [c.strip() for c in r.split('|')]
            if cells and cells[0] == '': cells.pop(0)
            if cells and cells[-1] == '': cells.pop()
            parsed_rows.append(cells)
            
        if not parsed_rows: return
        
        max_cols = max(len(r) for r in parsed_rows)
        if max_cols == 0: return
        
        try:
            table = doc_obj.add_table(rows=len(parsed_rows), cols=max_cols)
            table.style = 'Table Grid'
        except Exception:
            table = doc_obj.add_table(rows=len(parsed_rows), cols=max_cols)
            
        for row_idx, row_data in enumerate(parsed_rows):
            for col_idx, cell_text in enumerate(row_data):
                if col_idx < max_cols:
                    cell = table.cell(row_idx, col_idx)
                    cell.text = ""
                    p = cell.paragraphs[0]
                    parts = re.split(r'(\*\*.*?\*\*)', cell_text)
                    for part in parts:
                        if part.startswith('**') and part.endswith('**'):
                            p.add_run(part[2:-2]).bold = True
                        else:
                            p.add_run(part)

    for line in lines:
        line_strip = line.strip()
        
        # Detectar tablas markdown
        if line_strip.startswith('|') and line_strip.endswith('|'):
            in_table = True
            table_rows.append(line_strip)
            continue
        elif in_table:
            _render_table(doc, table_rows)
            in_table = False
            table_rows = []
            
        if not line_strip:
            doc.add_paragraph()
            continue
            
        # Detección de Cabeceras (con o sin espacio)
        if line_strip.startswith('# '):
            doc.add_heading(line_strip.lstrip('# ').strip(), level=1)
        elif line_strip.startswith('## '):
            doc.add_heading(line_strip.lstrip('# ').strip(), level=2)
        elif line_strip.startswith('### '):
            doc.add_heading(line_strip.lstrip('# ').strip(), level=3)
        elif line_strip.startswith('#### '):
            doc.add_heading(line_strip.lstrip('# ').strip(), level=4)
        
        # Listas
        elif line_strip.startswith('- ') or line_strip.startswith('* '):
            p = doc.add_paragraph(style='List Bullet')
            # Limpiar negritas dentro de la lista
            text = line_strip[2:].replace('**', '').replace('__', '')
            p.add_run(text)
            
        elif re.match(r'^\d+\. ', line_strip):
            content = re.sub(r'^\d+\. ', '', line_strip)
            p = doc.add_paragraph(style='List Number')
            # Limpiar negritas
            text = content.replace('**', '').replace('__', '')
            p.add_run(text)
            
        else:
            # Párrafo normal con soporte básico de negritas
            p = doc.add_paragraph()
            # Dividir por negritas **texto**
            parts = re.split(r'(\*\*.*?\*\*)', line_strip)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    p.add_run(part[2:-2]).bold = True
                else:
                    p.add_run(part)
                    
    if in_table:
        _render_table(doc, table_rows)
            
    doc.save(filepath)
    return filename

def extract_text_from_file(file_bytes: bytes, file_type: str, file_name: str) -> str:
    """Extrae texto de PDF, DOCX o TXT."""
    try:
        if file_type == 'txt':
            return file_bytes.decode('utf-8', errors='replace')

        elif file_type == 'pdf':
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                pages = [page.extract_text() or '' for page in reader.pages]
                return "\n\n".join(pages)
            except Exception as e:
                return f"[No se pudo extraer el texto del PDF: {e}]"

        elif file_type == 'docx':
            try:
                doc = Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                return "\n\n".join(paragraphs)
            except Exception as e:
                return f"[No se pudo extraer el texto del DOCX: {e}]"

    except Exception as e:
        return f"[Error al procesar el archivo: {e}]"

    return "[Formato no soportado]"

def download_youtube_media(url: str, mode: str = 'video', progress_callback=None) -> str:
    """Descarga video o audio de YouTube."""
    logging.info(f"tools.py: Iniciando descarga de {url} (modo: {mode})")
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Iniciar progreso en 0%
    if progress_callback:
        progress_callback(0, 'Iniciando descarga...')

    last_percent = -1
    def hook(d):
        nonlocal last_percent
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                percent = float(p)
                if percent >= last_percent + 1:
                    last_percent = percent
                    if progress_callback:
                        progress_callback(percent, 'Descargando...')
            except:
                pass
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback(100, 'Finalizando...')

    ydl_opts = {
        'progress_hooks': [hook],
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'source_address': '0.0.0.0', # Forzar IPv4 para evitar timeouts de red
        'nocheckcertificate': True,
    }

    if mode == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Si es audio, la extensión cambia a .mp3 por el postprocessor
            if mode == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'
            return os.path.basename(filename)
    except Exception as e:
        error_msg = str(e)
        if "ffmpeg" in error_msg.lower():
            return "Error: FFmpeg no encontrado. Es necesario para procesar videos de YouTube. Por favor instálalo."
        return f"Error: {error_msg}"

def execute_python_code(code: str) -> str:
    """Ejecuta código Python localmente de forma segura capturando la salida."""
    try:
        logging.info("tools.py: Ejecutando script de python generado por IA.")
        # Limpiar posibles comillas markdown residuales
        if code.startswith("```python"):
            code = code[9:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()

        # Ejecutar en un subproceso con timeout de 30s
        import os
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nErrores/Advertencias:\n{result.stderr}"
            
        if not output.strip():
            return "El script se ejecutó correctamente sin devolver ninguna salida visible."
            
        return output.strip()
    except subprocess.TimeoutExpired:
        return "Error: El script tardó demasiado (más de 30 segundos) y fue interrumpido."
    except Exception as e:
        return f"Error crítico al ejecutar: {e}"
