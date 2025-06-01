#!/usr/bin/env python3
"""
Simple startup script for the Payment Plan Analysis System
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    print("🚀 Starting Payment Plan Analysis System...")
    print("📊 Navigate to: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop")
    print()
    
    try:
        # Start the application
        subprocess.run([
            sys.executable, "streamlined_webapp.py"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Try running: python streamlined_webapp.py")

if __name__ == "__main__":
    main()