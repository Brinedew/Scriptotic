@echo off
cd /d "%~dp0"

rem ── Single entry point for all Scriptotic operations ──────────
rem ── Handles setup, testing, and launching automatically ──────

rem Check if this is a reset request
if "%1"=="--reset" goto :reset_environment

rem Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo First time setup - creating Python environment...
    call :setup_environment
    if %errorlevel% neq 0 exit /b 1
)

rem Activate virtual environment
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Virtual environment activation failed - recreating...
    call :reset_environment
    if %errorlevel% neq 0 exit /b 1
    call venv\Scripts\activate.bat
)

rem Test if WhisperX is working
python -c "import whisperx" >nul 2>&1
if %errorlevel% neq 0 (
    echo WhisperX missing - installing...
    call :install_packages
    if %errorlevel% neq 0 exit /b 1
)

rem Set environment variables
set "PYANNOTE_DEVICE=cuda"
if exist "ffmpeg-7.1.1-essentials_build\ffmpeg_bin" (
    set "PATH=%~dp0ffmpeg-7.1.1-essentials_build\ffmpeg_bin;%PATH%"
)
if exist "%VIRTUAL_ENV%\Lib\site-packages\nvidia\cudnn\bin" (
    set "PATH=%VIRTUAL_ENV%\Lib\site-packages\nvidia\cudnn\bin;%VIRTUAL_ENV%\Lib\site-packages\nvidia\cublas\bin;%PATH%"
)

rem Launch Scriptotic
if "%~1"=="" (
    python src\core\scriptotic.py
) else (
    python src\core\scriptotic.py %*
)

rem Keep window open on error
if %errorlevel% neq 0 (
    echo.
    echo Error occurred. Press any key to close...
    pause >nul
)
exit /b %errorlevel%

:setup_environment
echo.
echo ============================================
echo    SCRIPTOTIC SETUP
echo ============================================
echo.

rem Check Python version and find compatible one
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Default Python version: %PYTHON_VERSION%

rem Check if we have Python 3.13 (incompatible)
echo %PYTHON_VERSION% | findstr /C:"3.13" >nul
if %errorlevel% equ 0 (
    echo Python 3.13 detected - finding compatible version...
    py -3.12 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Using Python 3.12 for compatibility
        set PYTHON_CMD=py -3.12
        goto :python_found
    )
    py -3.11 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Using Python 3.11 for compatibility
        set PYTHON_CMD=py -3.11
        goto :python_found
    )
    py -3.10 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Using Python 3.10 for compatibility
        set PYTHON_CMD=py -3.10
        goto :python_found
    )
    py -3.9 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Using Python 3.9 for compatibility
        set PYTHON_CMD=py -3.9
        goto :python_found
    )
    echo ERROR: WhisperX requires Python 3.9-3.12
    echo Please install Python 3.12 from python.org
    pause
    exit /b 1
) else (
    set PYTHON_CMD=python
)

:python_found

echo Creating virtual environment...
%PYTHON_CMD% -m venv venv || exit /b 1

echo Activating virtual environment...
call venv\Scripts\activate.bat || exit /b 1

call :install_packages
exit /b %errorlevel%

:install_packages
echo Installing packages...
python -m pip install --upgrade pip || exit /b 1
echo Installing PyTorch 2.2.2 with correct cuDNN libraries...
python -m pip install "torch==2.2.2" "torchvision==0.17.2" "torchaudio==2.2.2" --index-url https://download.pytorch.org/whl/cu121 || (
    python -m pip install "torch==2.2.2" "torchvision==0.17.2" "torchaudio==2.2.2" || exit /b 1
)
echo Installing compatible versions to avoid Windows crash...
python -m pip install "faster-whisper==1.0.0" "ctranslate2==4.4.0" || exit /b 1
python -m pip install whisperx yt-dlp pyannote.audio huggingface-hub transformers || exit /b 1

echo Verifying installation...
python -c "import torch; import whisperx; import yt_dlp; import pyannote.audio; print('All packages working')" || exit /b 1

setx HF_HUB_DISABLE_SYMLINKS 1 >nul
echo Setup complete!
exit /b 0

:reset_environment
echo Resetting environment...
if exist venv rmdir /s /q venv
call :setup_environment
exit /b %errorlevel%