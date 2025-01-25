#!/bin/bash
# Activate the gemini-env environment
source /Users/1kf/anaconda3/bin/activate gemini-env

# Get the directory of the .command file
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Change to the directory of the script
cd "$SCRIPT_DIR"

# Run the Python script in the same directory
python "$SCRIPT_DIR/AiVocNote.py"