#!/usr/bin/env python3
"""
Fixed startup script for the Payment Plan Analysis System
Handles common setup issues and provides clear error messages
"""
import subprocess
import sys
import os
from pathlib import Path

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        "consolidated_analysis.py",
        "streamlined_webapp.py",
        "requirements.txt"
    ]
    
    required_dirs = [
        "static/css",
        "static/js", 
        "templates"
    ]
    
    missing_files = []
    missing_dirs = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_files or missing_dirs:
        print("❌ Missing required files/directories:")
        for file in missing_files:
            print(f"   📄 {file}")
        for dir_path in missing_dirs:
            print(f"   📁 {dir_path}/")
        print("\n📋 Please follow the setup guide to create these files.")
        return False
    
    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    try:
        import fastapi
        import uvicorn
        import pandas
        import numpy
        import openpyxl
        return True
    except ImportError as e:
        print(f"❌ Missing Python package: {e}")
        print("📦 Run: pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories if they don't exist"""
    dirs = ["uploads", "reports", "static/css", "static/js", "templates"]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created/verified directory: {dir_path}")

def main():
    print("🚀 Payment Plan Analysis System - Startup Check")
    print("=" * 50)
    
    # Check current directory
    current_dir = Path.cwd()
    print(f"📂 Current directory: {current_dir}")
    
    # Create directories
    create_directories()
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Setup incomplete. Please create missing files.")
        print("📖 Refer to the setup guide for complete instructions.")
        return
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependencies missing. Please install them first.")
        return
    
    print("\n✅ All requirements met!")
    print("🌐 Starting web server...")
    print("📊 Navigate to: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    try:
        # Try to import the consolidated analysis module
        try:
            from consolidated_analysis import PaymentPlanAnalysisEngine
            print("✅ Analysis engine loaded successfully")
        except ImportError as e:
            print(f"❌ Error importing analysis engine: {e}")
            print("📝 Check that consolidated_analysis.py is in the current directory")
            return
        
        # Start the application
        subprocess.run([
            sys.executable, "streamlined_webapp.py"
        ])
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except FileNotFoundError:
        print("❌ streamlined_webapp.py not found")
        print("📝 Make sure you're in the correct directory")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check that all files are in place")
        print("2. Verify Python dependencies are installed")
        print("3. Try running directly: python streamlined_webapp.py")

if __name__ == "__main__":
    main()