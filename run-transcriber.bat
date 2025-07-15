@echo off
cd /d "%~dp0"

rem ── Check if venv exists, if not provide helpful message ───────
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo ERROR: Python virtual environment not found!
    echo.
    echo Please follow the installation instructions in README.md:
    echo 1. Create virtual environment: python -m venv venv
    echo 2. Activate it: venv\Scripts\activate
    echo 3. Install dependencies: pip install -r requirements.txt
    echo.
    echo Then run this batch file again.
    pause
    exit /b 1
)

rem ── activate venv ───────────────────────────────────────────────
call venv\Scripts\activate.bat

rem ── prepend OUR ffmpeg first ───────────────────────────────────
if exist "ffmpeg-7.1.1-essentials_build\ffmpeg_bin" (
    set "PATH=%~dp0ffmpeg-7.1.1-essentials_build\ffmpeg_bin;%PATH%"
)

rem ── prepend cuDNN + cuBLAS runtime DLLs (*before* Python starts)
if exist "%VIRTUAL_ENV%\Lib\site-packages\nvidia\cudnn\bin" (
    set "PATH=%VIRTUAL_ENV%\Lib\site-packages\nvidia\cudnn\bin;%VIRTUAL_ENV%\Lib\site-packages\nvidia\cublas\bin;%PATH%"
)

rem ── your usual flags ───────────────────────────────────────────
set "PYANNOTE_DEVICE=cuda"

rem ── launch GUI/CLI ─────────────────────────────────────────────
if "%~1"=="" (
    echo Launching Scriptotic GUI...
    python src\core\scriptotic.py
) else (
    echo Launching Scriptotic CLI...
    python src\core\scriptotic.py %*
)

rem ── keep window open if there was an error ─────────────────────
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to close...
    pause >nul
)
