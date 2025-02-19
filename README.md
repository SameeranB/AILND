# Essential5 Learning Platform

A learning platform application for macOS.

## Requirements

- macOS
- Python 3.11 or later (you can install it from [python.org](https://www.python.org/downloads/))
- OpenAI API key (for AI-powered features)

## Setup

1. Copy the `.env.template` file to a new file named `.env`:
   ```bash
   cp .env.template .env
   ```
2. Open the `.env` file in a text editor and replace `your_openai_api_key_here` with your actual OpenAI API key.

## Running the Application

1. Double-click the `run_app.command` file
2. If you see a security warning, follow these steps:
   - Open System Preferences
   - Go to Security & Privacy
   - Click the "Open Anyway" button
3. The first time you run the application, it will:
   - Set up a Python virtual environment
   - Install required packages (this may take a few minutes)
   - Start the application
4. The application will open in your default web browser at http://localhost:8501

## Important Notes

- All your course data and progress will be saved automatically in the `data` directory
- To close the application, simply press any key in the terminal window
- Subsequent runs will be much faster as all packages are already installed
- Make sure your `.env` file is properly configured with your OpenAI API key

## Support

If you encounter any issues, please contact your system administrator or the development team. 