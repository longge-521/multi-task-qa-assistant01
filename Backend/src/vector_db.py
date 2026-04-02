import os
import logging
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .llm import init_embeddings
from .config import settings

logger = logging.getLogger(__name__)

class VectorDBManager:
    def __init__(self):
        self.embeddings = init_embeddings()
        self.db = None
        self.index_path = settings.VECTOR_DB_PATH
        self.knowledge_dir = settings.KNOWLEDGE_BASE_DIR
        
        # Ensure knowledge dir exists
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)
            # Create a placeholder file
            with open(os.path.join(self.knowledge_dir, "welcome.txt"), "w", encoding="utf-8") as f:
                f.write("欢迎使用多任务助手。这是一个本地知识库示例文件。")

    def initialize_db(self, force_rebuild=False):
        """Loads existing index or builds a new one from knowledge/ directory."""
        if os.path.exists(self.index_path) and not force_rebuild:
            logger.info(f"Loading existing vector index from {self.index_path}")
            self.db = FAISS.load_local(self.index_path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            logger.info(f"Building new vector index from {self.knowledge_dir}...")
            # Support .txt and .md
            loader = DirectoryLoader(self.knowledge_dir, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
            documents = loader.load()
            
            if not documents:
                logger.warning("No documents found in knowledge directory to index.")
                return None
                
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            docs = text_splitter.split_documents(documents)
            
            self.db = FAISS.from_documents(docs, self.embeddings)
            self.db.save_local(self.index_path)
            logger.info(f"Successfully indexed {len(docs)} chunks and saved to {self.index_path}")

    def query(self, text: str, k: int = 3):
        if not self.db:
            self.initialize_db()
        
        if not self.db:
            return []
            
        return self.db.similarity_search(text, k=k)

# Global manager instance
vector_manager = VectorDBManager()
