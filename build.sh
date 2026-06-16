#!/usr/bin/env bash
# exit on error
set -o errexit

# Build React UI frontend
echo "Building React frontend..."
npm --prefix frontend install
npm --prefix frontend run build

# Install backend Python requirements
echo "Installing Python dependencies..."
if command -v pip &> /dev/null; then
    pip install --upgrade pip
    pip install -r requirements.txt
elif command -v pip3 &> /dev/null; then
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
else
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
fi
