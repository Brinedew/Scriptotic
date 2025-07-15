@echo off
echo.
echo ============================================
echo    SCRIPTOTIC FIRST-TIME SETUP
echo ============================================
echo.
echo This will set up everything you need to run Scriptotic.
echo This only needs to be done once.
echo.
echo Setting up Python environment...
echo.

REM Try different Python commands to find the right one
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python is not installed or not in PATH
        echo Please install Python 3.8 or newer from python.org
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo Creating virtual environment...
%PYTHON_CMD% -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing CUDA-enabled PyTorch...
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

echo Installing WhisperX and dependencies...
python -m pip install whisperx yt-dlp

echo Installing speaker diarization components...
python -m pip install pyannote.audio

echo Installing additional dependencies...
python -m pip install huggingface-hub transformers librosa soundfile

echo Setting HuggingFace configuration...
setx HF_HUB_DISABLE_SYMLINKS 1

echo.
echo ============================================
echo    SETUP COMPLETED SUCCESSFULLY!
echo ============================================
echo.
echo You can now double-click run-transcriber.bat to start Scriptotic.
echo.
echo On first run, you'll need to:
echo 1. Enter your HuggingFace token
echo 2. Accept AI model licenses
echo.
echo See README.md for HuggingFace setup instructions.
echo.
pause
