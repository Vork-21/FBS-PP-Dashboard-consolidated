#!/usr/bin/env python3
"""
Consolidated Payment Plan Analysis System - Startup Script
Version 3.0: Simplified and Streamlined

This script helps you get started quickly with the consolidated payment plan analysis system.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    """Print welcome header"""
    print("=" * 60)
    print("🚀 Payment Plan Analysis System v3.0")
    print("📊 Consolidated & Streamlined Edition")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        print("   Please upgrade Python and try again.")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_required_files():
    """Check if all required files exist"""
    required_files = [
        "fastapi_webapp.py",
        "enhanced_main.py",
        "enhanced_parsers.py",
        "enhanced_analyzers.py", 
        "enhanced_calculators.py",
        "enhanced_reporters.py",
        "models.py",
        "utils.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file_name in required_files:
        if not Path(file_name).exists():
            missing_files.append(file_name)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_name in missing_files:
            print(f"   - {file_name}")
        return False
    
    print("✅ All required files present")
    return True

def setup_virtual_environment():
    """Setup virtual environment if needed"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment")
            return False
    else:
        print("✅ Virtual environment exists")
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📥 Installing dependencies...")
    
    # Determine pip executable
    if platform.system() == "Windows":
        pip_exe = "venv\\Scripts\\pip"
        python_exe = "venv\\Scripts\\python"
    else:
        pip_exe = "venv/bin/pip"
        python_exe = "venv/bin/python"
    
    try:
        # Upgrade pip first
        subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install requirements
        subprocess.run([pip_exe, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("   Try running manually:")
        print(f"   {get_activation_command()}")
        print("   pip install -r requirements.txt")
        return False
    except FileNotFoundError:
        print("❌ Virtual environment not properly set up")
        return False

def get_activation_command():
    """Get the appropriate activation command for the platform"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def create_directories():
    """Create necessary directories"""
    dirs = ["uploads", "reports", "static", "templates", "logs"]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"📁 Created directory: {dir_name}")
    
    print("✅ All directories ready")

def run_quick_test():
    """Run a quick test to ensure everything works"""
    print("🧪 Running quick system test...")
    
    try:
        # Test imports
        sys.path.insert(0, '.')
        
        from utils import format_currency, whole_months
        from enhanced_main import PaymentPlanAnalysisSystem
        
        # Test basic functionality
        test_currency = format_currency(1234.56)
        test_months = whole_months(3.7)
        
        if test_currency and test_months == 4:
            print("✅ System test passed")
            return True
        else:
            print("❌ System test failed")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def start_application():
    """Start the FastAPI application"""
    print("\n🌐 Starting Payment Plan Analysis System...")
    print("📍 The application will be available at: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    # Determine python executable
    if platform.system() == "Windows":
        python_exe = "venv\\Scripts\\python"
        uvicorn_exe = "venv\\Scripts\\uvicorn"
    else:
        python_exe = "venv/bin/python"
        uvicorn_exe = "venv/bin/uvicorn"
    
    try:
        # Try to start with uvicorn first (preferred)
        if Path(uvicorn_exe).exists() or Path(uvicorn_exe + ".exe").exists():
            cmd = [uvicorn_exe, "fastapi_webapp:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        else:
            cmd = [python_exe, "fastapi_webapp.py"]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except FileNotFoundError:
        print("❌ Failed to start server")
        print("   Try running manually:")
        print(f"   {get_activation_command()}")
        print("   python fastapi_webapp.py")

def show_usage_instructions():
    """Show usage instructions"""
    print("\n📖 Quick Start Guide:")
    print("1. Open your browser and go to: http://localhost:8000")
    print("2. Upload your payment plan CSV file")
    print("3. Review the unified customer analysis")
    print("4. Use the new combined customer/projections view")
    print("5. Download reports as needed")
    print()
    print("📁 CSV File Requirements:")
    print("- Required columns: Type, Date, Num, FOB, Open Balance, Amount")
    print("- Customer names should be in the first unnamed columns")
    print("- Invoice rows should have Type = 'Invoice'")
    print("- Optional: Class column for filtering")
    print()
    print("🆕 New in v3.0:")
    print("- Consolidated customer and projections view")
    print("- Simplified codebase with utilities")
    print("- Reduced redundancy and improved performance")
    print("- Maintained all original functionality")
    print()

def show_cli_instructions():
    """Show command line usage"""
    print("💻 Command Line Usage:")
    print("python enhanced_main.py <csv_file> [output_dir] [class_filter]")
    print()
    print("Examples:")
    print("python enhanced_main.py payment_data.csv")
    print("python enhanced_main.py payment_data.csv ./reports")
    print("python enhanced_main.py payment_data.csv ./reports BR")
    print()

def main():
    """Main startup function"""
    print_header()
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_required_files():
        print("\n❌ Setup incomplete. Please ensure all files are present.")
        sys.exit(1)
    
    # Setup environment
    if not setup_virtual_environment():
        sys.exit(1)
    
    if not install_dependencies():
        sys.exit(1)
    
    create_directories()
    
    # Run quick test
    if not run_quick_test():
        print("\n⚠️  System test failed, but you can still try to run the application.")
    
    # Show instructions
    show_usage_instructions()
    show_cli_instructions()
    
    # Ask user what they want to do
    print("What would you like to do?")
    print("1. Start web application (recommended)")
    print("2. Run command line analysis")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        start_application()
    elif choice == "2":
        csv_file = input("Enter CSV file path: ").strip()
        if csv_file and Path(csv_file).exists():
            print(f"\nRunning analysis on: {csv_file}")
            try:
                if platform.system() == "Windows":
                    python_exe = "venv\\Scripts\\python"
                else:
                    python_exe = "venv/bin/python"
                
                subprocess.run([python_exe, "enhanced_main.py", csv_file])
            except Exception as e:
                print(f"❌ Error running analysis: {e}")
        else:
            print("❌ Invalid file path")
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()