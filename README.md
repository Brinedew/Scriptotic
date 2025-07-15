# Scriptotic

**Turn YouTube videos into text transcripts with speaker identification**

Scriptotic is a Windows tool that downloads YouTube videos, extracts the audio, and creates accurate text transcripts with speaker diarization (identifying who said what). It uses OpenAI's Whisper model for transcription and advanced AI for speaker identification.

## Features

- **YouTube Video Download**: Automatically downloads audio from YouTube videos
- **High-Quality Transcription**: Uses WhisperX (enhanced Whisper) for accurate transcription
- **Speaker Identification**: Identifies different speakers and labels their dialogue
- **Multiple Model Sizes**: Choose from tiny to large models (larger = better quality, slower)
- **GUI & Command Line**: Easy-to-use graphical interface or command line for automation
- **Windows Optimized**: Built specifically for Windows with CUDA GPU acceleration

## What You Need

### System Requirements
- **Windows 10 or 11** (64-bit)
- **NVIDIA GPU** (RTX 20-series or newer recommended for best performance)
- **12GB+ RAM** (16GB+ recommended for large models)
- **10GB+ free disk space** (for models and temporary files)

### Accounts You'll Need
- **HuggingFace Account**: Free account at [huggingface.co](https://huggingface.co) for AI models
- **YouTube**: Any YouTube video you want to transcribe

## Installation Guide

### Step 1: Install Python (if not already installed)

1. Go to [python.org](https://www.python.org/downloads/)
2. Download **Python 3.8** or newer
3. During installation, **IMPORTANT: Check "Add Python to PATH"**
4. Restart your computer after installation

### Step 2: Install CUDA (for GPU acceleration)

1. Go to [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-downloads)
2. Download and install **CUDA Toolkit 12.4** or newer
3. Restart your computer after installation

### Step 3: Download Scriptotic

**Option A: Download ZIP (Easiest)**
1. Click the green "Code" button above
2. Select "Download ZIP"
3. Extract the ZIP file to your desired location (e.g., `C:\Scriptotic`)

**Option B: Git Clone (If you have Git)**
```bash
git clone https://github.com/brinedew/Scriptotic.git
```

### Step 4: Run Scriptotic

**That's it! Just double-click `run-transcriber.bat`**

The first time you run it, it will automatically:
- Set up the Python environment
- Download and install all required AI models
- Configure everything for you

This takes about 5-10 minutes the first time, then it's instant after that.

### Step 5: Set Up HuggingFace Token (First Run Only)

1. Go to [huggingface.co](https://huggingface.co) and create a free account
2. Go to [Settings → Access Tokens](https://huggingface.co/settings/tokens)
3. Click "New token" and create a token with **Read** permissions
4. **Accept the license agreements** for these AI models (click each link and accept):
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
   - [speechbrain/spkrec-ecapa-voxceleb](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)
   - [microsoft/speecht5_vc](https://huggingface.co/microsoft/speecht5_vc)
   - [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM)
5. **Save your token** - you'll need it when you first run Scriptotic

## How to Use

### Basic Usage (Recommended)

1. **Double-click `run-transcriber.bat`** to launch the GUI
2. **First time**: You'll be prompted to enter your HuggingFace token
3. Enter the YouTube video URL
4. Enter speaker names (comma-separated, e.g., "Alice, Bob, Charlie")
5. Choose model size (larger = better quality, slower):
   - **tiny**: Fastest, lowest quality (~2 minutes for 1-hour video)
   - **base**: Good balance of speed and quality (~5 minutes for 1-hour video)
   - **small**: Better quality, slower (~10 minutes for 1-hour video)
   - **medium**: High quality, much slower (~20 minutes for 1-hour video)
   - **large**: Best quality, very slow (~30+ minutes for 1-hour video)
6. Click "Generate Transcript"
7. Wait for processing
8. Transcript will be saved to the specified file

### Command Line Usage

You can also use Scriptotic from the command line:

```bash
# Basic usage (launches GUI)
run-transcriber.bat

# Direct CLI usage
run-transcriber.bat "https://www.youtube.com/watch?v=VIDEO_ID" --names "Alice,Bob,Charlie" --output "transcript.txt"

# With specific model
run-transcriber.bat "https://www.youtube.com/watch?v=VIDEO_ID" --model large --output "transcript.txt"
```

## Output Format

The transcript will include:
- **Video title and metadata**
- **Model information** (which AI model was used)
- **Speaker-labeled dialogue**:
  ```
  [Alice] Hello everyone, welcome to today's discussion.
  [Bob] Thanks for having me, Alice. I'm excited to talk about this topic.
  [Alice] Let's start with the basics...
  ```

## Troubleshooting

### Common Issues

**"Double-clicking run-transcriber.bat does nothing"**
- Make sure Python is installed and "Add Python to PATH" was checked during installation
- Try running from Command Prompt to see error messages
- Make sure you extracted the ZIP file completely (don't run from inside the ZIP)

**"Python is not installed or not in PATH"**
- Download Python from python.org
- During installation, check "Add Python to PATH"
- Restart your computer after installation

**"CUDA out of memory"**
- Use a smaller model (tiny, base, or small)
- Close other GPU-intensive applications
- Try restarting your computer

**"HuggingFace token invalid"**
- Make sure you accepted the license agreements for all required models
- Generate a new token with Read permissions
- The token should start with `hf_`

**Video download fails**
- Check that the YouTube URL is correct and publicly accessible
- Some videos may be region-locked or have download restrictions
- Try a different video to test

**Very slow transcription**
- This is normal for longer videos and larger models
- The "large" model can take 30+ minutes for a 1-hour video
- Consider using "base" or "small" models for faster results

**Setup takes a long time**
- The first-time setup downloads several GB of AI models
- This is normal and only happens once
- Make sure you have a stable internet connection

### Getting Help

If you encounter issues:
1. Check the error message in the GUI text area or command prompt
2. Make sure all installation steps were completed
3. Try with a shorter video and smaller model first
4. Check that your GPU drivers are up to date

## Technical Details

### What's Happening Under the Hood

1. **Audio Download**: yt-dlp downloads the audio from YouTube
2. **Transcription**: WhisperX transcribes the audio to text
3. **Speaker Diarization**: PyAnnote identifies different speakers
4. **Alignment**: The system aligns the transcript with speaker timings
5. **Output**: Generates a formatted transcript with speaker labels

### Model Information

- **Transcription**: Uses OpenAI Whisper models via WhisperX
- **Speaker ID**: Uses pyannote.audio neural networks
- **Processing**: Runs on your local GPU for privacy and performance

### Privacy

- **All processing is local** - no audio or transcripts are sent to external servers
- Only model downloads require internet connection
- Your HuggingFace token is stored locally in `~/.scriptotic/config.json`

## Version Information

- **Current Version**: 0.1.0
- **Status**: Core functionality working, diarization accuracy improvements planned for v0.2
- **Known Issues**: Speaker diarization may struggle with very rapid speaker changes

## License

This project is open source. See individual model licenses for AI models used.

## Contributing

Found a bug or want to improve Scriptotic? Please open an issue or submit a pull request!

---

**Made with ❤️ by [brinedew](https://github.com/brinedew)**