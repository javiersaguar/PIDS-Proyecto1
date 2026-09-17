@echo off
REM ===========================================================================
REM  Grabador del dataset de gestos - PIDS 26/27, Project 1   (kit v2)
REM
REM  Doble clic: pregunta tu identificador (p1..p5) y la mano.
REM  O desde PowerShell / cmd, dentro de esta carpeta:
REM      .\grabar_dataset.bat --participante p3 --mano derecha
REM      .\grabar_dataset.bat --participante p3 --prueba
REM
REM  Cada ejecucion crea una carpeta NUEVA:  HAR_mediapipe\data\gestos_<id>_<fecha-hora>
REM  Nunca se sobreescribe una toma anterior.
REM
REM  Sin bloques if ( ... ): solo goto. Asi no hacen falta variables con
REM  expansion retardada y el .bat funciona igual con finales de linea LF o CRLF.
REM ===========================================================================
setlocal
set PYTHONUTF8=1
set GLOG_minloglevel=2
set TF_CPP_MIN_LOG_LEVEL=2

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY if exist "%~dp0..\.venv\Scripts\python.exe" set "PY=%~dp0..\.venv\Scripts\python.exe"
if not defined PY goto :sinvenv

set "SCRIPT=%~dp0HAR_mediapipe\src\record_dataset.py"

if not "%~1"=="" goto :conargumentos

echo.
echo  ==============================================================
echo   GRABACION DEL DATASET DE GESTOS - PIDS 26/27
echo  ==============================================================
echo.
set /p "PARTICIPANTE=  Tu identificador de participante (p1, p2, p3, p4 o p5): "
set /p "MANO=  Mano con la que vas a grabar (izquierda / derecha): "
echo.
if not defined PARTICIPANTE goto :faltaid
if defined MANO goto :conmano
"%PY%" "%SCRIPT%" --participante "%PARTICIPANTE%"
goto :fin

:conmano
"%PY%" "%SCRIPT%" --participante "%PARTICIPANTE%" --mano "%MANO%"
goto :fin

:conargumentos
"%PY%" "%SCRIPT%" %*
goto :fin

:faltaid
echo [ERROR] No has escrito tu identificador de participante. Vuelve a lanzarlo.
goto :fin

:sinvenv
echo.
echo [ERROR] No encuentro el entorno virtual .venv
echo.
echo Crea el entorno una sola vez, desde esta misma carpeta:
echo     py -3.12 -m venv .venv
echo     .venv\Scripts\python.exe -m pip install --upgrade pip
echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.

:fin
echo.
echo Pulsa una tecla para cerrar esta ventana.
pause >nul
endlocal
