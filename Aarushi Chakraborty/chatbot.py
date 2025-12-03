import streamlit as st
import requests
import json
import threading
import time
from pathlib import Path
import fitz
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

st.set_page_config(page_title="Chatbot", layout="wide")
st.markdown("""
<style>
header .stAppName { 
    visibility: hidden; 
}

div[data-testid="stToolbar"]::before {
    content: "ClauseEase AI";
    font-size: 20px;
    font-weight: 600;
    color: white;

    position: absolute;
    top: 50%;
    left: 20px;
    transform: translateY(-50%);
    pointer-events: none;
}

/* Keep the toolbar height consistent */
div[data-testid="stToolbar"] {
    height: 48px;   
}

</style>
""", unsafe_allow_html=True)


# UI Styling
st.markdown("""
<style>
.stApp { 
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); 
    color: #ffffff; 
    font-family: 'Segoe UI', sans-serif; 
}
.stChatMessage { 
    border-radius: 20px; 
    padding: 14px 20px; 
    margin: 8px 0; 
    max-width: 100%; 
    word-wrap: break-word; 
    display: inline-block; 
    backdrop-filter: blur(5px); 
}
[data-testid="stChatMessage-Assistant"] { 
    background: rgba(255, 255, 255, 0.1); 
    border-left: 3px solid #00bfff; 
    text-align: left; 
}
[data-testid="stChatMessage-User"] { 
    background: rgba(255, 255, 255, 0.15); 
    border-right: 3px solid #ff69b4; 
    text-align: right; 
    margin-left: auto; 
}
.stChatMessage:hover { 
    transform: scale(1.02); 
    transition: 0.2s; 
}
.upload-heading {
    font-size: 20px;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 8px;
    color: white;
}
</style>
""", unsafe_allow_html=True)



# PDF / TXT Processing
def is_pdf_file(file_bytes: bytes) -> bool:
    return b"%PDF" in file_bytes[:64]

def extract_pdf_fast(file_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text("text") for page in doc)
    except:
        return ""

def chunk_text(text, chunk_size=800):
    words = text.split()
    out, cur = [], []
    for w in words:
        cur.append(w)
        if sum(len(x) + 1 for x in cur) >= chunk_size:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


# Ollama Streaming
stop_flag = threading.Event()

def stop_generation():
    stop_flag.set()

def stream_resp(prompt):
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3:latest", "prompt": prompt},
            stream=True,
            timeout=300,
        )
        placeholder = st.empty()
        reply = ""
        last = time.time()

        for line in r.iter_lines():
            if stop_flag.is_set():
                break
            if line:
                data = json.loads(line.decode("utf-8"))
                if "response" in data:
                    reply += data["response"]
                    if time.time() - last > 0.1:
                        placeholder.markdown(reply + "▌")
                        last = time.time()

        placeholder.markdown(reply.strip() or "*No response*")
        return reply.strip()

    except Exception as e:
        st.error(f"Error connecting to Ollama: {e}")
        return ""


# Helpers
def fast_detect_lang(text: str) -> str:
    snippet = text[:500].strip()
    if not snippet or snippet.isascii():
        return "English"
    try:
        lang_code = detect(snippet)
        mapping = {
            "en": "English","hi": "Hindi","es": "Spanish","fr": "French","de": "German",
            "zh-cn": "Chinese","zh-tw": "Chinese","ru": "Russian","ja": "Japanese",
            "ko": "Korean","ar": "Arabic","it": "Italian","bn": "Bengali"
        }
        return mapping.get(lang_code, lang_code)
    except:
        return "Unknown"


# Summaries / Translation / Q&A
def summarize_file(name):
    info = st.session_state.pdf_data.get(name)
    return stream_resp(f"Summarize the following text:\n\n{info['full_text'][:4000]}")

def translate_file(name):
    info = st.session_state.pdf_data.get(name)
    return stream_resp(
        f"The text is in {info['lang']}. Translate it to English:\n\n{info['original_text'][:4000]}"
    )

def answer_from_file(name, question):
    info = st.session_state.pdf_data.get(name)
    return stream_resp(
        f"Use only this document to answer.\n\nDOC:\n{info['full_text'][:4000]}\n\nQ:{question}\nA:"
    )


# Session State
for key, default in {
    "msgs": [{"role":"assistant","content":"Hello! How can I help you today?"}],
    "hist": [],
    "uploaded_names": [],
    "generating": False,
    "pdf_data": {},
    "upload_key": 0
}.items():
    st.session_state.setdefault(key, default)


