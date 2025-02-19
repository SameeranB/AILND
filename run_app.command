#!/bin/zsh

# Get the directory where this script is located
SCRIPT_DIR="${0:A:h}"

# Change to the application directory
cd "$SCRIPT_DIR"

# Check if .env file exists, if not create it from template
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        echo "Creating .env file from template..."
        cp .env.template .env
        echo "Please edit .env file and add your OpenAI API key before running the application again."
        read -n 1 -s -r -p "Press any key to close the window..."
        exit 1
    else
        echo "Error: .env.template file not found!"
        read -n 1 -s -r -p "Press any key to close the window..."
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    # Activate virtual environment
    source .venv/bin/activate
fi

# Ensure storage directories exist
mkdir -p data storage

# Run the application
echo "Starting the application..."
streamlit run main.py

# Keep the terminal window open if there's an error
read -n 1 -s -r -p "Press any key to close the window..." 