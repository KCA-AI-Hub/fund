# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a civil complaint processing chatbot application (민원처리 챗봇) built for employees to handle civil complaints using a ChatGPT-style interface. The project consists of:
- A Python backend (currently minimal, using uv package manager)
- A frontend application in the `design/` directory with HTML/CSS/JavaScript
- ChatGPT-style dark theme UI with Korean language support

## Development Setup

### Python Environment
- **Package Manager**: uv (v0.8.14)
- **Python Version**: 3.13+ (specified in .python-version)
- **Virtual Environment**: .venv/ (managed by uv)

### Essential Commands

```bash
# Install dependencies
uv sync

# Run Python main script
uv run python main.py

# Add new dependencies
uv add [package-name]

# Serve the frontend locally (from design/ directory)
cd design
python -m http.server 8000
# or
npx http-server
```

## Project Structure

```
fund/
├── main.py             # Python entry point (currently minimal)
├── pyproject.toml      # Python project configuration
├── uv.lock            # Lock file for dependencies
└── design/            # Frontend application
    ├── index.html     # Main HTML file
    ├── styles.css     # ChatGPT-style CSS
    ├── script.js      # Chat session management
    ├── app.js         # Additional functionality
    └── test.html      # Test interface
```

## Frontend Architecture

The frontend (`design/` directory) is a standalone ChatGPT-style web application with:

### Key Components
1. **Chat Interface**: Three-column layout (sidebar | chat | answer panel)
   - Left sidebar: Chat history and new chat button
   - Main area: Real-time chat messages
   - Right panel: Answer generation and related regulations (toggleable)

2. **Session Management**: JavaScript class-based structure for managing chat sessions
   - Automatic session saving
   - Previous chat history retrieval
   - New chat creation

3. **User Input**: Multiple input methods
   - Direct text input with Enter to send
   - Predefined civil complaint example buttons
   - Shift+Enter for line breaks

### Design System
- **Color Scheme**: Dark theme matching ChatGPT
  - Background: #343541 (main), #202123 (sidebar)
  - Accent: #10a37f (green)
  - Text: #ececf1 (white), #8e8ea0 (gray)
- **Typography**: Noto Sans KR (Google Fonts)
- **Icons**: Font Awesome library
- **Responsive**: Mobile, tablet, and desktop layouts

## Development Notes

### Current State
- The Python backend is minimal (just a hello world in main.py)
- Frontend is a complete prototype with simulated responses
- No actual LLM integration yet (prepared structure exists)
- No database connection (TODO comments mark integration points)

### Future Integration Points
The code has prepared structures for:
- LLM API integration (see script.js for placeholder functions)
- Database connectivity for chat session persistence
- User authentication and authorization
- File upload functionality
- Multi-language support

### Korean Language Context
This application is designed for Korean civil service, with:
- Korean UI text and labels
- Civil complaint examples in Korean
- Response templates targeting Korean administrative language