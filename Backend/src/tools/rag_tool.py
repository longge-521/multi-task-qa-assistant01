from langchain_core.tools import tool
import logging
from src.vector_db import vector_manager

logger = logging.getLogger(__name__)

@tool
def search_local_knowledge(query: str) -> str:
    """
    搜索本地知识库中的文档内容。
    当用户询问关于本项目说明、内部资料、或用户上传的文档内容时，请优先使用此工具。
    """
    try:
        logger.info(f"Tool 'search_local_knowledge' called with query: {query}")
        
        # We perform semantic search using the global vector manager
        results = vector_manager.query(query, k=3)
        
        if not results:
            logger.warning(f"No results found in knowledge base for query: {query}")
            return "本地知识库中未找到相关内容。"
        
        combined_text = "\n\n".join([f"[来源: {doc.metadata.get('source', '未知')}]\n{doc.page_content}" for doc in results])
        return f"在本地知识库中为您找到以下相关参考资料：\n\n{combined_text}"
        
    except Exception as e:
        logger.error(f"Error in 'search_local_knowledge' tool: {str(e)}")
        return f"查询本地知识库时发生错误: {str(e)}"
