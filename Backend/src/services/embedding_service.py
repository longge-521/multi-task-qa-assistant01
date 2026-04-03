import os
import json
import logging
from datetime import datetime
from src.config import settings
from src.llm import init_embeddings
from .chunk_service import chunk_service

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.save_dir = settings.EMBEDDING_DOC_DIR
        os.makedirs(self.save_dir, exist_ok=True)

    def compute_embeddings(
        self,
        filename: str,
        provider: str = "HuggingFace",
        model_name: str = "BAAI/bge-m3",
        embedding_mode: str = "dense",
        vector_dimension: int = None
    ) -> dict:
        """
        [STEP 3] 向量化服务 — 读取 chunk_doc 的分块数据，计算 embedding 向量，存储到 embedding_doc (JSON)
        """
        chunk_state = chunk_service.load_state(filename)
        if not chunk_state:
            raise ValueError(f"找不到文件 {filename} 的分块数据，请先执行切块步骤。")

        mode = (embedding_mode or "dense").lower()
        if mode not in {"dense", "sparse", "hybrid"}:
            raise ValueError("embedding_mode 必须是 dense / sparse / hybrid")

        chunks = chunk_state["chunks"]
        texts = [c["content"] for c in chunks]

        logger.info(
            f"Computing embeddings for {filename}: {len(texts)} chunks, "
            f"mode={mode}, model={model_name}, dim={vector_dimension}"
        )

        vectors = []
        if mode in {"dense", "hybrid"}:
            embeddings_model = init_embeddings(
                provider=provider,
                model_name=model_name,
                vector_dimension=vector_dimension
            )
            vectors = embeddings_model.embed_documents(texts)

        dimension = len(vectors[0]) if vectors else 0
        if vector_dimension and dimension and vector_dimension != dimension:
            raise ValueError(
                f"指定向量维度 {vector_dimension} 与模型实际维度 {dimension} 不一致。"
            )

        logger.info(f"Embedding complete: {len(vectors)} vectors, dimension={dimension}")

        result = {
            "filename": filename,
            "chunked_doc_name": f"{filename}.json",
            "created_at": datetime.now().isoformat(),
            "embedding_mode": mode,
            "embedding_provider": provider,
            "embedding_model": model_name,
            "requested_vector_dimension": vector_dimension,
            "vector_dimension": dimension,
            "embeddings": []
        }

        for i, chunk in enumerate(chunks):
            item = {
                "chunk_index": i,
                "content": chunk["content"],
                "metadata": chunk["metadata"]
            }
            if vectors:
                item["embedding"] = vectors[i]
            result["embeddings"].append(item)

        self._save_state(filename, result)

        return {
            "status": "success",
            "mode": mode,
            "count": len(result["embeddings"]),
            "dimension": dimension,
            "provider": provider,
            "model_name": model_name
        }

    def _save_state(self, filename: str, data: dict):
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_state(self, filename: str) -> dict:
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def load_vectors(self, filename: str) -> list:
        """从 JSON 中提取向量列表，供 index_service 使用"""
        state = self.load_state(filename)
        if not state or "embeddings" not in state:
            return None
        vectors = [item.get("embedding") for item in state["embeddings"] if "embedding" in item]
        return vectors if vectors else None

    def delete_state(self, filename: str):
        for ext in ['.json', '.pkl']:
            path = os.path.join(self.save_dir, f"{filename}{ext}")
            if os.path.exists(path):
                os.remove(path)


embedding_service = EmbeddingService()
