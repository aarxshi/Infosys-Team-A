Local Document Chatbot with Chunking (Ollama + Streamlit)

A project by Aditya Singh

This is a local AI-powered chatbot built using Streamlit and Ollama.
It allows users to:

Upload PDF, TXT, and CSV files

Extract text from the document

Convert it into JSON

Apply chunking to handle large documents

Feed the chunks into a local LLM (phi3 / gemma2 / mistral / llama3)

Chat and ask questions based on the uploaded file

Features
  Document Upload

Supports:

PDF

TXT

CSV

  Automatic Text Extraction

All text is extracted using:

PyPDF2 for PDF

Standard Python I/O for TXT

Pandas for CSV

  JSON Storage

The document is stored as:

{
  "filename": "file.pdf",
  "type": "application/pdf",
  "content": "full extracted text..."
}

  Chunking

The extracted text is split into multiple overlapping chunks, improving model accuracy.

Example chunk format:

{
  "id": 0,
  "text": "portion of document here..."
}

  Local LLM Integration

Works with local Ollama models such as:

phi3:latest (recommended)

gemma2:2b

mistral:latest

llama3.1:latest

  Chat Interface

Built with Streamlit’s chat UI (st.chat_message)
User can ask questions related to the uploaded document.

  Project Architecture
Upload File → Extract Text → Store JSON → Chunk Text → Feed Chunks → LLM Answers

  Technologies Used
Technology	Purpose
Python	Core logic
Streamlit	Chat UI
Ollama	Local LLM
PyPDF2	PDF text extraction
Pandas	CSV handling
JSON	Document storage
Chunking Algorithm	Splits large text into manageable parts
  Installation
1 Install dependencies
pip install streamlit PyPDF2 pandas ollama


(or)

python -m pip install streamlit PyPDF2 pandas ollama

2️ Install and run Ollama

Download Ollama from:
  https://ollama.com/download

Start Ollama server:

ollama serve


Pull a lightweight model (recommended):

ollama pull phi3

3️ Run the app
streamlit run chatbot_app.py


or if streamlit command doesn’t work:

python -m streamlit run chatbot_app.py

Project Structure
chatbot-ui/
│
├── chatbot_app.py        # Main application
├── requirements.txt      # Required libraries
├── README.md             # Project documentation
├── .env                  # Optional (no secrets uploaded)
└── uploads/              # (Optional) uploaded files

 How It Works (Step-by-Step)

1️ Upload a document
2️ App extracts the text
3️ Document is saved as JSON
4️ Chunking splits the text into manageable parts
5️ Relevant chunks are passed to the model
6️ User asks a question
7️ The chatbot responds based on document content

  Future Enhancements (Optional)

Add embeddings + vector search (RAG)

Support multiple documents

Support DOCX uploads

Improve UI layout

Add auto-summary after upload

 Author

Aditya Singh
Machine Learning & AI Student
Working with: Python • Streamlit • LLMs • RAG • Machine Learning
