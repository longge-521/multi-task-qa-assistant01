import os
import json
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .load_service import load_service
from src.config import settings

logger = logging.getLogger(__name__)

class ChunkService:
    def __init__(self):
        self.save_dir = settings.CHUNK_DOC_DIR
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def chunk_file(self, filename: str, strategy: str = "recursive", chunk_size: int = 600, overlap: int = 60) -> dict:
        """
        [STEP 2] 文档分块服务
        """
        parsed_state = load_service.load_state(filename)
        if not parsed_state:
            parsed_state = load_service.parse_file(filename)

        text = parsed_state["content"]
        source_meta = parsed_state["metadata"]
        
        chunks = []
        try:
            if strategy == "semantic":
                from langchain_experimental.text_splitter import SemanticChunker
                from src.llm import init_embeddings
                embeddings = init_embeddings()
                text_splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
                docs = text_splitter.create_documents([text])
                chunks = [{"content": doc.page_content, "metadata": {**source_meta, "strategy": "semantic"}} for doc in docs]
            elif strategy == "smart" or strategy == "recursive":
                separators = ["\n\n", "\n", "。", "！", "？", " ", ""] if strategy == "smart" else None
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size, 
                    chunk_overlap=overlap,
                    separators=separators
                )
                split_texts = text_splitter.split_text(text)
                chunks = [{"content": t, "metadata": {**source_meta, "strategy": strategy, "size": chunk_size}} for t in split_texts]
            elif strategy == "page":
                 pages = [p.strip() for p in text.split('\n\n') if p.strip()]
                 chunks = [{"content": p, "metadata": {**source_meta, "strategy": "page"}} for p in pages]
            else:
                 raise ValueError(f"未知策略: {strategy}")

            result = {"chunks": chunks, "filename": filename, "strategy": strategy}
            self.save_state(filename, result)
            return result
        except Exception as e:
            logger.error(f"切块错误 {filename}: {str(e)}")
            raise

    def save_state(self, filename: str, data: dict):
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_state(self, filename: str) -> dict:
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def delete_state(self, filename: str):
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        if os.path.exists(state_file):
            os.remove(state_file)

chunk_service = ChunkService()
