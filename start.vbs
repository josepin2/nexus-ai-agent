' start.vbs
' Lanza la aplicación sin ventana de consola
' Basado en start.bat - Activa el entorno virtual y abre el navegador automáticamente
' ========================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obtener el directorio donde está este script
strDir = fso.GetAbsolutePathName(".")
WshShell.CurrentDirectory = strDir

' ========================================
' 1. Crear entorno virtual si no existe
' ========================================
If Not fso.FolderExists(strDir & "\venv") Then
    WshShell.Run "cmd.exe /C python -m venv venv", 0, True
End If

' ========================================
' 2. Definir rutas del entorno virtual
' ========================================
venvPython = """" & strDir & "\venv\Scripts\python.exe"""
venvPip    = """" & strDir & "\venv\Scripts\pip.exe"""

' ========================================
' 3. Instalar/actualizar dependencias
' ========================================
WshShell.Run "cmd.exe /C " & venvPython & " -m pip install --upgrade pip -q", 0, True
WshShell.Run "cmd.exe /C " & venvPip & " install -r requirements.txt -q", 0, True

' ========================================
' 4. Iniciar servidor FastAPI (oculto)
' ========================================
WshShell.Run "cmd.exe /C " & venvPython & " main.py", 0, False

' ========================================
' 5. Iniciar servidor web para frontend (oculto)
' ========================================
WshShell.Run "cmd.exe /C " & venvPython & " -m http.server 3000", 0, False

' ========================================
' 6. Esperar 4 segundos para que los servidores se inicien
' ========================================
WScript.Sleep 4000

' ========================================
' 7. Abrir navegador con la dirección del frontend
' ========================================
WshShell.Run "http://localhost:3000"
