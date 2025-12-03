import streamlit as st
import requests
import json
from PyPDF2 import PdfReader

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="ChatBot", page_icon="💬", layout="wide")

MODEL_NAME = "tinyllama"   # Use small model for 8GB RAM
OLLAMA_URL = "http://localhost:11434"


# -------------------------
# HELPER FUNCTIONS
# -------------------------
def check_ollama_alive():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/version", timeout=3)
        if r.status_code == 200:
            return True, r.json()
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def ollama_query(prompt, model=MODEL_NAME):
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        r = requests.post(f"{OLLAMA_URL}/api/generate",
                          json=payload, timeout=60)

        if r.status_code != 200:
            return f"❌ Ollama error: {r.text}"

        return r.json().get("response", "").strip()

    except Exception as e:
        return f"❌ Connection error: {e}"


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def chunk_text(text, size=800):
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]


# -------------------------
# SESSION MANAGEMENT
# -------------------------
if "history" not in st.session_state:
    st.session_state.history = []


# -------------------------
# HEADER
# -------------------------
st.markdown("<h1 style='text-align:center;'>💬 ChatBot</h1>", unsafe_allow_html=True)

alive, info = check_ollama_alive()
if alive:
    st.success(f"Ollama is running — {info}")
else:
    st.error(f"Ollama not reachable — {info}")


# -------------------------
# SIDEBAR (HISTORY + UPLOAD)
# -------------------------
with st.sidebar:
    st.subheader("📂 Upload File")

    uploaded_pdf = st.file_uploader("Upload PDF file", type=["pdf"])

    st.write("---")
    st.subheader("📜 Chat History")

    for i, item in enumerate(st.session_state.history):
        st.write(f"**{i+1}.** {item[:40]}...")


# -------------------------
# PROCESS PDF
# -------------------------
if uploaded_pdf:
    st.success("File uploaded successfully!")

    # Extract text
    with st.spinner("Extracting text from PDF..."):
        text = extract_pdf_text(uploaded_pdf)

    st.markdown("### 📄 Extracted Text (Auto Language Detect)")

    st.write(text[:1000] + "...")   # Preview only

    # Chunking
    chunks = chunk_text(text)

    st.markdown("### 🧩 Chunks")
    st.info(f"Total chunks: {len(chunks)} (hidden)")   # Only show count

    # Translate + Summarize
    final_summary = ""

    with st.spinner("Translating & Summarizing into English..."):
        for chunk in chunks:
            prompt = f"""
            Translate the following text to English and summarize it clearly:

            {chunk}
            """
            response = ollama_query(prompt)
            final_summary += response + "\n\n"

    # Save to history
    st.session_state.history.append(f"Summary: {final_summary[:50]}")

    # Output summary
    st.markdown("## 📝 Summary in English")
    st.write(final_summary)


# -------------------------
# MANUAL QUESTION INPUT
# -------------------------
st.write("---")
user_input = st.text_input("Ask something about the PDF or anything:")

if st.button("Send"):
    if user_input.strip():
        response = ollama_query(user_input)
        st.session_state.history.append(f"Q: {user_input}")
        st.markdown("### 💬 ChatBot Reply")
        st.write(response)
