# src/core/whisperx_engine.py
import os, whisperx, torch, tempfile
from datetime import timedelta

class WhisperXEngine:
    """
    Drop-in replacement for TranscriptionEngine that uses whisperx
    to do *both* transcription *and* diarisation in one call.
    """

    def __init__(self, model_size="base", device=None, progress_callback=None,
                 hf_token=None):
        self.debug = os.getenv("WHISPERX_DEBUG", "false").lower() == "true"
        if self.debug:
            print(f"DEBUG: WhisperX engine starting initialization...")
            
        self.progress_callback = progress_callback
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype  = torch.float16 if self.device == "cuda" else torch.float32
        self.model_size = model_size  # Store for output formatting
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")

        if self.debug:
            print(f"DEBUG: Using device: {self.device}, model: {model_size}")
        if self.progress_callback:
            self.progress_callback(10, f"Loading WhisperX ({model_size}) on {self.device}...")

        if self.debug:
            print(f"DEBUG: About to call whisperx.load_model({model_size}, {self.device})...")
        
        # whisperx automatically grabs the correct English checkpoints
        try:
            self.model = whisperx.load_model(model_size, self.device, compute_type="float16" if self.device=="cuda" else "int8")
            if self.debug:
                print(f"DEBUG: whisperx.load_model() returned successfully!")
                print(f"DEBUG: WhisperX model loaded successfully")
        except Exception as e:
            print(f"DEBUG: Failed to load WhisperX model on {self.device}: {e}")
            if self.device == "cuda":
                print(f"DEBUG: Falling back to CPU")
                self.device = "cpu"
                self.dtype = torch.float32
                try:
                    self.model = whisperx.load_model(model_size, self.device, compute_type="int8")
                    if self.debug:
                        print(f"DEBUG: WhisperX model loaded successfully on CPU")
                except Exception as cpu_error:
                    print(f"DEBUG: Failed to load model on CPU too: {cpu_error}")
                    raise cpu_error
            else:
                raise e

    # ------------------------------------------------------------------
    # Public API identical to old engine
    # ------------------------------------------------------------------
    def transcribe_with_speakers(self, audio_path, speaker_names=None):
        """
        Returns list of segments with keys:
        start, end (sec float), text, speaker  ― same shape as before.
        """
        if self.debug:
            print(f"DEBUG: Starting WhisperX transcription of: {audio_path}")
        if self.progress_callback: self.progress_callback(30, "Transcribing audio...")
        
        # Use conservative batch size for Windows stability
        batch_size = 4 if self.device == "cuda" else 2
        if self.debug:
            print(f"DEBUG: Starting transcription with batch_size={batch_size}")
        
        whisper_result = self.model.transcribe(audio_path, batch_size=batch_size)
        if self.debug:
            print(f"DEBUG: Transcription completed - {len(whisper_result['segments'])} segments")

        if self.progress_callback: self.progress_callback(60, "Aligning & diarising...")

        # ── alignment to word-level ───────────────────────────────────
        if self.debug:
            print(f"DEBUG: Starting word-level alignment...")
        
        try:
            # Get alignment model metadata
            alignment_model, metadata = whisperx.load_align_model(language_code="en", device=self.device)
            if self.debug:
                print(f"DEBUG: Alignment model loaded successfully")
            
            whisper_result = whisperx.align(whisper_result["segments"],
                                            alignment_model, metadata,
                                            audio_path, self.device)
            if self.debug:
                print(f"DEBUG: Word alignment completed")
        except Exception as align_error:
            print(f"DEBUG: Word alignment failed: {align_error}")
            # Continue without word-level alignment
            if self.debug:
                print(f"DEBUG: Continuing without word-level alignment")
            pass

        # Skip diarization if no speaker names provided (for faster testing)
        if not speaker_names:
            if self.debug:
                print(f"DEBUG: No speaker names provided - skipping diarization")
            segments = []
            for seg in whisper_result["segments"]:
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"], 
                    "text": seg["text"],
                    "speaker": "Speaker"
                })
        else:
            if self.debug:
                print(f"DEBUG: Starting speaker diarization...")
                print(f"DEBUG: Running whisperx.diarize() - first run may download ~1.8GB models...")
            
            # Try different diarization methods in order of preference
            diarization_method = "none"
            try:
                # Method 1: Try custom fine-grained diarization for rapid speaker changes
                try:
                    from pyannote.audio import Pipeline
                    if self.debug:
                        print(f"DEBUG: Using custom fine-grained pyannote pipeline")
                    
                    # Load the pipeline and customize parameters for rapid speaker changes
                    diarize_model = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=self.hf_token
                    ).to(torch.device(self.device))
                    
                    # Configure for finer granularity - adjust VAD parameters
                    # These parameters make the system more sensitive to short utterances
                    diarize_model._segmentation.model.specifications.min_duration_on = 0.1    # minimum speech duration (default: 0.5s)
                    diarize_model._segmentation.model.specifications.min_duration_off = 0.1   # minimum silence duration (default: 0.5s)
                    
                    # Load audio for diarization
                    audio_for_diarization = whisperx.load_audio(audio_path)
                    
                    # Use min/max speakers if provided
                    if speaker_names and len(speaker_names) >= 2:
                        speaker_ts = diarize_model({"waveform": audio_for_diarization, "sample_rate": 16000}, 
                                                 min_speakers=len(speaker_names), max_speakers=len(speaker_names))
                    else:
                        speaker_ts = diarize_model({"waveform": audio_for_diarization, "sample_rate": 16000})
                    
                    # Convert pyannote output to DataFrame format
                    import pandas as pd
                    diarize_df = pd.DataFrame(speaker_ts.itertracks(yield_label=True), columns=['segment', 'label', 'speaker'])
                    diarize_df['start'] = diarize_df['segment'].apply(lambda x: x.start)
                    diarize_df['end'] = diarize_df['segment'].apply(lambda x: x.end)
                    speaker_ts = diarize_df
                    
                    diarization_method = "Custom Fine-Grained Pipeline"
                    if self.debug:
                        print(f"DEBUG: Fine-grained diarization created {len(speaker_ts)} segments")
                        print(f"DEBUG: Average segment length: {(speaker_ts['end'] - speaker_ts['start']).mean():.2f}s")
                    
                except Exception as fine_grained_error:
                    if self.debug:
                        print(f"DEBUG: Fine-grained diarization failed: {fine_grained_error}")
                    
                    # Method 2: Fallback to standard WhisperX DiarizationPipeline
                    try:
                        from whisperx.diarize import DiarizationPipeline
                        if self.debug:
                            print(f"DEBUG: Using whisperx.diarize.DiarizationPipeline")
                        diarize_model = DiarizationPipeline(
                            use_auth_token=self.hf_token,
                            device=self.device
                        )
                        # Use min/max speakers if provided
                        if speaker_names and len(speaker_names) >= 2:
                            speaker_ts = diarize_model(audio_path, min_speakers=len(speaker_names), max_speakers=len(speaker_names))
                        else:
                            speaker_ts = diarize_model(audio_path)
                        diarization_method = "WhisperX DiarizationPipeline"
                        if self.debug:
                            print(f"DEBUG: Standard diarization created {len(speaker_ts)} segments")
                        
                    except ImportError:
                        # Method 3: Final fallback to manual pyannote pipeline
                        if self.debug:
                            print(f"DEBUG: Using manual pyannote pipeline fallback")
                        from pyannote.audio import Pipeline
                        diarize_model = Pipeline.from_pretrained(
                            "pyannote/speaker-diarization-3.1",
                            use_auth_token=self.hf_token
                        ).to(torch.device(self.device))
                        
                        # Load audio for diarization
                        audio_for_diarization = whisperx.load_audio(audio_path)
                        speaker_ts = diarize_model({"waveform": audio_for_diarization, "sample_rate": 16000})
                        diarization_method = "Manual pyannote Pipeline"
                    
            except Exception as diarize_error:
                if self.debug:
                    print(f"DEBUG: Diarization failed: {diarize_error}")
                # Skip diarization and continue with generic Speaker labels
                speaker_ts = None
                diarization_method = "none (failed)"
            
            if self.debug:
                print(f"DEBUG: Speaker diarization completed")

            # ── merge word-timestamps + diarisation ───────────────────────
            if self.debug:
                print(f"DEBUG: Merging transcription with speaker labels...")
            
            if speaker_ts is not None:
                try:
                    transcript_with_speakers = whisperx.assign_word_speakers(
                        diarize_df=speaker_ts,
                        transcript_result=whisper_result
                    )
                    # assign_word_speakers returns the full transcript result, extract segments
                    final_segments = transcript_with_speakers["segments"]
                    
                    # Post-process to split long segments with rapid speaker changes
                    if self.debug:
                        print(f"DEBUG: Post-processing long segments for rapid speaker changes")
                    
                    # Split segments longer than 30 seconds that likely contain multiple speakers
                    processed_segments = []
                    for seg in final_segments:
                        segment_duration = seg["end"] - seg["start"]
                        if segment_duration > 30.0:  # Long segment likely contains multiple speakers
                            if self.debug:
                                print(f"DEBUG: Splitting long segment ({segment_duration:.1f}s)")
                            
                            # Simple heuristic: split at natural pause indicators in text
                            text = seg.get("text", "")
                            split_indicators = ["? ", ". ", "! ", " really? ", " what? ", " no ", " yeah ", " okay "]
                            
                            # Find potential split points
                            split_points = []
                            for indicator in split_indicators:
                                pos = text.find(indicator)
                                while pos != -1:
                                    split_points.append(pos + len(indicator))
                                    pos = text.find(indicator, pos + 1)
                            
                            split_points = sorted(set(split_points))
                            
                            if len(split_points) > 2:  # Only split if we have multiple potential points
                                # Create sub-segments
                                prev_pos = 0
                                current_speaker_index = 0
                                speakers_to_use = speaker_names if speaker_names and len(speaker_names) >= 2 else [seg["speaker"], "Speaker_B"]
                                
                                for i, split_pos in enumerate(split_points[::2]):  # Take every other split point
                                    if i > 3:  # Limit to avoid too many tiny segments
                                        break
                                    
                                    sub_text = text[prev_pos:split_pos].strip()
                                    if len(sub_text) > 10:  # Only create segment if substantial text
                                        sub_duration = segment_duration * (split_pos - prev_pos) / len(text)
                                        sub_start = seg["start"] + (segment_duration * prev_pos / len(text))
                                        sub_end = min(seg["end"], sub_start + sub_duration)
                                        
                                        processed_segments.append({
                                            "start": sub_start,
                                            "end": sub_end,
                                            "text": sub_text,
                                            "speaker": speakers_to_use[current_speaker_index % len(speakers_to_use)]
                                        })
                                        
                                        prev_pos = split_pos
                                        current_speaker_index += 1
                                
                                # Add remaining text as final segment
                                if prev_pos < len(text):
                                    remaining_text = text[prev_pos:].strip()
                                    if len(remaining_text) > 10:
                                        processed_segments.append({
                                            "start": seg["start"] + (segment_duration * prev_pos / len(text)),
                                            "end": seg["end"],
                                            "text": remaining_text,
                                            "speaker": speakers_to_use[current_speaker_index % len(speakers_to_use)]
                                        })
                            else:
                                processed_segments.append(seg)
                        else:
                            processed_segments.append(seg)
                    
                    final_segments = processed_segments
                    
                    # Map generic speaker labels to provided names
                    if speaker_names and len(speaker_names) >= 2:
                        if self.debug:
                            print(f"DEBUG: Mapping speakers to provided names: {speaker_names}")
                        
                        # Create speaker mapping based on first appearance
                        speaker_mapping = {}
                        speaker_index = 0
                        
                        for seg in final_segments:
                            if "speaker" in seg and seg["speaker"] not in speaker_mapping:
                                if speaker_index < len(speaker_names):
                                    speaker_mapping[seg["speaker"]] = speaker_names[speaker_index]
                                    speaker_index += 1
                                else:
                                    speaker_mapping[seg["speaker"]] = f"Speaker_{speaker_index + 1}"
                                    speaker_index += 1
                        
                        # Apply the mapping
                        for seg in final_segments:
                            if "speaker" in seg and seg["speaker"] in speaker_mapping:
                                seg["speaker"] = speaker_mapping[seg["speaker"]]
                                
                        if self.debug:
                            print(f"DEBUG: Speaker mapping applied: {speaker_mapping}")
                            print(f"DEBUG: Post-processing created {len(final_segments)} total segments")
                    
                except Exception as assign_error:
                    if self.debug:
                        print(f"DEBUG: assign_word_speakers failed: {assign_error}")
                    # Fall back to no diarization
                    final_segments = whisper_result["segments"]
            else:
                # No diarization, use generic speaker labels
                final_segments = whisper_result["segments"]

            # Re-shape to match your old OutputFormatter expectations
            if self.debug:
                print(f"DEBUG: final_segments type: {type(final_segments)}")
                print(f"DEBUG: final_segments content: {final_segments}")
            
            segments = []
            for seg in final_segments:
                segments.append({
                    "start": seg["start"],
                    "end"  : seg["end"],
                    "text" : seg["text"],
                    "speaker": seg.get("speaker", "Speaker")
                })

            # Optional: replace generic IDs with user-provided names
            if speaker_names:
                if self.debug:
                    print(f"DEBUG: Mapping speakers to provided names...")
                mapping = { f"SPEAKER_{i:02d}": name
                            for i, name in enumerate(speaker_names) }
                for s in segments:
                    s["speaker"] = mapping.get(s["speaker"], s["speaker"])

        if self.progress_callback: self.progress_callback(90, "Formatting output...")
        if self.debug:
            print(f"DEBUG: WhisperX processing completed - {len(segments)} final segments")
        return segments, diarization_method
