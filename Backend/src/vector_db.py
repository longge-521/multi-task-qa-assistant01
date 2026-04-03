import os
import json
import logging
from typing import List, Dict, Any
from src.config import settings

from .services.load_service import load_service
from .services.chunk_service import chunk_service
from .services.embedding_service import embedding_service
from .services.index_service import index_service

logger = logging.getLogger(__name__)


class VectorDBManager:
    """
    协调各个子服务并管理统一的文档元数据。
    """
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DOC_DIR
        self.metadata_path = settings.METADATA_PATH
        self.metadata = self._load_metadata()
        if "files" not in self.metadata:
            self.metadata = {"files": {}, "total_chunks": 0}
            self._save_metadata(self.metadata)

    def initialize_db(self):
        """启动时初始化向量数据库，确保目录和元数据就绪。"""
        os.makedirs(self.upload_dir, exist_ok=True)
        self.metadata = self._load_metadata()
        if "files" not in self.metadata:
            self.metadata = {"files": {}, "total_chunks": 0}
            self._save_metadata(self.metadata)
        logger.info("Vector DB initialized successfully")

    def parse_document(self, filename: str, loader_type: str = "PyMuPDF", use_ocr: bool = False):
        result = load_service.parse_file(filename, loader_type, use_ocr)
        self._update_file_status(filename, stage="parsed")
        return result

    def chunk_document(self, filename: str, strategy: str = "recursive", chunk_size: int = 600, overlap: int = 60):
        result = chunk_service.chunk_file(filename, strategy, chunk_size, overlap)
        self._update_file_status(filename, stage="chunked")
        return result

    def create_embeddings(
        self,
        filename: str,
        provider: str = "HuggingFace",
        model_name: str = "BAAI/bge-m3",
        embedding_mode: str = "dense",
        vector_dimension: int = None
    ):
        result = embedding_service.compute_embeddings(
            filename=filename,
            provider=provider,
            model_name=model_name,
            embedding_mode=embedding_mode,
            vector_dimension=vector_dimension
        )
        self._update_file_status(filename, stage="embedding_ready")
        return result

    def add_to_index(self, filename: str, db_type: str = "FAISS", db_name: str = "default"):
        result = index_service.index_file(filename, db_type, db_name)
        self._update_file_status(filename, stage="indexed", status="synced", db_info={"type": db_type, "name": db_name})
        return result

    def delete_document(self, filename: str):
        try:
            src_path = os.path.join(self.upload_dir, filename)
            if os.path.exists(src_path):
                os.remove(src_path)

            load_service.delete_state(filename)
            chunk_service.delete_state(filename)
            embedding_service.delete_state(filename)

            if filename in self.metadata["files"]:
                db_info = self.metadata["files"][filename].get("db_info", {})
                del self.metadata["files"][filename]
                self._save_metadata(self.metadata)
                db_type = db_info.get("type", "FAISS")
                db_name = db_info.get("name", "default")
                index_service.rebuild_index(db_type=db_type, db_name=db_name)
            else:
                self._save_metadata(self.metadata)

            return {"status": "success", "message": f"Deleted {filename}"}
        except Exception as e:
            logger.error(f"Error deleting {filename}: {str(e)}")
            raise

    def get_files_info(self, stage_filter: str = None):
        all_files = []
        try:
            os.makedirs(self.upload_dir, exist_ok=True)
            self.metadata = self._load_metadata()
            physical_files = [
                f for f in os.listdir(self.upload_dir)
                if os.path.isfile(os.path.join(self.upload_dir, f)) and not f.startswith('_')
            ]

            for filename in physical_files:
                file_path = os.path.join(self.upload_dir, filename)
                info = self.metadata["files"].get(filename, {
                    "filename": filename,
                    "path": file_path,
                    "status": "raw",
                    "stage": "raw",
                    "size": os.path.getsize(file_path)
                })

                if "size" not in info or info["size"] == 0:
                    info["size"] = os.path.getsize(file_path)

                if info.get("status") != "synced":
                    if embedding_service.load_state(filename):
                        info["stage"] = "embedding_ready"
                    elif chunk_service.load_state(filename):
                        info["stage"] = "chunked"
                    elif load_service.load_state(filename):
                        info["stage"] = "parsed"
                    else:
                        info["stage"] = "raw"

                if not stage_filter or info["stage"] == stage_filter:
                    all_files.append(info)
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
        return all_files

    def _update_file_status(self, filename: str, **kwargs):
        file_path = os.path.join(self.upload_dir, filename)
        if filename not in self.metadata["files"]:
            self.metadata["files"][filename] = {
                "filename": filename,
                "path": file_path,
                "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
        self.metadata["files"][filename].update(kwargs)
        self._save_metadata(self.metadata)

    def _load_metadata(self):
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except (json.JSONDecodeError, ValueError):
                    logger.warning(f"Metadata file corrupted, resetting: {self.metadata_path}")
                    return {}
        return {}

    def _save_metadata(self, metadata):
        os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 保留旧名称兼容 app.py 中的调用
    def load_metadata(self):
        return self._load_metadata()

    def save_metadata(self, metadata):
        self._save_metadata(metadata)

    def _load_processing_state(self, filename: str, step: str):
        if step == "parsed":
            return load_service.load_state(filename)
        if step == "chunked":
            return chunk_service.load_state(filename)
        if step == "embedding":
            return embedding_service.load_state(filename)
        return None

    def get_file_chunks(self, filename: str):
        state = chunk_service.load_state(filename)
        return state["chunks"] if state else []

    def process_pipeline(self, filename: str, loader_type: str = "PyMuPDF", use_ocr: bool = False,
                         strategy: str = "recursive", chunk_size: int = 600, overlap: int = 60,
                         embedding_provider: str = "HuggingFace", embedding_model: str = "BAAI/bge-m3",
                         embedding_mode: str = "dense", vector_dimension: int = None,
                         db_type: str = "FAISS", db_name: str = "default"):
        """One-click pipeline: parse -> chunk -> embedding -> index"""
        steps_done = []
        try:
            self.parse_document(filename, loader_type, use_ocr)
            steps_done.append("parsed")

            self.chunk_document(filename, strategy, chunk_size, overlap)
            steps_done.append("chunked")

            self.create_embeddings(
                filename=filename,
                provider=embedding_provider,
                model_name=embedding_model,
                embedding_mode=embedding_mode,
                vector_dimension=vector_dimension
            )
            steps_done.append("embedding_ready")

            result = self.add_to_index(filename, db_type, db_name)
            steps_done.append("indexed")

            return {"status": "success", "steps_completed": steps_done, "index_result": result}
        except Exception as e:
            logger.error(f"Pipeline error at step after {steps_done}: {str(e)}")
            return {"status": "partial", "steps_completed": steps_done, "error": str(e)}

    def query(self, text: str, k: int = 3, db_type: str = "FAISS", db_name: str = "default"):
        return index_service.query(text, k, db_type, db_name)

    def search(
        self,
        text: str,
        k: int = 5,
        db_type: str = "FAISS",
        db_name: str = "default",
        filenames=None,
        score_threshold: float = None,
        hybrid_alpha: float = 0.7
    ):
        return index_service.search(
            text=text,
            k=k,
            db_type=db_type,
            db_name=db_name,
            filenames=filenames,
            score_threshold=score_threshold,
            hybrid_alpha=hybrid_alpha
        )


vector_manager = VectorDBManager()
