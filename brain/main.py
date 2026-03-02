from fastapi import FastAPI, UploadFile, File, Form
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os
import shutil

app = FastAPI()

# --- CONFIGURATION ---
# Important: This uses a DIFFERENT folder than the free version 
# to avoid mixing OpenAI math with local math.
UPLOAD_DIR = "uploads"
DB_DIR = "db_vault" 
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 1. PAID EMBEDDINGS (Requires OPENAI_API_KEY in your system environment)
embeddings = OpenAIEmbeddings()

# 2. PAID LLM (GPT-4o)
llm = ChatOpenAI(model="gpt-4o", temperature=0)

@app.post("/ingest")
async def ingest_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Save physical file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    
    # Store in Chroma (Paid Vault)
    Chroma.from_documents(
        documents=splits, 
        embedding=embeddings, 
        persist_directory=DB_DIR
    )
    
    return {"status": "Success", "filename": file.filename}

@app.post("/ask")
async def ask_question(question: str = Form(...)):
    # Load the Paid Vault
    vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever()

    template = """Answer the question based ONLY on the following context:
    {context}

    Question: {question}
    
    Helpful Answer:"""
    
    prompt = ChatPromptTemplate.from_template(template)

    # RAG Chain using the Pipe (|) operator
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    try:
        response = rag_chain.invoke(question)
        return {"answer": response}
    except Exception as e:
        return {"answer": f"OpenAI Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print("--- AiVault PAID Brain Starting (OpenAI) ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)