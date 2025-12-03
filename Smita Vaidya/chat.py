import streamlit as st
import requests
import json
import pandas as pd
import chardet
import fitz 

from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

st.set_page_config(
    page_title="Language Simplifier",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def detect_output_language(user_input):
    """Detect if the user is asking for a specific output language."""
    if not user_input:
        return "en"  

    language_keywords = {
        "hindi": "hi",
        "english": "en",
        "urdu": "ur",
        "arabic": "ar",
        "french": "fr",
        "spanish": "es",
        "german": "de",
        "marathi": "mr",
        "gujarati": "gu",
        "tamil": "ta",
        "telugu": "te",
        "kannada": "kn"
    }

    text = user_input.lower()
    for key, code in language_keywords.items():
        if key in text:
            return code  

    try:
        return detect(user_input)
    except:
        return "en" 

# STREAMING OLLAMA FUNCTION
def stream_ollama(prompt):
    """Stream response from local Ollama (Llama 3 model)."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": True},
            stream=True
        )

        partial_text = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = json.loads(line)
                token = data.get("response", "")
                partial_text += token
                yield partial_text
            except:
                continue

    except Exception as e:
        yield f"⚠️ Error communicating with Ollama: {e}"

# UTILITY: CHUNK TEXT
def chunk_text(text, max_chars=1000, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

st.title("🤖 AI based Contract Language Simplifier")

# SESSION MANAGEMENT
if "sessions" not in st.session_state:
    st.session_state.sessions = {
        "Chat 1": {"messages": [], "file_chunks": [], "uploaded_file_name": None}
    }

if "current_session" not in st.session_state:
    st.session_state.current_session = "Chat 1"

# SIDEBAR: Chat Sessions
st.sidebar.title("Chat Sessions")
if st.sidebar.button("➕ New Chat"):
    new_name = f"Chat {len(st.session_state.sessions)+1}"
    st.session_state.sessions[new_name] = {"messages": [], "file_chunks": [], "uploaded_file_name": None}
    st.session_state.current_session = new_name
    st.rerun()

# Delete button
st.sidebar.markdown("""
<style>
button[kind="secondary"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}
button[kind="secondary"] > div {
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# List chats
for name in list(st.session_state.sessions.keys()):
    cols = st.sidebar.columns([6,1])
    if cols[0].button(name, key=f"switch_{name}"):
        st.session_state.current_session = name
        st.rerun()
    if cols[1].button("❌", key=f"delete_{name}"):
        del st.session_state.sessions[name]
        if st.session_state.sessions:
            st.session_state.current_session = list(st.session_state.sessions.keys())[0]
        else:
            st.session_state.sessions = {"Chat 1": {"messages": [], "file_chunks": [], "uploaded_file_name": None}}
            st.session_state.current_session = "Chat 1"
        st.rerun()

st.markdown("""
<style>

/* New Chat Button */
button[kind="primary"] {
    background: linear-gradient(135deg, #ff9966, #ff5e62) !important;
    color: black !important;           /* Text color black */
    border-radius: 12px !important;
    font-weight: 600;
}

/* Delete Chat Button */
button[kind="secondary"] {
    background: transparent !important;
    color: black !important;           /* Text color black */
    border:none !important;
    font-size: 20px !important;
    font-weight: 600;
}

button[kind="secondary"]:hover {
    color: #d60000 !important;
}

</style>
""", unsafe_allow_html=True)

# SIDEBAR: File Upload (per session)
st.sidebar.markdown("### 📄 Upload File")

uploaded_file = st.sidebar.file_uploader(
    "Choose a file",
    type=['txt','pdf','csv'],
    key=f"file_uploader_{st.session_state.current_session}"
)

current_chat = st.session_state.sessions[st.session_state.current_session]
chat_history = current_chat["messages"]
file_chunks = current_chat["file_chunks"]

# CASE 1: No new upload → keep existing file
if uploaded_file is None:
    pass

# CASE 2: New file uploaded
elif uploaded_file.name != current_chat.get("uploaded_file_name"):

    content = ""
    if uploaded_file.name.endswith(".txt"):
        raw_data = uploaded_file.read()
        detected = chardet.detect(raw_data)
        encoding = detected["encoding"] or "utf-8"

        content = raw_data.decode(encoding, errors="ignore")

    elif uploaded_file.name.endswith(".pdf"):

        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            for page in doc:
                text = page.get_text("text")
                if text:
                    content += text + "\n"

    elif uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        content = df.to_string()

    current_chat["file_chunks"] = chunk_text(content, max_chars=1000, overlap=100)
    current_chat["uploaded_file_name"] = uploaded_file.name

    info_message = f"📄 **File loaded:** {len(current_chat['file_chunks'])} chunks extracted."
    current_chat["messages"].append({"role": 'assistant', "content": info_message})

# Display chat history
for message in chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# CHAT INPUT and STREAMING REPLY
if prompt := st.chat_input("Type your question here..."):

    with st.chat_message("user"):
        st.markdown(prompt)
    chat_history.append({"role": "user", "content": prompt})

    output_lang = detect_output_language(prompt)

    if file_chunks:
        MAX_CHARS = 40000
        combined_text = "\n".join(file_chunks)[:MAX_CHARS]

        full_prompt = f"""
You are a multilingual AI assistant.

You have access to the following document:

--- DOCUMENT CONTENT START ---
{combined_text}
--- DOCUMENT CONTENT END ---

User question: {prompt}

Instructions:
- Understand the document even if multilingual
- Answer only in requested language
- Output language = {output_lang}

Now respond in language = {output_lang}:
"""
    else:
        full_prompt = prompt

    with st.chat_message("assistant"):
        placeholder = st.empty()
        final_text = ""
        for partial in stream_ollama(full_prompt):
            placeholder.markdown(partial)
            final_text = partial

    chat_history.append({"role": "assistant", "content": final_text})






