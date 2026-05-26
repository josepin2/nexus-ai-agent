@echo off
title Actualizar Repositorio - Nexus AI
chcp 65001 > nul

echo ===================================================
echo   NEXUS AI - Actualizador de Repositorio
echo ===================================================
echo.
echo [INFO] Obteniendo las últimas actualizaciones desde GitHub...
echo.

git pull

if errorlevel 1 (
    echo.
    echo ❌ [ERROR] Hubo un problema al intentar actualizar el repositorio.
    echo Asegúrate de tener Git instalado y conexión a Internet.
) else (
    echo.
    echo ✅ [ÉXITO] El repositorio ha sido actualizado correctamente.
)

echo.
echo Presiona cualquier tecla para salir...
pause > nul
