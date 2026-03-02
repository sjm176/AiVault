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
    # Connect to the local vector store
    vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # Modern 2026 RAG Prompt
    template = """Answer the question based ONLY on the following context:
    {context}

    Question: {question}
    
    Helpful Answer:"""
    prompt = ChatPromptTemplate.from_template(template)

    # LCEL Chain (No 'langchain.chains' needed)
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    response = rag_chain.invoke(question)
    return {"answer": response}

if __name__ == "__main__":
    import uvicorn
    print("--- AiVault Free Brain Starting ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)