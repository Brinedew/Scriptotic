@echo off
cd /d "%~dp0"

rem ── activate venv ───────────────────────────────────────────────
call venv\Scripts\activate.bat

rem ── prepend OUR ffmpeg first ───────────────────────────────────
set "PATH=%~dp0ffmpeg-7.1.1-essentials_build\ffmpeg_bin;%PATH%"

rem ── prepend cuDNN + cuBLAS runtime DLLs (*before* Python starts)
set "PATH=%VIRTUAL_ENV%\Lib\site-packages\nvidia\cudnn\bin;%VIRTUAL_ENV%\Lib\site-packages\nvidia\cublas\bin;%PATH%"

rem ── your usual flags ───────────────────────────────────────────
set "PYANNOTE_DEVICE=cuda"

rem ── launch GUI/CLI ─────────────────────────────────────────────
python src\core\scriptotic.py %*
