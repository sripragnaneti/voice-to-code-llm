import streamlit as st
import os, shutil, re, json, time
from agent import LocalAIAgent
from tools import list_files
from config_utils import get_available_apis, check_ollama_models, has_local_models

# --- Page Config ---
st.set_page_config(page_title="Aura — AI Agent", page_icon="🎙️", layout="wide")

# Fix for ffmpeg
if not shutil.which("ffmpeg"):
    wf = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe")
    if os.path.exists(wf): os.environ["PATH"] += os.pathsep + os.path.dirname(wf)

# ── Minimal Custom CSS (only for elements Streamlit doesn't theme) ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .aura-title {
        font-size: 3rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    .aura-subtitle {
        font-size: 1.1rem;
        color: #94a3b8;
        margin-bottom: 2.5rem;
        font-weight: 400;
    }
    .label-text {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 8px;
    }
    .chat-user {
        background: linear-gradient(135deg, #7c3aed, #6d28d9);
        color: #ffffff;
        padding: 12px 20px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        margin-left: 20%;
        text-align: right;
        font-size: 1rem;
        line-height: 1.6;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.2);
    }
    .chat-bot {
        background-color: #1a1a3e;
        color: #e2e8f0;
        padding: 12px 20px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        margin-right: 20%;
        border: 1px solid #2d2d5e;
        font-size: 1rem;
        line-height: 1.6;
    }
    .empty-state {
        text-align: center;
        color: #475569;
        padding: 6rem 2rem;
        font-size: 1rem;
    }
    .block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────
# PERSISTENCE & STATE
# ──────────────────────────
CHATS_FILE = ".aura_chats.json"

def load_chats():
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return {"General": []}

def save_chats(threads):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(threads, f, indent=2)

if 'setup_complete' not in st.session_state: st.session_state.setup_complete = False
if 'model_name' not in st.session_state: st.session_state.model_name = ""
if 'mode' not in st.session_state: st.session_state.mode = "local"
if 'base_output_dir' not in st.session_state: st.session_state.base_output_dir = os.pat
# WIP Threads