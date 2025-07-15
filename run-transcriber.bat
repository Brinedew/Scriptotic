@echo off
cd /d "%~dp0"

rem ── Check if venv exists, if not run setup automatically ───────
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo First time running Scriptotic - setting up automatically...
    echo.
    call rebuild_venv.bat
    if %errorlevel% neq 0 (
        echo.
        echo Setup failed. Please check the error messages above.
        pause
        exit /b 1
    )
    echo.
    echo Setup completed! Starting Scriptotic...
    echo.
)

rem ── activate venv ───────────────────────────────────────────────
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated successfully

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

rem ── Test WhisperX installation ─────────────────────────────────
echo Testing WhisperX installation...
python -c "import whisperx; print('WhisperX imported successfully')"
if %errorlevel% neq 0 (
    echo ERROR: WhisperX is not properly installed
    echo Please run rebuild_venv.bat to reinstall dependencies
    pause
    exit /b 1
)

rem ── launch GUI/CLI ─────────────────────────────────────────────
if "%~1"=="" (
    echo Launching Scriptotic GUI...
    echo Current directory: %CD%
    echo Python path: %PATH%
    python src\core\scriptotic.py
) else (
    echo Launching Scriptotic CLI...
    echo Current directory: %CD%
    python src\core\scriptotic.py %*
)

rem ── keep window open if there was an error ─────────────────────
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to close...
    pause >nul
)
