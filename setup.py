#!/usr/bin/env python3

"""
Mural Development Setup Script
This script helps set up the development environment for Mural.
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Run a shell command and print status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("🎨 Mural Development Setup")
    print("=" * 30)
    
    # Check Python version
    print(f"🐍 Python version: {sys.version}")
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists('venv'):
        if not run_command('python -m venv venv', 'Creating virtual environment'):
            return False
    else:
        print("✅ Virtual environment already exists!")
    
    # Activate virtual environment and install dependencies
    if sys.platform == 'win32':
        activate_cmd = 'venv\\Scripts\\activate && pip install -r requirements.txt'
    else:
        activate_cmd = 'source venv/bin/activate && pip install -r requirements.txt'
    
    if not run_command(activate_cmd, 'Installing dependencies'):
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Activate the virtual environment:")
    if sys.platform == 'win32':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Run the application:")
    print("   python app.py")
    print("3. Open your browser to: http://localhost:5000")
    
    print("\n🔗 Useful commands:")
    print("- Run development server: python app.py")
    print("- Install new packages: pip install <package> && pip freeze > requirements.txt")
    print("- Deactivate virtual environment: deactivate")

if __name__ == '__main__':
    main()
