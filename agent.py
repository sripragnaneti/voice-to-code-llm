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
        
        # Explicitly allow English and French
        if lang not in ["en", "fr"]:
            return f"❌ Unsupported language detected ({lang}). Please speak in English or French."
            
        return result["text"]

    def _chat(self, messages):
        """Unified chat call dispatcher."""
        if self.mode == "global" and hasattr(self, 'client'):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error using global API: {e}"
        else:
            try:
                response = ollama.chat(model=self.model_name, messages=messages, options={'temperature': 0})
                return response['message']['content']
            except Exception as e:
                return f"Error using local model: {e}"

    def get_intent_and_refine(self, prompt, history=[]):
        system_prompt = """
        You are 'Aura', a highly advanced Bilingual AI coding assistant fluent in English and French.
        You MUST detect the user's language and respond in the SAME language.
        
        FORMAT: return ONLY JSON: {"intent": "create_file|write_code|create_folder|summarize|chat|clarify", "filename": "...", "content": "..."}
        
        CRUCIAL RULE (TRANSCRIPTION ERROR DETECTION):
        If the prompt contains obvious phonetic transcription errors or lacks logical meaning (in English or French), DO NOT blindly generate code.
        Set "intent" to "clarify" and ask the user for confirmation in THEIR language.
        """
        messages = [{'role': 'system', 'content': system_prompt}]
        for msg in history:
            messages.append({'role': msg['role'], 'content': msg['content']})
        messages.append({'role': 'user', 'content': f"TASK: {prompt}"})

        content = self._chat(messages)
        content = re.sub(r'<\|.*?\|>', '', content)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try: return json.loads(json_match.group())
            except: pass
        return {"intent": "chat", "filename": None, "content": content}

    def execute(self, transcription, output_dir, history=[]):
        intent_data = self.get_intent_and_refine(transcription, history)
        intent = intent_data.get('intent')
        filename = intent_data.get('filename')
        content = intent_data.get('content')

        file_data = None
        if intent == "create_file":
            name = filename if filename else "new_file.txt"
            res = create_file(output_dir, name, content if content else "")
            file_data = {"name": name, "content": content if content else ""}
        elif intent == "create_folder":
            name = filename if filename else "new_folder"
            res = create_folder(output_dir, name)
            file_data = None
        elif intent == "write_code":
            name = filename if filename else "code.py"
            res = write_code(output_dir, name, content)
            file_data = {"name": name, "content": content}
        elif intent == "summarize":
            res = self._chat([{'role': 'user', 'content': f"Summarize: {content}"}])
        elif intent == "clarify":
            res = content if content else "I didn't quite catch that. Could you clarify what you meant?"
        else:
            if content: res = content
            else:
                messages = history + [{'role': 'user', 'content': transcription}]
                res = self._chat(messages)

        return {"transcription": transcription, "intent": intent, "result": res, "file_data": file_data}
