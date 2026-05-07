@echo off
setlocal

echo ========================================
echo Chatbot Ollama - Inicializando
echo ========================================
echo.

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo [INFO] Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
)

REM Activar entorno virtual
echo [INFO] Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias si no están instaladas
echo [INFO] Verificando dependencias...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

echo.
echo ========================================
echo Servidor iniciando
echo ========================================
echo.

REM Iniciar el servidor FastAPI en segundo plano (en la misma ventana)
echo [INFO] Inicializando servidor FastAPI...
start /B python main.py

REM Iniciar servidor web para el frontend en segundo plano (en la misma ventana)
echo [INFO] Inicializando servidor web para frontend...
start /B python -m http.server 3000

echo.
echo [INFO] API iniciada en http://127.0.0.1:8000
echo [INFO] Frontend iniciado en http://127.0.0.1:3000
echo [INFO] Abriendo interfaz web en el navegador...
echo.
echo [INFO] IMPORTANTE: Asegurate de que Ollama este corriendo
echo [INFO] en http://localhost:11434
echo.

REM Esperar a que los servidores se inicialicen y luego abrir el navegador
timeout /t 3 >nul 2>&1
start http://127.0.0.1:3000

echo.
echo ========================================
echo Chatbot listo (Presiona Ctrl+C para salir)
echo ========================================
echo.

REM Mantener la ventana abierta para ver los logs
waitfor /T 9999999999 PAUSE >nul 2>&1