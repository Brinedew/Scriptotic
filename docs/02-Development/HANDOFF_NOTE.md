# what i was working on - July 15, 2025

I was fixing a diarization accuracy problem in the URL-to-transcript tool. The basic transcription worked fine, but when speakers had rapid back-and-forth dialogue (like "oh really?", "what?", "no"), the diarization was lumping everything into massive blocks under one speaker instead of properly separating who said what.

## what actually works now

**The core functionality is solid:**
- GUI starts without crashes ✅
- Downloads YouTube audio without hanging ✅
- Transcribes with WhisperX using subprocess isolation ✅
- Displays errors in text area instead of annoying popups ✅
- Has model selector (tiny through large) ✅
- Speaker name mapping works (Linus/Luke instead of SPEAKER_01/02) ✅
- Outputs proper transcript with title, model info, and diarization method ✅

**Commands that work:**
```bash
cd "/mnt/d/Coding/Scriptotic"
/mnt/c/Windows/System32/cmd.exe /c "set HUGGINGFACE_TOKEN=YOUR_TOKEN_HERE && call venv\\Scripts\\activate && python src/core/scriptotic.py"
```

GUI defaults are set for testing:
- URL: https://www.youtube.com/watch?v=htOvH12T7mU
- Speakers: Scott, Dwarkesh, Daniel
- Model: large
- Output: transcript.txt

**Files I changed:**
- `src/core/scriptotic.py` - Lines 207-211: Added default test values. Lines 120-129: Fixed error display to show in text area. Lines 370-381: Fixed subprocess path and added cwd parameter. Lines 413-425: Added diarization_method to output formatting.
- `src/core/whisperx_engine.py` - Lines 84-159: Added cascading diarization methods (custom fine-grained → standard WhisperX → manual pyannote). Lines 184-278: Added post-processing to split long segments. Lines 142-178: Added speaker name mapping. Returns diarization_method now.
- `transcribe_worker.py` - Lines 12-25: Fixed sys.path namespace collision by removing project root. Lines 84-93: Added diarization_method to JSON output.
- `docs/bugs_log.md` - Updated Bug #9 with complete analysis of diarization accuracy issues.

## what's broken

**The main problem: massive dialogue blocks aren't getting split**

Looking at `/output/1.txt`, line 9 is still a giant wall of text that clearly contains rapid speaker exchanges:

```
[Linus]  I mean, it's been, it's been kind of, uh, it's been kind of eye opening... oh, really? It's jarring. Yeah... what no okay i'm pretty sure that's how people use that term no i think that's the n-word what are you guys talking about am i mistaken i think so...
```

This should be multiple separate speaker segments, not one massive Linus block.

**What I tried that didn't work:**
1. Custom fine-grained diarization with tuned VAD parameters (lines 84-123 in whisperx_engine.py) - fails and falls back to standard method
2. Post-processing to split long segments (lines 184-278) - code runs but doesn't actually split the segments

**Current status in output:**
- Shows "Diarization: WhisperX DiarizationPipeline" (not "Custom Fine-Grained Pipeline")
- Transcript identical to previous attempts
- Post-processing debug output not visible, suggesting it's not working

## where things stand

**Environment:**
- Windows 11 WSL2
- Python 3.12.10 in working venv at `venv/`
- CUDA 12.9 with PyTorch 2.6.0+cu124
- WhisperX 3.4.2 with HuggingFace auth working
- HuggingFace token accepted conditions for pyannote models

**What's currently working:**
- WhisperX transcription and basic diarization
- HuggingFace model downloads (no more auth errors)
- Speaker name mapping
- Subprocess isolation (fixed the original hanging issues)

**Test commands:**
```bash
# Test worker directly
cd "/mnt/d/Coding/Scriptotic"
/mnt/c/Windows/System32/cmd.exe /c "set HUGGINGFACE_TOKEN=YOUR_TOKEN_HERE && call venv\\Scripts\\activate && python transcribe_worker.py test_audio_raw.webm --model tiny"

# Test full GUI
/mnt/c/Windows/System32/cmd.exe /c "set HUGGINGFACE_TOKEN=YOUR_TOKEN_HERE && call venv\\Scripts\\activate && python src/core/scriptotic.py"
```

## what to do next

**Most urgent: Fix the post-processing segment splitting**

The post-processing code in `whisperx_engine.py` lines 184-278 should be splitting long segments but isn't working. Debug steps:

1. **Check if post-processing runs at all** - add more debug output to see if the code is even reached
2. **Check segment duration calculation** - the 30-second threshold might be wrong, or segments might not be as long as expected
3. **Test the text splitting logic** - make sure it's finding the split indicators like "? " and "really? "

**Alternative approaches to try:**
1. **Different VAD parameters** - research showed window size and shift length are key for rapid speaker changes
2. **Different diarization model** - maybe try "pyannote/speaker-diarization-3.0" instead of 3.1
3. **Completely different approach** - use a different diarization library or two-pass processing

**Files to focus on:**
- `src/core/whisperx_engine.py` lines 184-278 (the post-processing logic)
- Check debug output in transcribe_worker.py to see what's actually happening
- Maybe the segment isn't actually >30 seconds long?

## stuff to remember

**The breakthrough insight:** The original threading/hanging issues were caused by sys.path namespace collision, not actual threading problems. Removing the project root from sys.path in transcribe_worker.py fixed all the hanging issues.

**Diarization accuracy is fundamentally hard:** Research shows WhisperX/pyannote struggles with rapid speaker changes, short utterances, and conversational dialogue. Default parameters are designed for longer monologues, not back-and-forth chat.

**Working patterns that definitely work:**
- Subprocess isolation for both yt-dlp and WhisperX
- HuggingFace token authentication with accepted user conditions
- Error display in GUI text area instead of popups
- Speaker name mapping after diarization

**The environment is solid now:** All the basic plumbing works perfectly. This is purely a diarization accuracy tuning problem, not a fundamental system issue.

The next person should focus on debugging why the post-processing isn't splitting that massive opening dialogue block. Everything else works great.