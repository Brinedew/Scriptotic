#!/usr/bin/env python3
"""
Minimal test to isolate the WhisperX crash issue
"""
import os
import sys

# Set environment for CPU only (eliminate GPU issues)
os.environ["CUDA_VISIBLE_DEVICES"] = ""

print("Testing minimal WhisperX import and usage...")

try:
    import whisperx
    print("OK WhisperX imported successfully")
    
    # Test 1: Load model (CPU only with correct compute type)
    print("Loading WhisperX model (CPU)...")
    model = whisperx.load_model("tiny", device="cpu", compute_type="int8")
    print("OK Model loaded successfully")
    
    # Test 2: Check if audio file exists
    audio_file = "downloaded_audio.webm"
    if os.path.exists(audio_file):
        print(f"OK Audio file found: {audio_file}")
        
        # Test 3: Basic transcription (CPU, small batch)
        print("Starting minimal transcription...")
        result = model.transcribe(audio_file, batch_size=1)
        print(f"OK Transcription completed: {len(result['segments'])} segments")
        
        # Print first segment as test
        if result['segments']:
            print(f"First segment: {result['segments'][0]['text'][:50]}...")
    else:
        print("ERROR Audio file not found - please run main app first to download audio")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    
print("Test completed.")