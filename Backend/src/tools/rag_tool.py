from langchain_core.tools import tool
import os
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

        # Build response with citation markers
        response_parts = ["在本地知识库中为您找到以下相关参考资料："]

        for i, doc in enumerate(results, 1):
            source = doc.metadata.get('source', '未知')
            filename = os.path.basename(source) if source != '未知' else '未知文件'
            # Add citation marker [1], [2], etc.
            response_parts.append(f"\n[来源{i}: {filename}]\n{doc.page_content}")

        # Also include raw source information for frontend parsing
        # Format: [CITATION:filename:chunk_index]
        citation_info = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get('source', '')
            if source:
                filename = os.path.basename(source)
                # Extract chunk index from metadata if available
                chunk_index = doc.metadata.get('chunk_index', i)
                citation_info.append(f"[CITATION:{filename}:{chunk_index}]")

        full_response = "".join(response_parts)

        # Append citation markers at the end for frontend to parse
        if citation_info:
            full_response += "\n\n" + " ".join(citation_info)

        return full_response

    except Exception as e:
        logger.error(f"Error in 'search_local_knowledge' tool: {str(e)}")
        return f"查询本地知识库时发生错误: {str(e)}"
