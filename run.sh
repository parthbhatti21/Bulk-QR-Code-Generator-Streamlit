#!/bin/bash

# QR Code Generator - Startup Script
# This script activates the virtual environment and runs the Flask app

source venv/bin/activate

# Check if dependencies are installed
pip install -q 'Flask==2.3.3' 'qrcode[pil]==7.4.2' 'gunicorn==21.2.0' 'python-dotenv==1.0.0' 2>/dev/null || true

# Run the app
python3 app.py
