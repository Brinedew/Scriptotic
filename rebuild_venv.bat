@echo off
REM Creates venv and installs latest WhisperX for CUDA 11.8/12.x
py -3.12 -m venv venv || goto :eof
call venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install whisperx torch torchvision torchaudio ^
    --extra-index-url https://download.pytorch.org/whl/cu118 ^
    ffmpeg-python
python -m pip install huggingface-hub --upgrade
setx HF_HUB_DISABLE_SYMLINKS 1
echo.
echo Setup completed.  Double-click run_transcriber.bat next time.
pause
