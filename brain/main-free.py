from fastapi import FastAPI, UploadFile, File, Form
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os
import shutil

app = FastAPI()

# --- CONFIGURATION ---
UPLOAD_DIR = "uploads"
DB_DIR = "db_vault_free" # Separate DB for local models
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 1. FREE EMBEDDINGS (HuggingFace runs on your CPU/GPU)
# This model is small (~400MB) and very fast.
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. FREE LLM (Ollama)
# We use llama3.2:1b because it's only 1.3GB and very fast.
llm = ChatOllama(model="llama3.2:1b", temperature=0)

@app.post("/ingest")
async def ingest_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Load and Split
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    
    # Store in Local Chroma
    Chroma.from_documents(
        documents=splits, 
        embedding=embeddings, 
        persist_directory=DB_DIR
    )
    return {"status": "Success", "message": f"Indexed {file.filename} locally."}

@app.post("/ask")
async def ask_question(question: str = Form(...)):
    vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    
    # Increase k from 3 to 5 (gives the AI more context to find notes)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    # Updated Template to force a response
    template = """You are a helpful assistant. Use the following pieces of context to answer the question. 
    If you don't find the specific answer, summarize the most important points for the user.

    Context: {context}
    Question: {question}
    
    Helpful Answer (If no info found, say 'I couldn't find specific notes, but here is a summary'):"""
    
    prompt = ChatPromptTemplate.from_template(template)

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    try:
        response = rag_chain.invoke(question)
        # Ensure we ALWAYS return the 'answer' key, even if the AI is silent
        return {"answer": response or "The AI was unable to generate notes for this specific query."}
    except Exception as e:
        return {"answer": f"Brain Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print("--- AiVault Free Brain Starting ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)