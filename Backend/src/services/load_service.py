import os
import json
import logging
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    PyMuPDFLoader,
    UnstructuredMarkdownLoader
)
from src.config import settings

logger = logging.getLogger(__name__)

_ocr_reader = None


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        logger.info("Loading EasyOCR model (first time, will be cached)...")
        _ocr_reader = easyocr.Reader(['ch_sim', 'en'])
    return _ocr_reader


class LoadService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DOC_DIR
        self.save_dir = settings.LOAD_DOC_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.save_dir, exist_ok=True)

    def parse_file(self, filename: str, loader_type: str = "PyMuPDF", use_ocr: bool = False) -> dict:
        """
        [STEP 1] 文档解析服务 — 从 upload_doc/ 读取原文件，解析结果保存到 load_doc/
        """
        file_path = os.path.join(self.upload_dir, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")

        ext = os.path.splitext(filename)[1].lower()
        content = ""
        metadata = {"source": file_path, "filename": filename}

        try:
            if ext in ['.txt', '.md']:
                loader_cls = TextLoader if ext == '.txt' else UnstructuredMarkdownLoader
                loader = loader_cls(file_path, encoding='utf-8')
                docs = loader.load()
                content = "\n\n".join([doc.page_content for doc in docs])
                metadata["parsed_by"] = "Standard"
            elif ext == '.pdf':
                loader = PyMuPDFLoader(file_path) if loader_type == "PyMuPDF" else PyPDFLoader(file_path)
                docs = loader.load()
                content = "\n\n".join([doc.page_content for doc in docs])
                metadata["parsed_by"] = loader_type
            elif ext in ['.xlsx', '.xls']:
                import pandas as pd
                df = pd.read_excel(file_path)
                content = df.to_markdown(index=False)
                metadata["parsed_by"] = "Pandas"
            elif ext in ['.png', '.jpg', '.jpeg'] or use_ocr:
                reader = _get_ocr_reader()
                result = reader.readtext(file_path, detail=0)
                content = "\n".join(result)
                metadata["parsed_by"] = "EasyOCR"
            else:
                raise ValueError(f"不支持的格式: {ext}")

            result = {"content": content, "metadata": metadata}
            self.save_state(filename, result)
            return result
        except Exception as e:
            logger.error(f"解析失败 {filename}: {str(e)}")
            raise

    def save_state(self, filename: str, data: dict):
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_state(self, filename: str):
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def delete_state(self, filename: str):
        state_file = os.path.join(self.save_dir, f"{filename}.json")
        if os.path.exists(state_file):
            os.remove(state_file)

load_service = LoadService()
