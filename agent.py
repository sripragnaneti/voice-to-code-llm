import whisper
import ollama
import json
import re
import os
import multiprocessing
from groq import Groq
from openai import OpenAI
from tools import create_file, write_code, create_folder
from prompts import ORCHESTRATOR_PROMPT, PYTHON_PROMPT, C_PROMPT, JAVA_PROMPT, GENERAL_PROMPT
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
            
            # 🚀 PROACTIVE LOADING: Pre-download/load Whisper tiny model to background
            import threading
            threading.Thread(target=lambda: self.stt_model, daemon=True).start()

    @property
    def stt_model(self):
        if self._stt_model is None:
            # 'tiny.en' is roughly 2x faster than 'base' with similar performance for English
            self._stt_model = whisper.load_model("tiny.en")
        return self._stt_model

    def transcribe(self, audio_path):
        # Allow Whisper to output text even if it misidentifies the language 
        # (e.g. noisy audio or speech with strong accents)
        result = self.stt_model.transcribe(audio_path)
        text = result.get("text", "").strip()
        lang = result.get("language", "en")
        
        if not text:
            return "LANG_ERR: No speech detected. Please speak again."
            
        # Soft Guard: Allow the text through but notify the system of a low-confidence match
        if lang != "en":
            return f"LANG_WARN: {text}"
            
        return text

    def _chat(self, messages):
        """Unified chat call dispatcher."""
        if self.mode == "global" and hasattr(self, 'client'):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0
                )
                if response and response.choices:
                    return response.choices[0].message.content
                return "Error: No response from global API."
            except Exception as e:
                return f"Error using global API: {e}"
        else:
            try:
                # 🚀 FAST-STABLE PERFORMANCE
                options = {
                    'temperature': 0,
                    'num_ctx': 2048,      
                    'num_thread': 6,       
                    'num_predict': 1536   # Increased back to prevent cutoff in code
                }
                response = ollama.chat(model=self.model_name, messages=messages, options=options)
                return response['message']['content']
            except Exception as e:
                return f"Error using local model: {e}"
    def get_intent_and_refine(self, prompt, history=[]):
        # ── FAST-TRACK SHORT-CIRCUIT ──
        # If the prompt is explicitly asking for a file/code in a supported language, skip Phase 1.
        lower_prompt = prompt.lower()
        meta = {"intent": "chat", "language": "none", "target_file": None}
        
        # ⚡ INSTANT-INTENT BYPASS (0ms Latency)
        # Bypasses Phase 1 Orchestrator for nearly all common dev commands
        code_keywords = ["create", "write", "make", "generate", "code", "script", "program", "build", "implement", "def", "function", "calculator", "sort", "merge", "print"]
        is_code_request = any(k in lower_prompt for k in code_keywords)
        
        # Super-Fast Language Map 
        if any(x in lower_prompt for x in ["python", ".py", "py program"]): meta["language"] = "python"
        elif any(x in lower_prompt for x in ["java", ".java", "jvm"]): meta["language"] = "java"
        elif any(x in lower_prompt for x in ["c code", " c ", "gcc", ".c", "c program", "calculator"]): meta["language"] = "c"
        
        if is_code_request and meta["language"] != "none":
            meta["intent"] = "create_file"
            name_match = re.search(r'([\w\-]+)\.(?:py|c|java)', prompt, re.IGNORECASE)
            meta["target_file"] = name_match.group(0) if name_match else None
            raw_meta = "SKIP_PHASE_1"
        else:
            # Only if heuristic fails do we call the first LLM (Slower)
            orchestrator_msgs = [
                {'role': 'system', 'content': ORCHESTRATOR_PROMPT},
                {'role': 'user', 'content': f"TASK: {prompt}\nHISTORY: {str(history[-1:])}"}
            ]
            raw_meta = self._chat(orchestrator_msgs)
            
            # ── UNIVERSAL OVERRIDE: Prioritize explicit keywords in the CURRENT prompt ──
            if "python" in lower_prompt: meta["language"] = "python"
            elif "java" in lower_prompt: meta["language"] = "java"
            elif "c " in lower_prompt or " c " in lower_prompt: meta["language"] = "c"

            # Robust Meta Parse
            json_match = re.search(r'\{.*\}', raw_meta, re.DOTALL)
            if json_match:
                try: 
                    incoming_meta = json.loads(json_match.group())
                    # Merge logic
                    if meta["language"] == "none":
                        meta["language"] = incoming_meta.get("language", "none")
                    meta["intent"] = incoming_meta.get("intent", "chat")
                    if not meta["target_file"]:
                        meta["target_file"] = incoming_meta.get("target_file")
                except: pass
            else:
                # Heuristic Meta Recovery (if Override didn't work)
                if meta["language"] == "none":
                    if "python" in raw_meta.lower(): meta["language"] = "python"
                    elif "java" in raw_meta.lower(): meta["language"] = "java"
                    elif "c " in raw_meta.lower() or " c " in raw_meta.lower(): meta["language"] = "c"
                
                for i in ["create_file", "write_code", "summarize", "clarify"]:
                    if i in raw_meta.lower(): meta["intent"] = i
        
        # ── SCRUB AND REFINE TARGET FILENAME ──
        if not meta.get("target_file"):
            ext = "py" if meta.get("language") == "python" else ("c" if meta.get("language") == "c" else ("java" if meta.get("language") == "java" else "txt"))
            guess_match = re.search(r'([\w\-]+)\.' + ext, prompt, re.IGNORECASE)
            if guess_match:
                meta["target_file"] = guess_match.group(0)
            else:
                meta["target_file"] = f"application.{ext}" if meta.get("language") != "none" else "document.txt"

        intent = meta.get("intent", "chat")
        lang = meta.get("language", "none")

        # FAST EXIT: If intent is summarize or clarify or chat, don't do second phase here
        if intent not in ["create_file", "write_code"]:
            return {"intent": intent, "filename": meta.get("target_file"), "content": raw_meta}
        # Phase 2: Code Generation (if needed)
        # Pick the specialized prompt
        if lang in ["python", "c", "java"]:
            spec_prompt = PYTHON_PROMPT if lang == "python" else (C_PROMPT if lang == "c" else JAVA_PROMPT)
        else:
            from prompts import GENERAL_PROMPT
            spec_prompt = GENERAL_PROMPT
            
        gen_msgs = [
            {'role': 'system', 'content': spec_prompt},
            {'role': 'user', 'content': f"REQUEST: {prompt}\nCONTEXT: {str(history[-2:])}"}
        ]
        # Generate ONLY RAW content
        content = self._chat(gen_msgs)
        
        # Final Scrub for artifacts
        content = re.sub(r'<\|.*?\|>', '', content).strip()
        content = re.sub(r'```(?:\w+\n)?(.*?)```', r'\1', content, flags=re.DOTALL)
        
        # Determine filename
        filename = meta.get("target_file")
        if lang == "java":
            # 🚀 ENHANCED JAVA NAMING: Search for the class with the main method first
            main_class_match = re.search(r'public\s+class\s+(\w+).*?public\s+static\s+void\s+main', content, re.DOTALL)
            if main_class_match:
                filename = main_class_match.group(1) + ".java"
            else:
                # Fallback to the first public class
                class_match = re.search(r'public\s+class\s+(\w+)', content)
                if class_match:
                    filename = class_match.group(1) + ".java"

        if not filename or filename == "none":
            # Fallback filename logic
            ext = "py" if lang == "python" else ("c" if lang == "c" else ("java" if lang == "java" else "txt"))
            # Try to extract a name or guess
            name_match = re.search(r'(\w+)\.' + ext, prompt, re.IGNORECASE)
            filename = name_match.group(0) if name_match else f"document.{ext}"

        data = {"intent": intent, "filename": filename, "content": content.strip()}
            
        # ── THE SCRUBBER: Only applies to CHAT/SUMMARIZE/CLARIFY ──
        # This prevents breaking Java/C braces in created files.
        if intent not in ["create_file", "write_code"]:
            if isinstance(data.get('content'), str):
                c = data['content'].strip()
                if c.startswith('{') and c.endswith('}') and ('"content"' in c or '"intent"' in c):
                    c = c.strip('{').strip('}')
                    c = re.sub(r'^["\']?(?:intent|filename|content)["\']?:\s*["\']?.*?["\']?,?\s*', '', c, flags=re.IGNORECASE | re.MULTILINE)
                    c = re.sub(r'^["\']?(?:intent|filename|content)["\']?:\s*["\']?.*?["\']?,?\s*', '', c, flags=re.IGNORECASE | re.MULTILINE)
                    c = c.strip().strip('"').strip("'").strip()
                data['content'] = c
                    
        return data

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
            res = f"Created: {os.path.join(output_dir, name)}"
        elif intent == "create_folder":
            name = filename if filename else "new_folder"
            res = create_folder(output_dir, name)
            file_data = None
        elif intent == "write_code":
            name = filename if filename else "code.py"
            res = write_code(output_dir, name, content)
            file_data = {"name": name, "content": content}
            res = f"Updated: {os.path.join(output_dir, name)}"
        elif intent == "summarize":
            if content and "SKIP_PHASE_1" not in content and len(content) > 50:
                # If content already contains the summary from Phase 1, use it
                res = content
            else:
                res = self._chat([{'role': 'user', 'content': f"Summarize this concisely: {transcription}"}])
        elif intent == "clarify":
            if content and "SKIP_PHASE_1" not in content and len(content) > 20:
                res = content
            else:
                res = "I'm sorry, I couldn't quite understand that command. It seems like there might have been a transcription error. Could you please rephrase or clarify?"
        else:
            if content and "SKIP_PHASE_1" not in content: 
                res = content
            else:
                messages = history + [{'role': 'user', 'content': transcription}]
                res = self._chat(messages)

        return {"transcription": transcription, "intent": intent, "result": res, "file_data": file_data}
