#!/usr/bin/env python3
"""
Isolated WhisperX transcription worker to avoid process state pollution.
Runs in clean subprocess environment with minimal dependencies.
"""

import os
import sys
import json
import argparse

# Fix sys.path to prevent namespace collision with project root
project_root = os.path.dirname(os.path.abspath(__file__))
# Remove all variations of project root from sys.path
paths_to_remove = [
    project_root,
    os.path.normpath(project_root),
    project_root.replace('\\', '/'),
    project_root.replace('/', '\\'),
    '',  # Empty string (current directory)
    '.'  # Current directory
]
for path in paths_to_remove:
    while path in sys.path:
        sys.path.remove(path)

# Add the cuDNN DLL directories
if sys.platform == "win32":
    import pathlib
    script_dir = pathlib.Path(__file__).resolve().parent
    venv = script_dir / "venv"
    for sub in ("nvidia/cudnn/bin", "nvidia/cublas/bin"):
        p = venv / "Lib" / "site-packages" / sub
        if p.exists():
            os.add_dll_directory(str(p))

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
        
        # Perform transcription
        segments, diarization_method = engine.transcribe_with_speakers(args.audio_file, speaker_names=speaker_names)
        
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