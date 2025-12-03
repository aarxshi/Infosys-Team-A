import streamlit as st
import ollama
import time
import json
import tempfile
import os

# --- Import Libraries for File Reading ---
# These are necessary for PDF/DOCX file handling
try:
    from pypdf import PdfReader
except ImportError:
    st.error("Please install pypdf: pip install pypdf")
    st.stop()

try:
    import docx
except ImportError:
    st.error("Please install python-docx: pip install python-docx")
    st.stop()

# --- Configuration ---
OLLAMA_MODEL = 'llama3.2:3b' 
SYSTEM_PROMPT = """
You are ClauseEase, an expert legal language simplifier and translator. 
Your primary goal is to analyze the provided text, regardless of the input language, 
and produce a concise, legally accurate summary or explanation in **Plain English**.
Use bold text for key terms.
"""

# --- 1. Load Custom CSS ---
def local_css(file_name):
    """Function to load custom CSS file into the Streamlit app."""
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"{file_name} not found. Custom styles may not load.")

# --- 2. Backend Functions (Chunking & API) ---
def chunk_text(text, chunk_size=4000, overlap=500):
    """Splits text into smaller overlapping chunks."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        if end < text_len:
            last_period = text.rfind('.', start, end)
            if last_period != -1: end = last_period + 1
            else:
                last_space = text.rfind(' ', start, end)
                if last_space != -1: end = last_space
        chunks.append(text[start:end])
        start = end - overlap
        if start >= end: start = end 
    return chunks

@st.cache_data 
def get_ollama_response(messages):
    """Calls the Ollama API with message history."""
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages, 
            stream=False
        )
        return response['message']['content']
    except Exception as e:
        return f"Error: {e}"

def extract_text_from_file(uploaded_file):
    """Extracts raw text from PDF or DOCX file object."""
    text = ""
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else: 
            text = uploaded_file.read().decode("utf-8")
        return text
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

# --- UI Setup ---
st.set_page_config(page_title="ClauseEase AI", page_icon="⚖️", layout="wide")

# Load the CSS file
local_css("style.css")

# --- Sidebar ---
with st.sidebar:
    st.title("CLAUSE EASE")
    st.markdown("### *Your Legal Assistant*")
    st.caption(f"Engine: **{OLLAMA_MODEL}**")
    
    st.markdown("---")
    if st.button("📝 New Conversation", use_container_width=True):
        st.session_state.messages = []
        keys_to_clear = ["document_text", "uploaded_file_name"]
        for key in keys_to_clear:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
    
    st.markdown("### History")
    if "messages" in st.session_state:
        for msg in st.session_state.messages:
            if msg['role'] == 'user':
                st.caption(f"• {msg['content'][:25]}...")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome. Upload a legal document to begin analysis."}]

# --- Main Layout ---
col_main_1, col_main_2 = st.columns([1, 3])

# --- Left Column: Document Controls ---
with col_main_1:
    st.subheader("INPUT")
    uploaded_file = st.file_uploader("Upload Contract", type=["pdf", "docx", "txt"], label_visibility="visible")

    if uploaded_file:
        if "uploaded_file_name" not in st.session_state or st.session_state.uploaded_file_name != uploaded_file.name:
            st.session_state.uploaded_file_name = uploaded_file.name
            if "document_text" in st.session_state: del st.session_state.document_text
        
        # Summarize Button Logic
        if st.button(f"Summarize Document", use_container_width=True):
            overall_start_time = time.time() # Start Timer
            
            with st.spinner("1. Extracting text..."):
                raw_text = extract_text_from_file(uploaded_file)
            
            if raw_text:
                st.session_state.document_text = raw_text 
                
                try:
                    # JSON Storage Simulation
                    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json', encoding='utf-8') as temp_json:
                        temp_filename = temp_json.name
                        document_data = {"content": raw_text}
                        json.dump(document_data, temp_json)
                    with open(temp_filename, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)
                    text_to_process = loaded_data['content']
                    os.remove(temp_filename)

                    # Chunking Process
                    chunks = chunk_text(text_to_process, chunk_size=4000, overlap=200)
                    total_chunks = len(chunks)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty() # Placeholder for timer text
                    partial_summaries = []

                    for i, chunk in enumerate(chunks):
                        # Timer Update Logic
                        current_time = time.time()
                        elapsed = int(current_time - overall_start_time)
                        status_text.caption(f"Analyzing Chunk {i+1}/{total_chunks} | Time: {elapsed}s")
                        
                        msgs = [
                            {'role': 'system', 'content': SYSTEM_PROMPT},
                            {'role': 'user', 'content': f"Analyze this section. Summarize key legal points in English:\n\n{chunk}"}
                        ]
                        summary = get_ollama_response(msgs)
                        partial_summaries.append(summary)
                        progress_bar.progress((i + 1) / total_chunks)
                    
                    # Final Synthesis
                    with st.spinner("Synthesizing Final Report..."):
                        combined_text = "\n".join(partial_summaries)
                        msgs = [
                             {'role': 'system', 'content': "You are an expert summarizer. Output in English."},
                             {'role': 'user', 'content': f"Create a cohesive executive summary from these notes:\n\n{combined_text}"}
                        ]
                        final_response = get_ollama_response(msgs)
                        
                        total_time = int(time.time() - overall_start_time)
                        status_text.empty() 
                        
                        st.session_state.messages.append({"role": "assistant", "content": f"### Executive Summary\n\n*(Processed in {total_time} seconds)*\n\n{final_response}"})
                        st.rerun()

                except Exception as e:
                    st.error(f"Processing Error: {e}")

# --- Right Column: Chat Session ---
with col_main_2:
    st.subheader("CONSULTATION CHAT")
    
    # Display Messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("Type your legal question here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            start_chat_time = time.time()
            with st.spinner("Consulting..."):
                chat_history_for_ai = [{'role': 'system', 'content': SYSTEM_PROMPT}]

                if "document_text" in st.session_state:
                    doc_context = st.session_state.document_text[:15000] 
                    chat_history_for_ai.append({
                        'role': 'user', 
                        'content': f"Context:\n\n{doc_context}\n\n(End Context)"
                    })
                    chat_history_for_ai.append({'role': 'assistant', 'content': "Context received."})

                for msg in st.session_state.messages[-6:]: 
                     chat_history_for_ai.append(msg)

                response = get_ollama_response(chat_history_for_ai)
                
                chat_elapsed = int(time.time() - start_chat_time)
                st.markdown(response)
                st.caption(f"⏱ {chat_elapsed}s")
                st.session_state.messages.append({"role": "assistant", "content": response})