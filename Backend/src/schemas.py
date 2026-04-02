from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query or message")
    session_id: str = Field("default_session", description="Unique identifier for the chat session")
    model: str = Field("deepseek-chat", description="The DeepSeek model to use (chat or reasoner)")

class ToolUsed(BaseModel):
    tool: str
    tool_input: Any

class ChatResponse(BaseModel):
    answer: str = Field(..., description="The AI assistant's final structured answer")
    tools_used: List[ToolUsed] = Field(default_factory=list, description="List of tools invoked during the process")

class ToolMetadata(BaseModel):
    name: str
    label: str
    icon: str
    description: str

class ToolsListResponse(BaseModel):
    tools: List[ToolMetadata]
