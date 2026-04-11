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
        letter-
# WIP Sidebar