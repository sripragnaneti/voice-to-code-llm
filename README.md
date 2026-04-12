# Aura: Voice-Controlled Local AI Agent

Aura is a sophisticated local AI agent that processes voice commands to perform system tasks like file creation, code generation, and text summarization. 

## 🚀 Features
- **Voice Transcription**: Powered by OpenAI Whisper (running locally).
- **Intent Recognition**: Utilizes Local LLMs via Ollama to classify user intents into actionable tasks.
- **Secure File Operations**: All file manipulations are restricted to a dedicated `output/` directory.
- **Premium UI**: Built with Streamlit, featuring a modern, responsive design.

## 🛠️ Tech Stack
- **Frontend**: Streamlit
- **STT**: OpenAI Whisper
- **LLM**: Ollama (Llama 3 / Qwen)
- **Audio Handling**: SoudDevice & Scipy

## 📦 Setup Instructions

1. **Install Ollama** (if not already installed):
   Download from [ollama.com](https://ollama.com).

2. **Pull the required models**:
   ```bash
   ollama pull llama3
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

## 🏗️ Architecture
1. **Audio Input**: User uploads an audio file or records via microphone.
2. **STT (Whisper)**: Audio is transcribed into plain text.
3. **Intent Classifier (LLM)**: The transcription is sent to Ollama with a system prompt that forces a JSON response containing the `intent`, `filename`, and `content`.
4. **Tool Execution**: Based on the intent, Python functions handle file I/O or further text processing.
5. **Output**: The results are displayed back to the user in a clean, glassmorphic UI.

---
*Developed as part of the Voice AI Agent Assignment.*
