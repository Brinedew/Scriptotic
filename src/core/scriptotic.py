#!/usr/bin/env python3
"""
YouTube URL-to-Transcript Tool (Simplified Version)
Works without speaker diarization - can be added later
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import argparse
from datetime import timedelta
import tempfile
import queue
from pathlib import Path
import faulthandler, sys, threading, time
import os, sys, pathlib
if sys.platform == "win32":
    venv = pathlib.Path(__file__).resolve().parent.parent / "venv"
    for sub in ("nvidia/cudnn/bin", "nvidia/cublas/bin"):
        p = venv / "Lib" / "site-packages" / sub
        if p.exists():
            os.add_dll_directory(str(p))     # Python ≥3.8

faulthandler.enable()
# faulthandler.dump_traceback_later(30, repeat=True)   # disabled - causes timeouts during model downloads

try:
    from whisperx_engine import WhisperXEngine as TranscriptionEngine
except ImportError:
    from src.core.whisperx_engine import WhisperXEngine as TranscriptionEngine

# Token management
try:
    from config.token_manager import TokenManager
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from config.token_manager import TokenManager

# Core imports for WhisperX
try:
    import yt_dlp
    import whisperx
    import torch
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("\nPlease install required packages:")
    print("pip install yt-dlp whisperx torch")
    sys.exit(1)


class AudioDownloader:
    """Handles YouTube audio extraction using yt-dlp"""
    
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        
    def download(self, url, output_path=None):
        """Download audio from YouTube URL using subprocess to avoid hanging"""
        if not output_path:
            output_path = tempfile.mktemp(suffix='.webm')
            
        base_path = output_path.replace('.webm', '')
        
        try:
            # Use subprocess to avoid yt-dlp hanging issues on Windows
            import subprocess
            import json
            
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                '--format', 'bestaudio',
                '--output', base_path + '.%(ext)s', 
                '--print-json',
                '--quiet',
                url
            ]
            
            if self.progress_callback:
                self.progress_callback(20, "Downloading audio...")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise Exception(f"yt-dlp failed: {result.stderr}")
            
            # Parse info from JSON output
            info_lines = [line for line in result.stdout.strip().split('\n') if line.startswith('{')]
            if info_lines:
                info = json.loads(info_lines[-1])
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
            else:
                title = 'Unknown'
                duration = 0
                
            # Find the actual downloaded file
            for ext in ['.webm', '.m4a', '.mp4', '.opus']:
                actual_output = base_path + ext
                if os.path.exists(actual_output):
                    if self.progress_callback:
                        self.progress_callback(40, "Audio downloaded successfully")
                    return actual_output, title, duration
            
            raise Exception(f"Downloaded file not found at expected location: {base_path}.*")
            
        except Exception as e:
            raise Exception(f"Failed to download audio: {str(e)}")
    
    def _progress_hook(self, d):
        if d['status'] == 'downloading' and self.progress_callback:
            percent = d.get('_percent_str', '0%').replace('%', '')
            try:
                self.progress_callback(float(percent), "Downloading audio...")
            except:
                pass




class OutputFormatter:
    """Formats transcription output in various formats"""
    
    @staticmethod
    def to_text(segments, title=None, model=None, diarization_method=None):
        """Convert to readable text format"""
        output = []
        if title:
            output.append(f"# {title}")
        if model:
            output.append(f"Model: WhisperX {model}")
        if diarization_method and diarization_method != "none":
            output.append(f"Diarization: {diarization_method}")
        if title or model or diarization_method:
            output.append("")  # Add blank line
            
        current_speaker = None
        current_text = []
        
        for segment in segments:
            if segment['speaker'] != current_speaker:
                if current_text:
                    output.append(f"[{current_speaker}] {' '.join(current_text)}")
                current_speaker = segment['speaker']
                current_text = [segment['text']]
            else:
                current_text.append(segment['text'])
                
        if current_text:
            output.append(f"[{current_speaker}] {' '.join(current_text)}")
            
        return '\n\n'.join(output)
    
    @staticmethod
    def to_json(segments, title=None, duration=None, model=None, diarization_method=None):
        """Convert to JSON format"""
        data = {
            'video_title': title or 'Unknown',
            'duration': duration or 0,
            'model': f'WhisperX {model}' if model else 'Unknown',
            'diarization': diarization_method if diarization_method and diarization_method != "none" else None,
            'speakers': []
        }
        
        for segment in segments:
            data['speakers'].append({
                'speaker_id': segment['speaker'],
                'start_time': segment['start'],
                'end_time': segment['end'],
                'text': segment['text']
            })
            
        return json.dumps(data, indent=2)
    
    @staticmethod
    def to_srt(segments):
        """Convert to SRT subtitle format"""
        output = []
        
        for i, segment in enumerate(segments, 1):
            start = OutputFormatter._seconds_to_srt_time(segment['start'])
            end = OutputFormatter._seconds_to_srt_time(segment['end'])
            text = f"[{segment['speaker']}] {segment['text']}"
            
            output.append(f"{i}")
            output.append(f"{start} --> {end}")
            output.append(text)
            output.append("")
            
        return '\n'.join(output)
    
    @staticmethod
    def _seconds_to_srt_time(seconds):
        """Convert seconds to SRT time format"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = td.total_seconds() % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')


