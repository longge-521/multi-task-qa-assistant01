import logging
from .weather import get_weather
from .news import search_news
from .stock import get_stock
from .rag_tool import search_local_knowledge
from src.vector_db import vector_manager

logger = logging.getLogger(__name__)

# Trigger initial indexing on tool module load
try:
    logger.info("Initializing vector DB for RAG tool indexing...")
    vector_manager.initialize_db()
except Exception as e:
    logger.error(f"Failed to initialize vector DB: {str(e)}")

# Define all available tools for the agent
get_agent_tools = [
    get_weather,
    search_news,
    get_stock,
    search_local_knowledge
]
