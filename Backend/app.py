import uvicorn
import os
import shutil
import json
import logging
import asyncio
from pathlib import PurePosixPath
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import settings
from src.schemas import ChatRequest, ChatResponse, ToolsListResponse, ToolMetadata
from src.agent import get_agent_response, stream_agent_response, get_agent_tools
from src.vector_db import vector_manager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Multi-Task QA Assistant API",
    description="FastAPI powered agent with tool-calling capabilities",
    version="2.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class ProcessConfigRequest(BaseModel):
    # Step 1: Load
    loader_type: str = "PyMuPDF"
    use_ocr: bool = False
    
    # Step 2: Chunk
    strategy: str = "recursive"
    chunk_size: int = 600
    chunk_overlap: int = 60
    
    # Step 3: Embedding
    embedding_provider: str = "HuggingFace"
    embedding_model: str = "BAAI/bge-m3"
    embedding_mode: str = "dense"  # dense | sparse | hybrid
    vector_dimension: Optional[int] = None
    
    # Step 4: Index
    db_type: str = "FAISS"
    db_name: str = "default"


class SearchRequest(BaseModel):
    query: str
    k: int = 5
    db_type: str = "FAISS"
    db_name: str = "default"
    filenames: Optional[List[str]] = None
    score_threshold: Optional[float] = None
    hybrid_alpha: float = 0.7

# --- Endpoints ---

@app.get("/api/tools", response_model=ToolsListResponse)
async def get_tools():
    tool_labels = {
        "get_weather": "实时天气",
        "search_news": "新闻搜索",
        "get_stock":   "A股涨停",
        "search_local_knowledge": "文档知识库",
    }
    tool_icons = {
        "get_weather": "weather",
        "search_news": "news",
        "get_stock":   "stock",
        "search_local_knowledge": "knowledge",
    }
    tools_info = []
    for tool in get_agent_tools:
        raw_desc = tool.description or ""
        clean_desc = raw_desc.split(" - ", 1)[1].strip() if " - " in raw_desc else raw_desc.strip()
        tools_info.append(ToolMetadata(
            name=tool.name,
            label=tool_labels.get(tool.name, tool.name),
            icon=tool_icons.get(tool.name, "default"),
            description=clean_desc
        ))
    return ToolsListResponse(tools=tools_info)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await get_agent_response(request.session_id, request.query, request.model)
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_agent_response(request.session_id, request.query, request.model),
        media_type="text/event-stream"
    )

# --- Knowledge Base Management ---

@app.get("/api/knowledge/files")
async def list_files(stage: str = None):
    try:
        return vector_manager.get_files_info(stage_filter=stage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/stages/stats")
async def get_stage_stats():
    try:
        files = vector_manager.get_files_info()
        stats = {"raw": 0, "parsed": 0, "chunked": 0, "indexed": 0}
        for f in files:
            stage = f.get("stage", "raw")
            if stage == "embedding_ready": stage = "chunked" # Group for stats
            if stage in stats: stats[stage] += 1
        return stats
    except Exception:
        return {"raw": 0, "parsed": 0, "chunked": 0, "indexed": 0}

@app.get("/api/knowledge/files/{filename}/chunks")
async def get_chunks(filename: str):
    try:
        chunks = vector_manager.get_file_chunks(filename)
        return {"filename": filename, "chunks": chunks, "count": len(chunks)}
    except Exception as e:
        return {"filename": filename, "chunks": [], "count": 0}


@app.post("/api/knowledge/search")
async def search_knowledge(req: SearchRequest):
    try:
        results = await asyncio.to_thread(
            vector_manager.search,
            text=req.query,
            k=req.k,
            db_type=req.db_type,
            db_name=req.db_name,
            filenames=req.filenames,
            score_threshold=req.score_threshold,
            hybrid_alpha=req.hybrid_alpha
        )
        return {
            "query": req.query,
            "total": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/knowledge/files/{filename}")
async def delete_file(filename: str):
    try:
        return vector_manager.delete_document(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/process/state/{filename}/{step}")
async def get_process_state(filename: str, step: str):
    state = vector_manager._load_processing_state(filename, step)
    if not state: return {"error": "State not found"}
    return state

@app.get("/api/knowledge/embedding/preview/{filename}")
async def get_embedding_preview(filename: str):
    """返回向量化摘要信息（不含完整向量，避免传输过大）"""
    from src.services.embedding_service import embedding_service
    state = embedding_service.load_state(filename)
    if not state:
        return {"error": "Embedding data not found"}
    embeddings_list = state.get("embeddings", [])
    preview_items = []
    for item in embeddings_list:
        vec = item.get("embedding", [])
        preview_items.append({
            "chunk_index": item.get("chunk_index"),
            "content": item.get("content", "")[:200],
            "dimension": len(vec),
            "vector_sample": vec[:8] if vec else [],
        })
    return {
        "filename": state.get("filename"),
        "embedding_mode": state.get("embedding_mode", "dense"),
        "embedding_provider": state.get("embedding_provider"),
        "embedding_model": state.get("embedding_model"),
        "requested_vector_dimension": state.get("requested_vector_dimension"),
        "vector_dimension": state.get("vector_dimension"),
        "count": len(embeddings_list),
        "created_at": state.get("created_at"),
        "items": preview_items
    }

# --- Modular Pipeline Atomic Steps ---

@app.post("/api/knowledge/parse/{filename}")
async def parse_doc(filename: str, config: ProcessConfigRequest):
    try:
        result = await asyncio.to_thread(
            vector_manager.parse_document, filename,
            loader_type=config.loader_type, use_ocr=config.use_ocr
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/chunk/{filename}")
async def chunk_doc(filename: str, config: ProcessConfigRequest):
    try:
        result = await asyncio.to_thread(
            vector_manager.chunk_document, filename,
            strategy=config.strategy, chunk_size=config.chunk_size, overlap=config.chunk_overlap
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/embedding/{filename}")
async def config_embedding(filename: str, config: ProcessConfigRequest):
    try:
        result = await asyncio.to_thread(
            vector_manager.create_embeddings, filename,
            provider=config.embedding_provider,
            model_name=config.embedding_model,
            embedding_mode=config.embedding_mode,
            vector_dimension=config.vector_dimension
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/index/{filename}")
async def index_doc(filename: str, config: ProcessConfigRequest):
    try:
        result = await asyncio.to_thread(
            vector_manager.add_to_index, filename,
            db_type=config.db_type, db_name=config.db_name
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/pipeline/{filename}")
async def pipeline_doc(filename: str, config: ProcessConfigRequest):
    try:
        result = await asyncio.to_thread(
            vector_manager.process_pipeline, filename,
            loader_type=config.loader_type, use_ocr=config.use_ocr,
            strategy=config.strategy, chunk_size=config.chunk_size, overlap=config.chunk_overlap,
            embedding_provider=config.embedding_provider, embedding_model=config.embedding_model,
            embedding_mode=config.embedding_mode, vector_dimension=config.vector_dimension,
            db_type=config.db_type, db_name=config.db_name
        )
        if result["status"] == "partial":
            raise HTTPException(status_code=500, detail=result["error"])
        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        safe_filename = PurePosixPath(file.filename).name
        if not safe_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        allowed_extensions = {'.txt', '.md', '.pdf', '.xlsx', '.xls', '.png', '.jpg', '.jpeg'}
        file_ext = os.path.splitext(safe_filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {file_ext}")

        upload_dir = settings.UPLOAD_DOC_DIR
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"message": "Upload successful", "filename": safe_filename, "size": os.path.getsize(file_path)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
