#!/usr/bin/env python3
"""
Simple script to start the financial model API backend
Run this before starting your React app
"""

import subprocess
import sys
import os

def main():
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    
    print("🚀 Starting Renewable Energy Financial Model API...")
    print(f"📁 Backend directory: {backend_dir}")
    
    try:
        # Start the FastAPI server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "financial_model_api:app", 
            "--host", "0.0.0.0", 
            "--port", "8001", 
            "--reload"
        ], cwd=backend_dir)
    except KeyboardInterrupt:
        print("\n👋 Shutting down API server...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
