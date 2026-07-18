import os
import json
import time
import shutil
import pandas as pd
import base64
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Import processing logic from backend/processor.py
from backend.processor import LocalVectorStore, DocumentProcessor, generate_groq_answer, UPLOAD_DIR

app = FastAPI(title="AI Document Intelligence Agent API")

# Configure CORS for Next.js app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Next.js origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REGISTRY_FILE = os.path.join(UPLOAD_DIR, "registry.json")
vector_store = LocalVectorStore()

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_registry(registry):
    try:
        with open(REGISTRY_FILE, "w") as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        print(f"Error saving registry: {e}")

class QueryRequest(BaseModel):
    query: str
    groq_key: Optional[str] = None

@app.get("/api/documents")
def get_documents():
    return load_registry()

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    groq_key: Optional[str] = Form(None)
):
    try:
        filename = file.filename
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Save file to upload directory
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        ext = os.path.splitext(filename)[1].lower()
        file_type = ext.replace(".", "").upper()
        
        # Parse and process document
        result = DocumentProcessor.process_file(file_path, file_type, api_key=groq_key)
        
        # Store to ChromaDB vector store
        file_id = f"doc_{int(time.time())}_{filename.replace('.', '_')}"
        vector_store.add_document(
            file_id=file_id,
            content=result["content"],
            doc_metadata=result["metadata"]
        )
        
        # Save to registry
        registry = load_registry()
        # Remove any existing entry with the same filename to prevent duplication
        registry = [r for r in registry if r["filename"] != filename]
        
        new_doc = {
            "file_id": file_id,
            "filename": filename,
            "type": file_type,
            "path": file_path,
            "content_preview": result["content"][:2000],
            "size": os.path.getsize(file_path)
        }
        registry.append(new_doc)
        save_registry(registry)
        
        return new_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.delete("/api/documents/{file_id}")
def delete_document(file_id: str):
    registry = load_registry()
    doc_to_delete = next((r for r in registry if r["file_id"] == file_id), None)
    
    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Document not found in registry")
        
    filename = doc_to_delete["filename"]
    path = doc_to_delete["path"]
    
    # 1. Delete from ChromaDB
    vector_store.delete_document(filename)
    
    # 2. Delete from local disk
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error removing local file: {e}")
        
    # 3. Update registry
    registry = [r for r in registry if r["file_id"] != file_id]
    save_registry(registry)
    
    return {"message": f"Successfully deleted and de-indexed {filename}"}

@app.post("/api/query")
def run_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty")
        
    # Search ChromaDB
    search_results = vector_store.search(request.query, n_results=5)
    
    if not search_results:
        return {
            "answer": "No relevant document chunks found in the database. Please make sure files are uploaded and indexed.",
            "sources": []
        }
        
    # Synthesize answer using Groq
    if request.groq_key:
        answer = generate_groq_answer(request.groq_key, request.query, search_results)
    else:
        top_match = search_results[0]
        answer = (
            f"**[Offline Mode] Best Match from {top_match['metadata']['filename']}:**\n\n"
            f"{top_match['document']}\n\n"
            f"*Configure a Groq API Key to synthesize conversational summaries.*"
        )
        
    return {
        "answer": answer,
        "sources": [
            {
                "filename": r["metadata"]["filename"],
                "chunk_index": r["metadata"].get("chunk_index", 0),
                "document": r["document"],
                "score": r["score"]
            }
            for r in search_results
        ]
    }

@app.get("/api/preview/{file_id}")
def preview_document(file_id: str):
    registry = load_registry()
    doc = next((r for r in registry if r["file_id"] == file_id), None)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    path = doc["path"]
    ext = os.path.splitext(doc["filename"])[1].lower()
    
    # If Excel sheet, parse and return structured sheets JSON for rendering a visual grid
    if ext in [".xls", ".xlsx"]:
        try:
            xls = pd.ExcelFile(path)
            sheets_data = {}
            for name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=name)
                # Fill NaN for JSON serialization
                df = df.fillna("")
                sheets_data[name] = {
                    "columns": list(df.columns.astype(str)),
                    "rows": df.to_dict(orient="records")
                }
            return {"type": "excel", "sheets": sheets_data}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error parsing Excel: {str(e)}")
            
    # If image, return raw base64 data for inline preview
    elif ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        try:
            with open(path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
            return {"type": "image", "base64": encoded, "format": ext.replace(".", "")}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading image: {str(e)}")
            
    # For others (txt, pdf, docx), return preview text
    else:
        return {"type": "text", "content": doc["content_preview"]}

@app.get("/api/download/{file_id}")
def download_document(file_id: str):
    registry = load_registry()
    doc = next((r for r in registry if r["file_id"] == file_id), None)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not os.path.exists(doc["path"]):
        raise HTTPException(status_code=404, detail="Physical file does not exist on disk")
        
    return FileResponse(
        path=doc["path"],
        filename=doc["filename"],
        media_type="application/octet-stream"
    )

@app.post("/api/reset")
def reset_database():
    try:
        vector_store.reset_db()
        # Clean local folder
        if os.path.exists(UPLOAD_DIR):
            for f in os.listdir(UPLOAD_DIR):
                if f != "registry.json":
                    try:
                        file_path = os.path.join(UPLOAD_DIR, f)
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        else:
                            os.remove(file_path)
                    except Exception:
                        pass
        save_registry([])
        return {"message": "Database and upload registry successfully cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")
