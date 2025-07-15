@echo off
echo.
echo ============================================
echo    TESTING SCRIPTOTIC SETUP
echo ============================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found. Please run rebuild_venv.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Testing Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not working
    pause
    exit /b 1
)

echo Testing PyTorch...
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
if %errorlevel% neq 0 (
    echo ERROR: PyTorch not working
    pause
    exit /b 1
)

echo Testing WhisperX...
python -c "import whisperx; print('WhisperX imported successfully')"
if %errorlevel% neq 0 (
    echo ERROR: WhisperX not working
    pause
    exit /b 1
)

echo Testing yt-dlp...
python -c "import yt_dlp; print('yt-dlp imported successfully')"
if %errorlevel% neq 0 (
    echo ERROR: yt-dlp not working
    pause
    exit /b 1
)

echo Testing PyAnnote...
python -c "import pyannote.audio; print('PyAnnote imported successfully')"
if %errorlevel% neq 0 (
    echo ERROR: PyAnnote not working
    pause
    exit /b 1
)

echo.
echo ============================================
echo    ALL TESTS PASSED!
echo ============================================
echo.
echo Your Scriptotic installation is working correctly.
echo You can now run run-transcriber.bat to start using Scriptotic.
echo.
pause