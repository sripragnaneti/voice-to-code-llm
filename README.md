# Aura: Voice-Controlled Local AI Agent

Aura is a sophisticated local AI agent that processes voice commands to perform system tasks like file creation, code generation, and text summarization. 

## Features
- **Voice Transcription**: Powered by OpenAI Whisper (running locally).
- **Intent Recognition**: Utilizes Local LLMs via Ollama to classify user intents into actionable tasks.
- **Secure File Operations**: All file manipulations are restricted to a dedicated `output/` directory.
- **Premium UI**: Built with Streamlit, featuring a modern, responsive design.

## Tech Stack
- **Frontend**: Streamlit
- **STT**: OpenAI Whisper (Local)
- **Local LLM**: Ollama (Llama 3.2 / Qwen 2.5)
- **API Fallback**: Groq (High-speed inference)
- **Audio Handling**: SoudDevice & Scipy

## Setup Instructions

**Run the Application**:
```bash
streamlit run app.py
```

## Hardware Efficiency and Hybrid Architecture

Aura is designed with a Local-First philosophy, prioritizing privacy and security by running Llama 3.2 and Whisper on the user's physical hardware. 

However, to ensure high performance across varying hardware specifications (including non-GPU systems), we have implemented a Latency-Aware Hybrid Fallback:
- **Baseline**: All tasks are processed locally via Ollama.
- **Efficiency Layer (Groq)**: The application features a real-time latency monitor. If a local model's inference time exceeds a user-defined threshold value (for example, 15 seconds), Aura offers a dynamic choice.
- **User Choice**: Upon reaching the threshold, the user is presented with a prompt to either manually switch to the Groq API for an instant high-speed response or continue waiting for the local model to finish processing for maximum privacy.
- **Reasoning**: This fallback fulfills the requirement for efficient operation on constrained hardware. It allows the agent to be highly usable on lower-end systems while keeping the user in full control of their data and processing speed.

## Architecture
1. **Audio Input**: User records commands via the specialized 3-column input grid (Code, Upload, or Summarize).
2. **STT (Whisper)**: Audio is transcribed locally into plain text.
3. **Intent Classifier (LLM)**: Transcription is sent to Ollama (or Groq during fallback) with a system prompt that enforces a JSON response.
4. **Latency Monitor**: A dedicated background thread monitors execution time and provides real-time UI feedback.
5. **Tool Execution**: Python modules handle file I/O or text summarization based on the detected intent.
6. **Output**: Results are displayed in a premium Streamlit interface.

---
*Developed as part of the specialized Voice AI Agent project.*
