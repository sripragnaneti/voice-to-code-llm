import whisper
import ollama
import json
import re
import os
from groq import Groq
from openai import OpenAI
from tools import create_file, write_code, create_folder
from dotenv import load_dotenv

load_dotenv()

class LocalAIAgent:
    def __init__(self, mode="local", model_name=None):
        """Initialize agent with specified mode."""
        self.mode = mode
        self.model_name = model_name
        self._stt_model = None
        
        if self.mode == "global":
            self.client = None
            if os.getenv("GROQ_API_KEY"):
                self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                self.provider = "groq"
                if not self.model_name or self.model_name == "groq":
                    self.model_name = "llama-3.3-70b-versatile"
            elif os.getenv("OPENAI_API_KEY"):
                self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.provider = "openai"
                if not self.model_name or self.model_name == "openai":
                    self.model_name = "gpt-4o"
        else:
            self.provider = "ollama"
            if not self.model_name:
                try:
                    m_list = ollama.list()
                    models = getattr(m_list, 'models', [])
                    self.model_name = models[0].model if models else "llama3"
                except:
                    self.model_name = "llama3"

    @property
    def stt_model(self):
        if self._stt_model is None:
            self._stt_model = whisper.load_model("base")
        return self._stt_model

    def transcribe(self, audio_path):
        result = self.stt_model.transcribe(audio_path)
        lang = result.get("language", "en")
        
        if lang != "en":
            return f"❌ Non-English audio detected ({lang}). Please speak in English, as phonetic sound-mapping has been disabled."
            
        return result["text"]

    