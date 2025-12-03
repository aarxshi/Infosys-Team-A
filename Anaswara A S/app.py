import streamlit as st
import random
import time
import requests
import json
import io 

# Required for document processing
from pypdf import PdfReader 
from langchain_text_splitters import RecursiveCharacterTextSplitter 

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="Chatbot", page_icon="🤖", layout="wide")

# --- File Processing and Chunking ---

def extract_text_from_uploaded_file(uploaded_file):
    """Extracts text from PDF or plain text files."""
    file_type = uploaded_file.type
    file_content = uploaded_file.getvalue()
    text = ""

    # Handle PDF files
    if 'pdf' in file_type:
        try:
            pdf_reader = PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                text += page.extract_text() if page.extract_text() else ""
        except Exception as e:
            st.error(f"Error extracting text from PDF: {e}")
            return None
    
    # Handle plain text files
    elif 'text' in file_type or 'json' in file_type:
        try:
            text = file_content.decode("utf-8")
        except Exception as e:
            st.error(f"Error decoding text file: {e}")
            return None
            
    else:
        st.warning(f"Unsupported file type: {file_type}. Only PDF and text files are supported.")
        return None
        
    return text

def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    """Chunks the text using a RecursiveCharacterTextSplitter."""
    if not text:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    chunks = text_splitter.split_text(text)
    
    
    json_chunks = [{"chunk_id": i, "content": chunk} for i, chunk in enumerate(chunks)]
    
    return json_chunks

# ---------------- Helper: call Ollama (Streaming Version) ----------------

def get_ollama_streaming_response(prompt, context_chunks=None, model_name="llama3.1:8b", timeout=120):
    """
    Call local Ollama server and yield the model's text response chunks using streaming.
    Takes an optional list of context_chunks (JSON structure).
    """
    url = "http://localhost:11434/api/generate"
    
    # Base system prompt
    system_prompt = "You are a helpful, concise, and friendly assistant. Always respond in English. When providing code, always wrap it in a markdown code block."
    
    # 🌟 RAG Integration: Inject context into the system prompt 🌟
    if context_chunks:
        context_text = "\n---\n".join([c['content'] for c in context_chunks])
        
        context_instruction = f"\n\n---CONTEXT---\n\nUse the following document text to answer the user's question. If the answer is not found in the context, state that explicitly. \n\nDOCUMENT TEXT: {context_text}"
        system_prompt += context_instruction

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True,  
        "system": system_prompt
    }
    
    
    try:
        with requests.post(url, json=payload, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            
            for line in resp.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        response_chunk = data.get("response", "")
                        yield response_chunk
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
                        
    except Exception as e:
        yield f"[error: Cannot connect to Ollama server or request failed: {e}]"


# ---------------- SESSION STATE SETUP ----------------
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": [{"role": "assistant", "content": "Let's start chatting! 👇"}]}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"
if "chat_count" not in st.session_state:
    st.session_state.chat_count = 1
# Store chunks in session state 
if "current_file_chunks" not in st.session_state:
    st.session_state.current_file_chunks = None


# ---------------- SIDEBAR ----------------
st.sidebar.title("💬 Chat History")

# New Chat and Chat List sections 
if st.sidebar.button("🆕 New Chat"):
    st.session_state.chat_count += 1
    new_chat_name = f"Chat {st.session_state.chat_count}"
    st.session_state.chats[new_chat_name] = [{"role": "assistant", "content": "Let's start chatting! 👇"}]
    st.session_state.current_chat = new_chat_name
    st.session_state.current_file_chunks = None # Clear context on new chat

chat_names = list(st.session_state.chats.keys())
selected_chat = st.sidebar.radio("Your Chats", chat_names, index=chat_names.index(st.session_state.current_chat))
st.session_state.current_chat = selected_chat

# --- File Upload Section ---
st.sidebar.markdown("---")
st.sidebar.subheader("📎 Upload a File")
uploaded_file = st.sidebar.file_uploader("Choose a file", type=["pdf", "txt", "json"]) # Restrict types

# File Preview (like before)
if uploaded_file is not None:
    st.sidebar.write("### 📄 File Preview")
    st.sidebar.info(f"**Filename:** {uploaded_file.name}\n\n**Type:** {uploaded_file.type}")

    # Attach and Process Logic 
    if st.sidebar.button("📎 Attach and Process File"):
        with st.spinner(f"Processing '{uploaded_file.name}'..."):
            # 1. Extract Text
            raw_text = extract_text_from_uploaded_file(uploaded_file)
            
            if raw_text:
                # 2. Chunk Text
                file_chunks = chunk_text(raw_text)
                
                # 3. Store in Session State
                st.session_state.current_file_chunks = file_chunks
                
                # 4. Add message to chat
                file_message = f"✅ File successfully processed! Found **{len(file_chunks)}** chunks. You can now ask questions about **{uploaded_file.name}**."
                st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": file_message})
                st.session_state.current_file_name = uploaded_file.name # Store name for display
                st.success("File processing complete!")
                st.rerun() # Rerun to display the success message immediately

# Display current context status
if st.session_state.current_file_chunks:
    st.sidebar.success(f"Context active: **{st.session_state.current_file_name}** ({len(st.session_state.current_file_chunks)} chunks)")
else:
    st.sidebar.info("No file context currently active.")


st.sidebar.markdown("---")

# --- Clear Current Chat ---
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.chats[st.session_state.current_chat] = [{"role": "assistant", "content": "Let's start chatting! 👇"}]
    st.session_state.current_file_chunks = None # Clear context on chat clear

# ---------------- MAIN CHAT AREA ----------------
st.title("🤖 Chatbot")

# Get messages for current chat
messages = st.session_state.chats[st.session_state.current_chat]

# Display chat messages
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- CHAT INPUT ----------------
if prompt := st.chat_input("Type your message..."):
    # Add user message
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Streaming display logic
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Pass the chunks to the streaming function 
        for chunk in get_ollama_streaming_response(
            prompt, 
            context_chunks=st.session_state.current_file_chunks, 
            model_name="llama3.1:8b", 
            timeout=120
        ):
            # Check for error first
            if chunk.startswith("[error:"):
                full_response = chunk
                break

            full_response += chunk
            
            # Display the full response generated so far with a cursor effect
            message_placeholder.markdown(full_response + "▌") 
            
        # Display the final, complete response without the cursor
        message_placeholder.markdown(full_response)

    messages.append({"role": "assistant", "content": full_response})

# Save chat
st.session_state.chats[st.session_state.current_chat] = messages