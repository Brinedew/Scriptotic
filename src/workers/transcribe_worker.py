#!/usr/bin/env python3
"""
Isolated WhisperX transcription worker to avoid process state pollution.
Runs in clean subprocess environment with minimal dependencies.
"""

import os
import sys
import json
import argparse

# Fix sys.path for proper imports when running as subprocess
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))  # Go up two levels: workers -> src -> project_root
core_dir = os.path.join(project_root, 'src', 'core')

# Add project root and core directory to sys.path for imports
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Add the cuDNN DLL directories using correct project root path
if sys.platform == "win32":
    import pathlib
    venv = pathlib.Path(project_root) / "venv"  # Use project_root calculated above
    print(f"DEBUG: Looking for DLLs in venv: {venv}", file=sys.stderr)
    for sub in ("nvidia/cudnn/bin", "nvidia/cublas/bin"):
        p = venv / "Lib" / "site-packages" / sub
        print(f"DEBUG: Checking DLL path: {p}, exists: {p.exists()}", file=sys.stderr)
        if p.exists():
            os.add_dll_directory(str(p))
            print(f"DEBUG: Added DLL directory: {p}", file=sys.stderr)
        else:
            print(f"DEBUG: DLL directory not found: {p}", file=sys.stderr)

# Import only what we absolutely need
try:
    from src.core.whisperx_engine import WhisperXEngine
except ImportError:
    sys.path.append('src/core')
    from whisperx_engine import WhisperXEngine

# Debug: Check what whisperx module we're getting
import whisperx
print(f"DEBUG: whisperx module location: {whisperx.__file__}", file=sys.stderr)
print(f"DEBUG: whisperx.diarize exists: {hasattr(whisperx, 'diarize')}", file=sys.stderr)

# Check if DiarizationPipeline can be imported
try:
    from whisperx.diarize import DiarizationPipeline
    print(f"DEBUG: whisperx.diarize.DiarizationPipeline import: SUCCESS", file=sys.stderr)
except ImportError as e:
    print(f"DEBUG: whisperx.diarize.DiarizationPipeline import: FAILED - {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Isolated WhisperX transcription worker')
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large'])
    parser.add_argument('--speakers', help='Speaker names (comma-separated)')
    parser.add_argument('--hf-token', help='HuggingFace token')
    
    args = parser.parse_args()
    
    # Debug: Print environment info to stderr
    print(f"DEBUG: Current working directory: {os.getcwd()}", file=sys.stderr)
    print(f"DEBUG: sys.path: {sys.path[:3]}...", file=sys.stderr)
    print(f"DEBUG: __file__ location: {__file__}", file=sys.stderr)
    print(f"DEBUG: Project root removed from sys.path: {project_root not in sys.path}", file=sys.stderr)
    
    try:
        # Parse speaker names
        speaker_names = None
        if args.speakers:
            speaker_names = [s.strip() for s in args.speakers.split(',')]
        
        # Initialize engine in clean environment
        engine = WhisperXEngine(
            model_size=args.model,
            hf_token=args.hf_token or os.getenv("HUGGINGFACE_TOKEN")
        )
        
        # Perform transcription with memory management
        try:
            print(f"DEBUG: Starting transcription of {args.audio_file}", file=sys.stderr)
            segments, diarization_method = engine.transcribe_with_speakers(args.audio_file, speaker_names=speaker_names)
            print(f"DEBUG: Transcription completed successfully", file=sys.stderr)
        except Exception as transcribe_error:
            print(f"DEBUG: Transcription failed with error: {transcribe_error}", file=sys.stderr)
            print(f"DEBUG: Error type: {type(transcribe_error).__name__}", file=sys.stderr)
            # Try to clean up memory
            import gc
            gc.collect()
            raise transcribe_error
        
        # Output result as JSON to stdout (use stderr for debug output)
        result = {
            "success": True,
            "model": args.model,
            "diarization_method": diarization_method,
            "segments": segments,
            "segment_count": len(segments)
        }
        
        # Only print JSON to stdout, everything else goes to stderr
        print(json.dumps(result), file=sys.stdout)
        print(f"SUCCESS: Transcribed {len(segments)} segments", file=sys.stderr)
        
    except Exception as e:
        # Output error as JSON to stdout
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(json.dumps(error_result), file=sys.stdout)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()