# Sidebar — New Chat, Upload, and Chat History
with st.sidebar:

    if st.button("New Chat", use_container_width=True):
        if len(st.session_state.msgs) > 1:
            st.session_state.hist.append(st.session_state.msgs)
        st.session_state.msgs = [{"role":"assistant","content":"Hello! How can I help you today?"}]
        st.session_state.pdf_data = {}
        st.session_state.uploaded_names = []
        st.session_state.upload_key += 1
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='upload-heading'>Upload Files</div>", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "",
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.upload_key}",
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("<h2 style='text-align: left; color: white;'>Previous Chats</h2>", unsafe_allow_html=True)

    if st.session_state.hist:
        for idx, chat in enumerate(st.session_state.hist):
            summary = None
            for msg in chat:
                if msg.get("role") == "user":
                    if msg.get("type") == "file":
                        name = msg["file_name"]
                        if len(name) > 20:
                            name = name[:15] + "…" + name.split('.')[-1]
                        summary = name
                        break
                    elif msg.get("content"):
                        content = msg["content"].strip()
                        summary = content[:25] + ("…" if len(content) > 25 else "")
                        break
            if not summary:
                summary = "(No message)"

            if st.button(f"Chat {idx+1}: {summary}", key=f"hist_{idx}", use_container_width=True):
                st.session_state.msgs = chat
                st.session_state.uploaded_names = [
                    m["file_name"] for m in chat if m.get("type") == "file"
                ]
                st.session_state.upload_key += 1
                st.rerun()


# Chat Window
for msg in st.session_state.msgs:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# Chat Input
input_text = st.chat_input("Ask me anything...")

if input_text and not st.session_state.generating:
    st.session_state.msgs.append({"role":"user","content":input_text})
    with st.chat_message("user"):
        st.write(input_text)

    st.session_state.generating = True
    stop_flag.clear()

    with st.chat_message("assistant"):
        st.button("Stop Generation", on_click=stop_generation)
        with st.spinner("Thinking..."):

            text = input_text.lower()
            data = st.session_state.pdf_data
            reply = None

            if "summarize" in text and data:
                target = next((fn for fn in data if fn.lower() in text), None)
                if not target and len(data) == 1:
                    target = list(data.keys())[0]
                reply = summarize_file(target) if target else "Which file?"

            if reply is None and "translate" in text and data:
                target = next((fn for fn in data if fn.lower() in text), None)
                if not target and len(data) == 1:
                    target = list(data.keys())[0]
                reply = translate_file(target) if target else "Which file?"

            if reply is None and data:
                target = next((fn for fn in data if fn.lower() in text), None)
                if target:
                    reply = answer_from_file(target, input_text)

            if reply is None:
                reply = stream_resp(input_text)

    st.session_state.msgs.append({"role":"assistant","content":reply})
    st.session_state.generating = False
    st.rerun()


# File Handling
if uploaded_files:
    new = False
    for file in uploaded_files:
        if file.name in st.session_state.uploaded_names:
            continue

        st.session_state.uploaded_names.append(file.name)
        file_bytes = file.getvalue()
        suffix = Path(file.name).suffix.lower()

        is_pdf = (suffix == ".pdf") or is_pdf_file(file_bytes)

        if is_pdf:
            preview = extract_pdf_fast(file_bytes)[:500]
        else:
            try:
                preview = file_bytes.decode("utf-8", errors="ignore")[:500]
            except:
                preview = file_bytes.decode("latin-1", errors="ignore")[:500]

        st.session_state.msgs.append({
            "role": "assistant",
            "content": (
                f"Processing `{file.name}`...\n\n"
                f"Preview:\n```text\n{preview}\n```"
            )
        })

        if is_pdf:
            full_text = extract_pdf_fast(file_bytes)
        else:
            try:
                full_text = file_bytes.decode("utf-8", errors="ignore")
            except:
                full_text = file_bytes.decode("latin-1", errors="ignore")

        lang = fast_detect_lang(full_text)
        chunks = chunk_text(full_text)

        st.session_state.pdf_data[file.name] = {
            "full_text": full_text,
            "chunks": chunks,
            "lang": lang,
            "original_text": full_text,
        }

        st.session_state.msgs.append({
            "role": "assistant",
            "content": (
                f"Your file `{file.name}` has been processed into **{len(chunks)} chunks**.\n"
                f"Language detected: **{lang}**.\n"
                "How can I help with this?"
            )
        })

        new = True

    if new:
        st.rerun()
