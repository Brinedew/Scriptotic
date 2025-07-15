#!/usr/bin/env python3
"""
Test WhisperX with GPU to confirm crash point
"""
import os

print("Testing WhisperX with GPU...")

try:
    import whisperx
    print("OK WhisperX imported successfully")
    
    # Test with GPU (this should crash)
    print("Loading WhisperX model (CUDA)...")
    model = whisperx.load_model("tiny", device="cuda", compute_type="float16")
    print("OK Model loaded successfully on GPU")
    
    # If we get here, check audio file
    audio_file = "downloaded_audio.webm"
    if os.path.exists(audio_file):
        print(f"OK Audio file found: {audio_file}")
        print("Starting GPU transcription (this might crash)...")
        result = model.transcribe(audio_file, batch_size=1)
        print(f"OK Transcription completed: {len(result['segments'])} segments")
    else:
        print("ERROR Audio file not found")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    
print("Test completed.")