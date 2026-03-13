#!/usr/bin/env python3
import subprocess
import sys
import os

# Start uvicorn server in foreground
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("Starting server...")
print("Open http://localhost:8000 in your browser")
print("Press Ctrl+C to stop\n")

# Run uvicorn
try:
    subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
except KeyboardInterrupt:
    print("\nServer stopped")
except Exception as e:
    print(f"Error: {e}")