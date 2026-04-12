import os
import ollama
from dotenv import load_dotenv

load_dotenv()

def check_ollama_models():
    """Returns a list of available local models via Ollama."""
    try:
        models_data = ollama.list()
        # Newer ollama versions return an object with a 'models' attribute
        models = []
        if hasattr(models_data, 'models'):
            models = [m.model for m in models_data.models]
        else:
            # Older versions might return a list directly
            models = [m['name'] for m in models_data]
            
        # Filter out cloud templates for THIS project exclusively
        return [m for m in models if "cloud" not in m.lower()]
    except Exception as e:
        print(f"Error checking Ollama: {e}")
        return []

def get_available_apis():
    """Checks for API keys in environment variables."""
    apis = []
    if os.getenv("GROQ_API_KEY"):
        apis.append("groq")
    return apis

def has_local_models():
    """Checks if any local models are installed."""
    return len(check_ollama_models()) > 0

def has_global_api():
    """Checks if any API keys are configured."""
    return len(get_available_apis()) > 0