class TranscriptGUI:
    """Main GUI application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube to Transcript")
        self.root.geometry("800x600")
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Variables with default values for testing
        self.url_var = tk.StringVar(value="https://www.youtube.com/watch?v=htOvH12T7mU")
        self.speakers_var = tk.StringVar(value="Scott, Dwarkesh, Daniel")
        self.format_var = tk.StringVar(value='text')
        self.model_var = tk.StringVar(value='large')
        self.output_path_var = tk.StringVar(value='transcript.txt')
        
        # Progress tracking
        self.progress_queue = queue.Queue()
        self.processing = False
        
        self._setup_ui()
        self._center_window()
        
        # No need to initialize engine at startup with subprocess approach
        self.status_label.config(text="Ready - Select model and generate transcript")
        
    def _setup_ui(self):
        """Create GUI elements"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # URL input
        ttk.Label(main_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Speaker names  
        ttk.Label(main_frame, text="Speaker Names:").grid(row=1, column=0, sticky=tk.W, pady=5)
        speakers_entry = ttk.Entry(main_frame, textvariable=self.speakers_var, width=40)
        speakers_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(main_frame, text="(comma-separated, optional)").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # Model selection
        ttk.Label(main_frame, text="WhisperX Model:").grid(row=2, column=0, sticky=tk.W, pady=5)
        model_combo = ttk.Combobox(main_frame, textvariable=self.model_var, 
                                  values=['tiny', 'base', 'small', 'medium', 'large'], 
                                  state='readonly', width=20)
        model_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="(larger = better quality, slower)").grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # Output format
        ttk.Label(main_frame, text="Output Format:").grid(row=3, column=0, sticky=tk.W, pady=5)
        format_combo = ttk.Combobox(main_frame, textvariable=self.format_var, 
                                   values=['text', 'json', 'srt'], state='readonly', width=20)
        format_combo.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Output path
        ttk.Label(main_frame, text="Save Location:").grid(row=4, column=0, sticky=tk.W, pady=5)
        path_entry = ttk.Entry(main_frame, textvariable=self.output_path_var, width=40)
        path_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse", command=self._browse_output).grid(row=4, column=2, pady=5)
        
        # Generate button
        self.generate_btn = ttk.Button(main_frame, text="Generate Transcript", 
                                      command=self._generate_transcript)
        self.generate_btn.grid(row=5, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=7, column=0, columnspan=3, pady=5)
        
        # Results area
        ttk.Label(main_frame, text="Transcript:").grid(row=8, column=0, sticky=tk.W, pady=5)
        
        # Text area with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.result_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=80, height=20)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(8, weight=1)
        
    def _center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        
    def _browse_output(self):
        """Browse for output file location"""
        filename = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[
                ('Text files', '*.txt'),
                ('JSON files', '*.json'),
                ('SRT files', '*.srt'),
                ('All files', '*.*')
            ]
        )
        if filename:
            self.output_path_var.set(filename)
            
    def _generate_transcript(self):
        """Generate transcript in background thread"""
        if self.processing:
            return
            
        url = self.url_var.get().strip()
        if not url:
            # Show error in text area instead of popup
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, "ERROR: Please enter a YouTube URL")
            self.status_label.config(text="No URL provided")
            return
            
        self.processing = True
        self.generate_btn.config(state='disabled')
        self.result_text.delete(1.0, tk.END)
        
        # Start processing in background
        thread = threading.Thread(target=self._process_video, args=(url,))
        thread.daemon = True
        thread.start()
        
        # Start checking for updates
        self._check_progress()
        
    def _process_video(self, url):
        """Process video in background thread"""
        temp_audio = None
        
        try:
            # Ensure HuggingFace token is configured
            token_manager = TokenManager()
            token_manager.ensure_token()
            
            # Parse speaker names
            speaker_names = None
            if self.speakers_var.get().strip():
                speaker_names = [s.strip() for s in self.speakers_var.get().split(',')]
            
            # Download audio
            downloader = AudioDownloader(progress_callback=self._update_progress)
            temp_audio, title, duration = downloader.download(url)
            
            # Copy temp file to current directory to avoid Windows temp path issues
            import shutil
            local_audio = "downloaded_audio.webm"
            shutil.copy2(temp_audio, local_audio)
            temp_audio = local_audio
            
            # Use subprocess isolation to avoid process state pollution (like CLI)
            self._update_progress(60, "Starting transcription...")
            
            import subprocess
            import json
            
            model_size = self.model_var.get()
            # Get the project root directory (two levels up from src/core/)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            worker_path = os.path.join(project_root, 'transcribe_worker.py')
            
            cmd = [
                sys.executable, worker_path,
                temp_audio,
                '--model', model_size,
                '--hf-token', token_manager.get_token() or ""
            ]
            
            if speaker_names:
                cmd.extend(['--speakers', ','.join(speaker_names)])
            
            # Debug: Print command and working directory
            self._update_progress(70, f"Running command: {' '.join(cmd[:3])}...")
            
            # Run from project root directory to match command line behavior
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=project_root)
            
            if result.returncode != 0:
                # Include both stdout and stderr in error message for better debugging
                error_msg = f"Transcription subprocess failed (exit code {result.returncode}):\n"
                if result.stderr:
                    error_msg += f"STDERR:\n{result.stderr}\n"
                if result.stdout:
                    error_msg += f"STDOUT:\n{result.stdout}\n"
                raise Exception(error_msg)
            
            # Parse JSON result from subprocess output
            lines = result.stdout.strip().split('\n')
            json_line = None
            for line in lines:
                if line.startswith('{') and line.endswith('}'):
                    json_line = line
                    break
            
            if not json_line:
                raise Exception("No JSON output found in subprocess result")
                
            transcription_result = json.loads(json_line)
            
            if not transcription_result.get("success"):
                raise Exception(f"Transcription failed: {transcription_result.get('error', 'Unknown error')}")
            
            segments = transcription_result["segments"]
            model_used = transcription_result["model"]
            diarization_method = transcription_result.get("diarization_method", "unknown")
            
            # Format output
            format_type = self.format_var.get()
            if format_type == 'json':
                output = OutputFormatter.to_json(segments, title, duration, model_used, diarization_method)
            elif format_type == 'srt':
                output = OutputFormatter.to_srt(segments)
            else:
                output = OutputFormatter.to_text(segments, title, model_used, diarization_method)
            
            # Save to file
            output_path = self.output_path_var.get()
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output)
            
            # Update GUI
            self.progress_queue.put(('done', output))
            self._update_progress(100, f"Completed using {model_used} model - Saved to {output_path}")
            
        except Exception as e:
            self.progress_queue.put(('error', str(e)))
            
        finally:
            # Cleanup
            if temp_audio and os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except:
                    pass
            
            # Also cleanup the copied local file
            if os.path.exists("downloaded_audio.webm"):
                try:
                    os.remove("downloaded_audio.webm")
                except:
                    pass
                    
            self.processing = False
            
    def _update_progress(self, percent, message):
        """Update progress from background thread"""
        self.progress_queue.put(('progress', (percent, message)))
        
    def _check_progress(self):
        """Check for progress updates from background thread"""
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()
                
                if msg_type == 'progress':
                    percent, message = data
                    self.progress_var.set(percent)
                    self.status_label.config(text=message)
                    
                elif msg_type == 'done':
                    self.result_text.insert(1.0, data)
                    self.generate_btn.config(state='normal')
                    self.status_label.config(text="Transcript generated successfully!")
                    
                elif msg_type == 'error':
                    self.generate_btn.config(state='normal')
                    self.progress_var.set(0)
                    self.status_label.config(text="Error occurred")
                    # Show error in the text area instead of popup
                    error_text = f"ERROR: Failed to process video\n\n{data}\n\n"
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(1.0, error_text)
                    
        except queue.Empty:
            pass
            
        if self.processing or not self.progress_queue.empty():
            self.root.after(100, self._check_progress)
            
    def run(self):
        """Run the GUI"""
        self.root.mainloop()


