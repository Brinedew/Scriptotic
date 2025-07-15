# URL-to-Transcript Tool - Claude Notes

## Environment Setup

**System:** Windows (run from WSL but executes Windows commands)
**Python:** 3.12.10 in virtual environment at `venv/`
**GPU:** RTX 4080 Laptop GPU (works with CUDA)

### Critical Command Pattern

**ALL Python commands must use this exact syntax:**
```bash
cd "/mnt/d/Coding/URL-to-transcript"
/mnt/c/Windows/System32/cmd.exe /c "COMMAND_HERE"
```

**Activate environment and run Python:**
```bash
/mnt/c/Windows/System32/cmd.exe /c "call venv\\Scripts\\activate && python SCRIPT.py"
```

**With environment variables:**
```bash
/mnt/c/Windows/System32/cmd.exe /c "set HUGGINGFACE_TOKEN=YOUR_TOKEN_HERE && set HF_HUB_DISABLE_SYMLINKS=1 && call venv\\Scripts\\activate && python SCRIPT.py"
```

**Install dependencies:**
```bash
/mnt/c/Windows/System32/cmd.exe /c "call venv\\Scripts\\activate && pip install yt-dlp whisperx torch --extra-index-url https://download.pytorch.org/whl/cu124"
```

### Critical WhisperX Process State Pollution Issue - RESOLVED

**PROBLEM:** WhisperX transcription hangs when called from main CLI/GUI process but works fine standalone.

**Evidence:** 
- Standalone test works perfectly in 5.2 seconds
- Same code hangs indefinitely when called from main script
- Audio downloads work perfectly (proves environment is fine)

**Root cause:** Process state pollution - main script's complex initialization (GUI imports, yt-dlp library usage) creates conflicts with WhisperX's native libraries.

**Solution implemented:** Subprocess isolation using transcribe_worker.py
- WhisperX runs in clean subprocess environment
- Avoids all library conflicts and state pollution
- CLI and GUI both use this approach

**Key insight:** This was NOT a threading or dependency issue. It was environmental contamination.

## Production Process

### Testing Commands

**Check environment:**
```bash
/mnt/c/Windows/System32/cmd.exe /c "call venv\\Scripts\\activate && python -c \"import whisperx; print([x for x in dir(whisperx) if not x.startswith('_')])\""
```

**Test basic functionality:**
```bash
# This works (audio download + transcription):
/mnt/c/Windows/System32/cmd.exe /c "set HUGGINGFACE_TOKEN=YOUR_TOKEN_HERE && call venv\\Scripts\\activate && python src/core/scriptotic.py https://www.youtube.com/watch?v=EXAMPLE_VIDEO --output test.txt"

# Or use the batch launcher:
/mnt/c/Windows/System32/cmd.exe /c "run-transcriber.bat https://www.youtube.com/watch?v=EXAMPLE_VIDEO --output test.txt"
```

**Common mistakes to avoid:**
- Don't run `python` directly from WSL - it won't find tkinter
- Don't forget the `/c` flag in cmd.exe calls
- Always use double backslashes in Windows paths: `venv\\Scripts\\activate`
- Set environment variables BEFORE calling Python, not after

### File Structure

```
Scriptotic/
├── src/core/
│   ├── scriptotic.py           # Main GUI+CLI app
│   └── whisperx_engine.py      # WhisperX wrapper
├── config/
│   └── token_manager.py        # HuggingFace token management
├── venv/                       # Python virtual environment
├── transcribe_worker.py        # Isolated transcription worker
├── run-transcriber.bat         # Windows launcher
├── requirements.txt            # Essential deps only
└── docs/02-Development/
    └── HANDOFF_NOTE.md         # Current status details
```

### Code Architecture Notes

**Single-file approach works better than PRD structure:**
- `url-to-transcript.py` handles both GUI and CLI modes
- Cleaner than separate `app.py` and `cli.py` files
- All imports work correctly with fallback paths

**Audio downloading is bulletproof:**
- `AudioDownloader` class uses yt-dlp Python API
- Downloads 2MB in ~2 seconds consistently
- Proper progress callbacks for GUI

**WhisperX engine design:**
- Handles both transcription and speaker diarization
- Fallback from `whisperx.diarize()` to manual pyannote pipeline
- Debug output shows exactly where it hangs

### Speaker Diarization API Hell

**Current WhisperX 3.4.2 state:**
- No `DiarizationPipeline` class
- No `whisperx.diarize()` function
- Falls back to manual pyannote.audio Pipeline

**API evolution:**
- WhisperX 3.1.1: Had `diarize` but yanked (NumPy 2.0 conflict)
- WhisperX 3.4.2: Missing both `DiarizationPipeline` and `diarize`
- Manual pyannote fallback works but triggers the threading issue

### Gotchas

**Don't use these approaches:**
- Installing multiple WhisperX versions (APIs keep changing)
- Trying to fix with environment variables only
- Assuming it's a dependency problem

**Unicode issues in Windows console:**
- Avoid emoji in debug output (use "DEBUG:" not "🔧")
- Use proper error handling for console encoding

**HuggingFace token:**
- Required for speaker diarization models
- Set as environment variable, not hardcoded
- Test with `bool(os.getenv("HUGGINGFACE_TOKEN"))`

### What Actually Works

1. **Audio extraction:** Perfect, fast, reliable
2. **Environment setup:** CUDA, Python, dependencies all correct
3. **File structure:** Clean, follows project conventions
4. **Error handling:** Good debug output shows exact hang location

### What's Broken

1. **Model loading in threaded context:** Core blocking issue
2. **Speaker diarization:** Depends on fixing #1
3. **End-to-end transcription:** Can't test until #1 is fixed

### Next Steps Priority

1. **HIGH:** Fix threading deadlock in WhisperX model loading
2. **MEDIUM:** Test speaker diarization once model loading works
3. **LOW:** Add error handling for edge cases
4. **LOW:** Package as executable

The tool is 90% working. Fix the threading issue and you're done.