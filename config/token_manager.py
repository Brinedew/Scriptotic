"""
HuggingFace Token Management System
Handles secure storage and retrieval of HuggingFace tokens
"""

import os
import json
import sys
from pathlib import Path

class TokenManager:
    def __init__(self):
        # Store config in user's home directory, not in project
        self.config_dir = Path.home() / ".scriptotic"
        self.config_file = self.config_dir / "config.json"
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
    def get_token(self):
        """Get HuggingFace token from environment or config file"""
        # First check environment variable
        token = os.getenv("HUGGINGFACE_TOKEN")
        if token:
            return token
            
        # Then check config file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get("huggingface_token")
            except (json.JSONDecodeError, FileNotFoundError):
                pass
                
        return None
    
    def set_token(self, token):
        """Store HuggingFace token in config file"""
        config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        config["huggingface_token"] = token
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Set environment variable for current session
        os.environ["HUGGINGFACE_TOKEN"] = token
        
    def is_token_configured(self):
        """Check if token is available from any source"""
        return self.get_token() is not None
        
    def prompt_for_token(self):
        """Interactive prompt to get token from user"""
        print("\n" + "="*60)
        print("HUGGINGFACE TOKEN SETUP REQUIRED")
        print("="*60)
        print("\nScriptotic needs a HuggingFace token for speaker diarization.")
        print("This is a one-time setup that will be remembered.")
        print("\nTo get your token:")
        print("1. Go to https://huggingface.co/settings/tokens")
        print("2. Create a new token with 'Read' permissions")
        print("3. Accept the license agreements for these models:")
        print("   - https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("   - https://huggingface.co/pyannote/segmentation-3.0")
        print("   - https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb")
        print("   - https://huggingface.co/microsoft/speecht5_vc")
        print("   - https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM")
        print("\n" + "="*60)
        
        while True:
            token = input("\nEnter your HuggingFace token: ").strip()
            if token:
                # Basic validation - HF tokens start with 'hf_'
                if not token.startswith('hf_'):
                    print("⚠️  Warning: HuggingFace tokens typically start with 'hf_'")
                    if input("Continue anyway? (y/n): ").lower() != 'y':
                        continue
                        
                self.set_token(token)
                print("✅ Token saved successfully!")
                print(f"Config stored in: {self.config_file}")
                return token
            else:
                print("❌ Token cannot be empty. Please try again.")
                
    def ensure_token(self):
        """Ensure token is available, prompt if not"""
        if not self.is_token_configured():
            return self.prompt_for_token()
        return self.get_token()