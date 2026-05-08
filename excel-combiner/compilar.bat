@echo off
echo ============================================================
echo        COMPILADOR - COMBINADOR DE EXCEL
echo ============================================================
echo.

echo [1/2] Instalando dependencias...
pip install -r requirements.txt
echo.

echo [2/2] Compilando...
pyinstaller --onefile --console --name "Combinador Excel" combinador.py
echo.

echo ============================================================
echo Listo! El .exe esta en la carpeta "dist"
echo ============================================================
pause
