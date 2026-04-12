import streamlit as st
import os, shutil, re, json, time, threading
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
                data = json.load(f)
                # Migration logic for existing list-based threads
                for k, v in data.items():
                    if isinstance(v, list):
                        data[k] = {"messages": v, "model": "llama3.2"}
                return data
        except Exception: pass
    return {"General": {"messages": [], "model": "llama3.2"}}

def save_chats(threads):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(threads, f, indent=2)

if 'setup_complete' not in st.session_state: st.session_state.setup_complete = False
if 'mode' not in st.session_state: st.session_state.mode = "local"
if 'base_output_dir' not in st.session_state: st.session_state.base_output_dir = os.path.join(os.getcwd(), "output")
if 'run_trigger' not in st.session_state: st.session_state.run_trigger = False
if 'pending_text' not in st.session_state: st.session_state.pending_text = ""
if 'open_sidebar_file' not in st.session_state: st.session_state.open_sidebar_file = None
if 'last_audio_hash' not in st.session_state: st.session_state.last_audio_hash = None
if 'last_file_hash' not in st.session_state: st.session_state.last_file_hash = None
if 'last_doc_hash' not in st.session_state: st.session_state.last_doc_hash = None
if 'expander_pulse' not in st.session_state: st.session_state.expander_pulse = 0
if 'threads' not in st.session_state: st.session_state.threads = load_chats()
if 'active_thread' not in st.session_state:
    st.session_state.active_thread = list(st.session_state.threads.keys())[0] if st.session_state.threads else "General"
if 'available_apis' not in st.session_state: st.session_state.available_apis = get_available_apis()
if 'available_local_models' not in st.session_state: st.session_state.available_local_models = check_ollama_models()


