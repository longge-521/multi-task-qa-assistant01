import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import List

from src.config import settings
from src.schemas import ChatRequest, ChatResponse, ToolsListResponse, ToolMetadata
from src.agent import get_agent_response, get_agent_tools


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
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/tools", response_model=ToolsListResponse)
async def get_tools():
    """
    Returns dynamically the list of all registered agent tools with their metadata.
    """
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
        # Handle different docstring formats
        if " - " in raw_desc:
            clean_desc = raw_desc.split(" - ", 1)[1].strip()
        else:
            clean_desc = raw_desc.strip()

        tools_info.append(ToolMetadata(
            name=tool.name,
            label=tool_labels.get(tool.name, tool.name),
            icon=tool_icons.get(tool.name, "default"),
            description=clean_desc
        ))
    
    return ToolsListResponse(tools=tools_info)

from fastapi.responses import StreamingResponse
from src.agent import get_agent_response, stream_agent_response, get_agent_tools

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint using FastAPI and Pydantic validation (non-streaming).
    """
    logger.info(f"Received query: {request.query} - Model: {request.model}")
    try:
        result = await get_agent_response(
            session_id=request.session_id, 
            query=request.query, 
            model=request.model
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    """
    logger.info(f"Received STREAMING query: {request.query} - Model: {request.model}")
    return StreamingResponse(
        stream_agent_response(request.session_id, request.query, request.model),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    logger.info(f"Starting FastAPI server on {settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        "app:app", 
        host=settings.APP_HOST, 
        port=settings.APP_PORT, 
        reload=settings.DEBUG
    )
