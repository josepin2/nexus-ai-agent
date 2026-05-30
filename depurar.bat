@echo off
title Debug Agente IA

cd /d "%~dp0"

call venv\Scripts\activate

echo ============================
echo INICIANDO BACKEND EN DEBUG
echo ============================
echo.

python main.py 2> error_log.txt

echo.
echo ============================
echo ERROR CAPTURADO
echo ============================
echo.

type error_log.txt

echo.
pause