# ═══════════════════════════════════════════════
# PHASE 1 — SETUP
# ═══════════════════════════════════════════════
if not st.session_state.setup_complete:
    # Centered layout for setup
    left_pad, center, right_pad = st.columns([1, 2, 1])

    with center:
        st.markdown("")
        st.markdown('<div class="aura-title">🎙️ Aura</div>', unsafe_allow_html=True)
        st.markdown('<div class="aura-subtitle">Trilingual Voice-to-Code Platform</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🖥️ Local Workbench")
        
        if st.session_state.available_local_models:
            sel_model = st.selectbox("Select Your Primary Local Engine", st.session_state.available_local_models)
        else:
            st.error("❌ Ollama not found. Please ensure Ollama is running.")
            if st.button("🔄 Refresh Local Models"):
                st.session_state.available_local_models = check_ollama_models()
                st.rerun()
            st.stop()
            
        st.markdown("---")
        
        with st.expander("⚙️ Advanced Workspace Optimization"):
            st.session_state.base_output_dir = st.text_input("Local Project Workspace", value=st.session_state.base_output_dir)
            # Latency fallback threshold
            if 'latency_threshold' not in st.session_state: st.session_state.latency_threshold = 15
            st.session_state.latency_threshold = st.slider("Latency Fallback Threshold (Seconds)", 5, 60, st.session_state.latency_threshold, help="Switch suggestion triggered after this time")

        if st.button("🚀 Launch Aura", use_container_width=True, type="primary"):
            st.session_state.threads[st.session_state.active_thread]['model'] = sel_model
            st.session_state.mode = "local" # Strictly local on launch
            st.session_state.output_dir = os.path.join(os.getcwd(), "output")
            st.session_state.setup_complete = True
            save_chats(st.session_state.threads)
            st.rerun()


# ═══════════════════════════════════════════════
# PHASE 2 — DASHBOARD
# ═══════════════════════════════════════════════
else:
    # Workplace Cache
    CACHE_DIR = ".audio_cache"
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Workspace Isolation Sync
    # Force lowercase and strip to prevent Windows path case-desync
    safe_thread = re.sub(r'[\\/*?:"<>|.]', "", st.session_state.active_thread).strip().lower()
    if not safe_thread: safe_thread = "default"
    st.session_state.output_dir = os.path.join(st.session_state.base_output_dir, safe_thread)
    os.makedirs(st.session_state.output_dir, exist_ok=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### 🎙️ Aura")
        mode_label = "🖥️ Local Model" if st.session_state.mode == "local" else "🌐 Global API"
        current_model = st.session_state.threads[st.session_state.active_thread].get('model', 'llama3.2')
        
        if st.session_state.mode == "local":
            avail = check_ollama_models()
            idx = avail.index(current_model) if current_model in avail else 0
            new_mod = st.selectbox(mode_label, avail, index=idx, label_visibility="collapsed")
            if new_mod and new_mod != current_model:
                st.session_state.threads[st.session_state.active_thread]['model'] = new_mod
                save_chats(st.session_state.threads)
                st.rerun()
        else:
            avail = [a.upper() for a in st.session_state.available_apis]
            idx = avail.index(current_model.upper()) if current_model.upper() in avail else 0
            new_mod = st.selectbox(mode_label, avail, index=idx, label_visibility="collapsed")
            if new_mod and new_mod.lower() != current_model:
                st.session_state.threads[st.session_state.active_thread]['model'] = new_mod.lower()
                save_chats(st.session_state.threads)
                st.rerun()

        st.markdown("---")

        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.setup_complete = False
            st.rerun()

        st.markdown("---")
        st.markdown("**Threads**")
        if st.button("＋ New thread", use_container_width=True):
            new_id = f"New Chat {len(st.session_state.threads) + 1}"
            st.session_state.threads[new_id] = {"messages": [], "model": "llama3.2"}
            st.session_state.active_thread = new_id
            st.session_state.pending_text = ""
            st.session_state.last_audio_hash = None
            st.session_state.last_doc_hash = None
            save_chats(st.session_state.threads)
            st.rerun()

        for t_id in list(st.session_state.threads.keys()):
            is_active = t_id == st.session_state.active_thread
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                if st.button(t_id, key=f"sb_{t_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.active_thread = t_id
                    st.session_state.pending_text = ""
                    st.session_state.last_audio_hash = None
                    st.session_state.last_doc_hash = None
                    st.rerun()
            with col2:
                if st.button("🧹", key=f"clr_{t_id}", help="Clear chat"):
                    st.session_state.threads[t_id]['messages'] = []
                    save_chats(st.session_state.threads)
                    clr_dir = os.path.join(st.session_state.base_output_dir, re.sub(r'[\\/*?:"<>|.]', "", t_id).strip())
                    if os.path.exists(clr_dir): shutil.rmtree(clr_dir, ignore_errors=True)
                    st.rerun()
            with col3:
                if st.button("✕", key=f"del_{t_id}", help="Delete chat"):
                    del st.session_state.threads[t_id]
                    if st.session_state.active_thread == t_id:
                        st.session_state.active_thread = list(st.session_state.threads.keys())[0] if st.session_state.threads else "General"
                    save_chats(st.session_state.threads)
                    del_dir = os.path.join(st.session_state.base_output_dir, re.sub(r'[\\/*?:"<>|.]', "", t_id).strip())
                    if os.path.exists(del_dir): shutil.rmtree(del_dir, ignore_errors=True)
                    st.rerun()
        
        if st.session_state.active_thread != "General":
            new_name = st.text_input("Rename Active Chat", value=st.session_state.active_thread, key="rename_input")
            if new_name != st.session_state.active_thread and new_name not in st.session_state.threads:
                old_safe = re.sub(r'[\\/*?:"<>|.]', "", st.session_state.active_thread).strip()
                new_safe = re.sub(r'[\\/*?:"<>|.]', "", new_name).strip()
                old_dir = os.path.join(st.session_state.base_output_dir, old_safe)
                new_dir = os.path.join(st.session_state.base_output_dir, new_safe)
                if os.path.exists(old_dir) and not os.path.exists(new_dir):
                    os.rename(old_dir, new_dir)
                    
                st.session_state.threads[new_name] = st.session_state.threads.pop(st.session_state.active_thread)
                st.session_state.active_thread = new_name
                save_chats(st.session_state.threads)
                st.rerun()

        st.markdown("---")
        st.markdown("**Files**")
        
        with st.expander("＋ New Folder"):
            new_f_name = st.text_input("Folder Name", key="new_f_input")
            if st.button("Create Folder", use_container_width=True) and new_f_name:
                os.makedirs(os.path.join(st.session_state.output_dir, new_f_name), exist_ok=True)
                st.rerun()

        if st.button("🗑️ Clear All", use_container_width=True):
            if os.path.exists(st.session_state.output_dir):
                shutil.rmtree(st.session_state.output_dir, ignore_errors=True)
            os.makedirs(st.session_state.output_dir, exist_ok=True)
            st.rerun()

        # File routing logic
        if not os.path.exists(st.session_state.output_dir): os.makedirs(st.session_state.output_dir)
        items = os.listdir(st.session_state.output_dir)
        folders = [f for f in items if os.path.isdir(os.path.join(st.session_state.output_dir, f))]
        files = [f for f in items if os.path.isfile(os.path.join(st.session_state.output_dir, f))]

        # Render Root Files
        for f in files:
            fp = os.path.join(st.session_state.output_dir, f)
            is_expanded = (st.session_state.open_sidebar_file == f)
            
            # Use dynamic keys to force expansion reset on button click
            exp_key = f"exp_{f}_{st.session_state.expander_pulse}"
            
            # Wrap in a div with an ID for auto-scrolling
            st.markdown(f'<div id="file-anchor-{f}"></div>', unsafe_allow_html=True)
            with st.expander(f"📄 {f}", expanded=is_expanded):
                col_r, col_df = st.columns([5, 1])
                with col_r:
                    new_f = st.text_input("Rename", value=f, key=f"rn_{f}", label_visibility="collapsed")
                    if new_f != f and new_f.strip():
                        os.rename(fp, os.path.join(st.session_state.output_dir, new_f.strip()))
                        st.rerun()
                with col_df:
                    if st.button("🗑️", key=f"del_{f}", help="Delete File"):
                        os.unlink(fp)
                        st.rerun()

                with open(fp, "r", encoding="utf-8") as file_: c = file_.read()
                st.download_button("Download", data=c, file_name=f, key=f"dl_{f}")
                st.code(c, language="python" if f.endswith(".py") else None)
                if folders:
                    target_dir = st.selectbox("Move into folder...", ["-- Select --"] + folders, key=f"mv_{f}")
                    if target_dir != "-- Select --":
                        shutil.move(fp, os.path.join(st.session_state.output_dir, target_dir, f))
                        st.rerun()

        # Render Folders
        for d in folders:
            dp = os.path.join(st.session_state.output_dir, d)
            subfiles = [f for f in os.listdir(dp) if os.path.isfile(os.path.join(dp, f))]
            folder_expanded = (st.session_state.open_sidebar_file in subfiles)
            
            exp_key_f = f"exp_fold_{d}_{st.session_state.expander_pulse}"
            
            # Wrap in a div with an ID for auto-scrolling
            st.markdown(f'<div id="folder-anchor-{d}"></div>', unsafe_allow_html=True)
            with st.expander(f"📁 {d} ({len(subfiles)})", expanded=folder_expanded):
                c_rn, c_del = st.columns([5,1])
                with c_rn:
                    new_d = st.text_input("Rename folder", value=d, key=f"rn_{d}", label_visibility="collapsed")
                    if new_d != d and new_d.strip():
                        os.rename(dp, os.path.join(st.session_state.output_dir, new_d.strip()))
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"del_{d}", help="Delete Folder"):
                        shutil.rmtree(dp, ignore_errors=True)
                        st.rerun()

                st.markdown("---")
                if not subfiles: st.caption("Empty folder")
                for sf in subfiles:
                    sfp = os.path.join(dp, sf)
                    is_active = (st.session_state.open_sidebar_file == sf)
                    
                    if is_active: st.markdown(f"**👉 `{sf}`**")
                    else: st.markdown(f"`{sf}`")
                    
                    c_rn_sf, c_del_sf = st.columns([5, 1])
                    with c_rn_sf:
                        new_sf = st.text_input("Rename subfile", value=sf, key=f"rn_{d}_{sf}", label_visibility="collapsed")
                        if new_sf != sf and new_sf.strip():
                            os.rename(sfp, os.path.join(dp, new_sf.strip()))
                            st.rerun()
                    with c_del_sf:
                        if st.button("🗑️", key=f"del_{d}_{sf}"):
                            os.unlink(sfp)
                            st.rerun()

                    col_u, col_d2 = st.columns(2)
                    with col_u:
                        if st.button("Up ↰", key=f"up_{d}_{sf}", help="Move to root"):
                            shutil.move(sfp, os.path.join(st.session_state.output_dir, sf))
                            st.rerun()
                    with col_d2:
                        with open(sfp, "r", encoding="utf-8") as sfile_: sc = sfile_.read()
                        st.download_button("💾 Download", data=sc, file_name=sf, key=f"dl_{d}_{sf}")
                        
                    show_code = st.checkbox(f"👁️ View file code", value=is_active, key=f"view_{d}_{sf}")
                    if show_code: 
                        st.code(sc, language="python" if sf.endswith(".py") else None)
                    st.markdown("---")

        # ── Auto-Scroll Snipe Logic ──
        if st.session_state.open_sidebar_file:
            target = st.session_state.open_sidebar_file
            st.components.v1.html(f"""
                <script>
                const targetId = 'file-anchor-{target}';
                const el = window.parent.document.getElementById(targetId);
                if (el) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
                </script>
            """, height=0)

        col_code, col_file, col_sum = st.columns(3)
        
        # 1. LIVE CODE COMMAND
        with col_code:
            st.markdown('<div class="label-text">🎤 Record Code Command</div>', unsafe_allow_html=True)
            audio_code = st.audio_input("Code Mic", label_visibility="collapsed", key=f"mic_code_{st.session_state.active_thread}_{st.session_state.expander_pulse}")

            if audio_code:
                current_hash = hash(audio_code.getvalue())
                if current_hash != st.session_state.last_audio_hash:
                    buf_path = os.path.join(".audio_cache", f"mic_{st.session_state.active_thread}.wav")
                    with open(buf_path, 'wb') as f: f.write(audio_code.getbuffer())
                    with st.spinner("Extracting logic..."):
                        t = LocalAIAgent(mode=st.session_state.mode, model_name=st.session_state.threads[st.session_state.active_thread].get('model', 'llama3.2')).transcribe(buf_path)
                        if t.startswith("LANG_ERR"):
                            st.warning(f"⚠️ {t.replace('LANG_ERR: ', '')}")
                        else:
                            append_to_input(t)
                        st.session_state.last_audio_hash = current_hash
                    st.rerun()

        # 2. UPLOAD LOGIC SOURCE
        with col_file:
            st.markdown('<div class="label-text">📁 Upload Audio Source</div>', unsafe_allow_html=True)
            up = st.file_uploader("Audio Upload", type=["wav", "mp3"], label_visibility="collapsed", key=f"up_{st.session_state.active_thread}_{st.session_state.expander_pulse}")
            
            if up:
                current_file_hash = hash(up.getvalue())
                if current_file_hash != st.session_state.last_file_hash:
                    up_path = os.path.join(".audio_cache", f"up_{st.session_state.active_thread}.wav")
                    with open(up_path, "wb") as f: f.write(up.getbuffer())
                    with st.spinner("Processing logic file..."):
                        t = LocalAIAgent(mode=st.session_state.mode, model_name=st.session_state.threads[st.session_state.active_thread].get('model', 'llama3.2')).transcribe(up_path)
                        if t.startswith("LANG_ERR"):
                            st.warning(f"⚠️ {t.replace('LANG_ERR: ', '')}")
                        else:
                            append_to_input(f"--- ATTACHED LOGIC SOURCE ---\n{t}\n--- END SOURCE ---")
                        st.session_state.last_file_hash = current_file_hash
                    st.rerun()

        # 3. LIVE SUMMARIZE Command
        with col_sum:
            st.markdown('<div class="label-text">📝 Record Summarize</div>', unsafe_allow_html=True)
            audio_summ = st.audio_input("Summ Mic", label_visibility="collapsed", key=f"mic_sum_{st.session_state.active_thread}_{st.session_state.expander_pulse}")
            
            if audio_summ:
                current_sum_hash = hash(audio_summ.getvalue())
                if current_sum_hash != st.session_state.get('last_sum_hash'):
                    buf_path = os.path.join(".audio_cache", f"sum_{st.session_state.active_thread}.wav")
                    with open(buf_path, 'wb') as f: f.write(audio_summ.getbuffer())
                    with st.spinner("Drafting summary..."):
                        t = LocalAIAgent(mode=st.session_state.mode, model_name=st.session_state.threads[st.session_state.active_thread].get('model', 'llama3.2')).transcribe(buf_path)
                        if t.startswith("LANG_ERR"):
                            st.warning(f"⚠️ {t.replace('LANG_ERR: ', '')}")
                        else:
                            append_to_input(f"Summarize this concisely: {t}")
                            st.session_state.run_trigger = True
                        st.session_state.last_sum_hash = current_sum_hash
                    st.rerun()

    # ── Header ──
    st.markdown(f"### 💬 {st.session_state.active_thread}")

    # ── Input Bar ──
    input_key = f"cmd_input_{st.session_state.active_thread}"
    if input_key not in st.session_state:
        st.session_state[input_key] = ""

    def append_to_input(text):
        if st.session_state[input_key].strip():
            st.session_state[input_key] += f"\n\n{text}"
        else:
            st.session_state[input_key] = text

                    st.session_state.last_file_hash = current_file_hash
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_input, col_btn = st.columns([8, 1])
    with col_input:
        st.text_area("Review Transcribed Text / Type Command", height=68, placeholder="Press Ctrl+Enter to effortlessly submit your command...", key=input_key)
        f_cmd = st.session_state[input_key]
    with col_btn:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        is_error = "❌" in f_cmd
        
        def handle_submit():
            val = st.session_state[input_key]
            if val.strip() and not ("❌" in val):
                st.session_state.last_transcription = val
                st.session_state[input_key] = ""
                st.session_state.run_trigger = True
                
        st.button("➤ Submit", use_container_width=True, type="primary", disabled=is_error, on_click=handle_submit)

    st.markdown("---")

    # ── Chat History ──
    if st.session_state.active_thread not in st.session_state.threads:
        st.session_state.threads[st.session_state.active_thread] = {"messages": [], "model": "llama3.2"}
        save_chats(st.session_state.threads)
        
    thread_data = st.session_state.threads[st.session_state.active_thread]
    history = thread_data['messages']
    current_thread_model = thread_data.get('model', 'llama3.2')
    
    with st.container(height=450):
        if not history:
            st.markdown('<div class="empty-state">No messages yet.<br>Type a command above to begin.</div>', unsafe_allow_html=True)
        for idx, msg in enumerate(history):
            if msg['role'] == 'user':
                st.markdown(f'<div class="chat-user"><b>🎙️ Transcribed Text:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                intent_val = msg.get("intent", "UNKNOWN").upper()
                ex_t = msg.get("execution_time")
                time_badge = f'<span style="float: right; color:#a6accd;">⏱️ {ex_t}s</span>' if ex_t is not None else ""
                
                st.markdown(f'<div class="chat-bot">', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.75rem; color:#89b4fa; font-weight:700; margin-bottom: 6px;">🧠 DETECTED INTENT: {intent_val}{time_badge}</div>', unsafe_allow_html=True)
                
                if msg.get('file_data'):
                    fd = msg['file_data']
                    st.markdown(f'<b>⚙️ Action Taken:</b> Invoked local file system module.<br>', unsafe_allow_html=True)
                    st.markdown(f'<b>✅ Final Output:</b> Successfully created and routed <code>{fd["name"]}</code>.<br><br>', unsafe_allow_html=True)
                    
                    if st.button(f"🔍 Show '{fd['name']}' in Sidebar Explorer", key=f"btn_open_{idx}"):
                        st.session_state.open_sidebar_file = fd['name']
                        st.session_state.expander_pulse += 1 # Force rotate expander IDs
                        st.rerun()
                else:
                    action_txt = "Processed text summary via LLM." if intent_val == "SUMMARIZE" else "Generated conversational text response based on context."
                    st.markdown(f'<b>⚙️ Action Taken:</b> {action_txt}<br>', unsafe_allow_html=True)
                    st.markdown(f'<b>✅ Final Output:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

    # ── Agent Execution ──
    if st.session_state.run_trigger:
        try:
            with st.status("🚀 Aura is thinking...", expanded=True) as status:
                start_t = time.time()
                is_first_msg = len(history) == 0
                res_container = {"data": None, "error": None}
                
                # Capture state for thread-safety
                smode = st.session_state.mode
                smodel = current_thread_model
                strans = st.session_state.last_transcription
                sout = st.session_state.output_dir
                shist = history
                sthreshold = st.session_state.latency_threshold

                def run_agent():
                    try:
                        agent = LocalAIAgent(mode=smode, model_name=smodel)
                        res_container["data"] = agent.execute(strans, sout, shist)
                    except Exception as e: res_container["error"] = str(e)

                t = threading.Thread(target=run_agent)
                t.start()
                
                timer_p = st.empty()
                fallback_trig = False
                while t.is_alive():
                    elap = time.time() - start_t
                    timer_p.markdown(f"⏱️ **Elapsed:** {elap:.1f}s / {sthreshold}s")
                    if elap > sthreshold and not fallback_trig:
                        fallback_trig = True
                        st.warning("⚠️ Local engine is running slow.")
                        if st.session_state.get('available_apis'):
                            if st.button("🚀 Switch to Global (Groq) for Instant Result?", key="fallback_btn"):
                                st.session_state.mode = "global"
                                st.session_state.threads[st.session_state.active_thread]['model'] = "groq"
                                st.rerun()
                    time.sleep(0.1)
                t.join()
                
                if res_container["error"]:
                    st.error(f"Error: {res_container['error']}")
                    res = {"result": "Execution failed.", "intent": "chat"}
                else:
                    res = res_container["data"]
                
                elapsed = round(time.time() - start_t, 2)
                is_first_msg = len(history) == 0
                
                # Append user msg
                st.session_state.threads[st.session_state.active_thread]['messages'].append(
                    {"role": "user", "content": st.session_state.last_transcription}
                )
                
                # Append bot msg with potential file_data and intent
                st.session_state.threads[st.session_state.active_thread]['messages'].append(
                    {
                        "role": "assistant", 
                        "content": res["result"], 
                        "file_data": res.get("file_data"),
                        "intent": res.get("intent", "CHAT"),
                        "execution_time": elapsed
                    }
                )
                
                # Auto-name thread based on first prompt
                if is_first_msg and st.session_state.active_thread.startswith("New Chat"):
                    short_desc = st.session_state.last_transcription[:25].strip()
                    auto_name = f"{short_desc}..." if len(st.session_state.last_transcription) > 25 else short_desc
                    # Ensure uniqueness
                    if auto_name in st.session_state.threads: auto_name += " (1)"
                    
                    old_safe = re.sub(r'[\\/*?:"<>|.]', "", st.session_state.active_thread).strip()
                    new_safe = re.sub(r'[\\/*?:"<>|.]', "", auto_name).strip()
                    old_dir = os.path.join(st.session_state.base_output_dir, old_safe)
                    new_dir = os.path.join(st.session_state.base_output_dir, new_safe)
                    if os.path.exists(old_dir) and not os.path.exists(new_dir):
                        os.rename(old_dir, new_dir)
                        
                    st.session_state.threads[auto_name] = st.session_state.threads.pop(st.session_state.active_thread)
                    st.session_state.active_thread = auto_name

                save_chats(st.session_state.threads)
                status.update(label="Done", state="complete")
            st.session_state.run_trigger = False
            st.session_state.last_transcription = ""
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.run_trigger = False