def cli_main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description='YouTube URL to Transcript Tool')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--names', help='Comma-separated speaker names')
    parser.add_argument('--format', choices=['text', 'json', 'srt'], default='text',
                      help='Output format')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large'],
                      default='base', help='Whisper model size')
    
    args = parser.parse_args()
    
    # Ensure HuggingFace token is configured
    token_manager = TokenManager()
    token_manager.ensure_token()
    
    # Parse speaker names
    speaker_names = None
    if args.names:
        speaker_names = [s.strip() for s in args.names.split(',')]
    
    print("Downloading audio...")
    downloader = AudioDownloader()
    temp_audio, title, duration = downloader.download(args.url)
    print(f"Audio downloaded: {temp_audio}")
    
    # Copy temp file to current directory to avoid Windows temp path issues
    import shutil
    local_audio = "downloaded_audio.webm"
    shutil.copy2(temp_audio, local_audio)
    print(f"Audio copied to: {local_audio}")
    temp_audio = local_audio
    
    print("DEBUG: About to enter try block...")
    try:
        print("DEBUG: Inside try block...")
        print(f"Initializing WhisperX {args.model} model...")
        print(f"HF Token available: {bool(token_manager.get_token())}")
        print("DEBUG: Using subprocess isolation to avoid process state pollution...")
        
        # Use subprocess to run transcription in clean environment (Gemini's recommendation)
        import subprocess
        import json
        
        # Get the project root directory (two levels up from src/core/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        worker_path = os.path.join(project_root, 'transcribe_worker.py')
        
        cmd = [
            sys.executable, worker_path,
            temp_audio,
            '--model', args.model,
            '--hf-token', token_manager.get_token() or ""
        ]
        
        if speaker_names:
            cmd.extend(['--speakers', ','.join(speaker_names)])
        
        print(f"Running isolated transcription: {' '.join(cmd[:3])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=project_root)  # 30 min timeout
        
        if result.returncode != 0:
            # Include both stdout and stderr in error message for better debugging
            error_msg = f"Transcription subprocess failed (exit code {result.returncode}):\n"
            if result.stderr:
                error_msg += f"STDERR:\n{result.stderr}\n"
            if result.stdout:
                error_msg += f"STDOUT:\n{result.stdout}\n"
            raise Exception(error_msg)
        
        # Parse JSON result from subprocess output (JSON is at the end)
        try:
            # Find the JSON line (starts with '{' and ends with '}')
            lines = result.stdout.strip().split('\n')
            json_line = None
            for line in lines:
                if line.startswith('{') and line.endswith('}'):
                    json_line = line
                    break
            
            if not json_line:
                raise Exception("No JSON output found in subprocess result")
                
            transcription_result = json.loads(json_line)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse transcription result: {e}\nOutput: {result.stdout}")
        
        if not transcription_result.get("success"):
            raise Exception(f"Transcription failed: {transcription_result.get('error', 'Unknown error')}")
        
        segments = transcription_result["segments"]
        model_used = transcription_result["model"]
        diarization_method = transcription_result.get("diarization_method", "unknown")
        print(f"Transcription completed! Got {len(segments)} segments using {model_used} model")
        
        print("Formatting output...")
        if args.format == 'json':
            output = OutputFormatter.to_json(segments, title, duration, model_used, diarization_method)
        elif args.format == 'srt':
            output = OutputFormatter.to_srt(segments)
        else:
            output = OutputFormatter.to_text(segments, title, model_used, diarization_method)
        
        # Save or print
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Transcript saved to {args.output}")
        else:
            print("\n" + "="*50 + "\n")
            print(output)
            
    finally:
        # Cleanup
        if os.path.exists(temp_audio):
            os.remove(temp_audio)


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
            cli_main()
        else:
            app = TranscriptGUI()
            app.run()
    except Exception as e:
        # Show the error instead of dying silently
        import traceback
        traceback.print_exc()      # prints to console
        # For fatal errors, we can't avoid popup since GUI might not be initialized
        print(f"FATAL ERROR: {e}")
        sys.exit(1)