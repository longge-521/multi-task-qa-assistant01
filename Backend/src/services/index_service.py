import os
import re
import math
import json
import shutil
import logging
from langchain_community.vectorstores import FAISS, Chroma
from langchain_core.documents import Document
from src.config import settings
from src.llm import init_embeddings
from .embedding_service import embedding_service

logger = logging.getLogger(__name__)


class IndexService:
    INDEX_META_FILE = "index_meta.json"
    SPARSE_INDEX_FILE = "sparse_index.json"

    def __init__(self):
        self.save_dir = settings.VECTOR_STORE_DIR
        os.makedirs(self.save_dir, exist_ok=True)
        self._db_cache = {}
        self._sparse_cache = {}

    def index_file(self, filename: str, db_type: str = "FAISS", db_name: str = "default") -> dict:
        """
        [STEP 4] 写入向量库 — 读取 embedding_doc 的预计算向量，写入 FAISS/Chroma
        """
        emb_state = embedding_service.load_state(filename)
        if not emb_state or "embeddings" not in emb_state:
            raise ValueError(f"找不到文件 {filename} 的向量化数据，请先执行向量化步骤。")

        chunks = [{"content": e["content"], "metadata": e["metadata"]} for e in emb_state["embeddings"]]
        mode = emb_state.get("embedding_mode", "dense")
        provider = emb_state.get("embedding_provider", "HuggingFace")
        model_name = emb_state.get("embedding_model", "BAAI/bge-m3")
        vector_dimension = emb_state.get("vector_dimension", 0)

        vectors = embedding_service.load_vectors(filename)
        if mode in {"dense", "hybrid"} and not vectors:
            raise ValueError(f"文件 {filename} 的 embedding_mode={mode}，但未找到向量数据。")

        embeddings_fn = None
        if mode in {"dense", "hybrid"}:
            embeddings_fn = init_embeddings(
                provider=provider,
                model_name=model_name,
                vector_dimension=vector_dimension or None
            )

        text_embeddings = list(zip([c["content"] for c in chunks], vectors)) if vectors else []
        metadatas = [c["metadata"] for c in chunks]

        db_path = os.path.join(self.save_dir, db_type, db_name)
        os.makedirs(db_path, exist_ok=True)
        cache_key = (db_type, db_name)

        try:
            if mode in {"dense", "hybrid"}:
                if db_type == "FAISS":
                    if self._has_valid_faiss_index(db_path):
                        vector_db = self._load_faiss(db_path, embeddings_fn)
                        vector_db.add_embeddings(text_embeddings, metadatas=metadatas)
                    elif os.path.exists(os.path.join(db_path, "index.faiss")) or os.path.exists(os.path.join(db_path, "index.pkl")):
                        # Existing FAISS files are incomplete/corrupted, rebuild from scratch.
                        logger.warning(f"Detected broken FAISS index files under {db_path}, recreating index.")
                        self._clear_faiss_files(db_path)
                        vector_db = FAISS.from_embeddings(text_embeddings, embeddings_fn, metadatas=metadatas)
                    else:
                        vector_db = FAISS.from_embeddings(text_embeddings, embeddings_fn, metadatas=metadatas)
                    vector_db.save_local(db_path)
                    self._db_cache[cache_key] = vector_db
                elif db_type == "Chroma":
                    docs = [Document(page_content=c["content"], metadata=c["metadata"]) for c in chunks]
                    vector_db = Chroma.from_documents(docs, embeddings_fn, persist_directory=db_path)
                    vector_db.persist()
                    self._db_cache[cache_key] = vector_db
                else:
                    raise ValueError(f"不支持的向量数据库类型: {db_type}")

            if mode in {"sparse", "hybrid"}:
                sparse_index = self._build_sparse_index(chunks)
                self._save_sparse_index(db_path, sparse_index)
                self._sparse_cache[cache_key] = sparse_index

            self._save_index_meta(db_path, {
                "embedding_mode": mode,
                "embedding_provider": provider,
                "embedding_model": model_name,
                "vector_dimension": vector_dimension,
                "db_type": db_type,
                "db_name": db_name
            })

            return {
                "status": "success",
                "db_path": db_path,
                "chunks": len(chunks),
                "embedding_mode": mode,
                "vector_dimension": vector_dimension
            }
        except Exception as e:
            logger.error(f"写入向量库出错: {str(e)}")
            raise

    def rebuild_index(self, db_type: str = "FAISS", db_name: str = "default"):
        """从所有剩余的 embedding 状态文件重建向量索引（删除文档后调用）。"""
        emb_dir = settings.EMBEDDING_DOC_DIR
        cache_key = (db_type, db_name)
        db_path = os.path.join(self.save_dir, db_type, db_name)
        index_meta = self._load_index_meta(db_path) or {}
        mode = index_meta.get("embedding_mode", "dense")
        provider = index_meta.get("embedding_provider", "HuggingFace")
        model_name = index_meta.get("embedding_model", "BAAI/bge-m3")
        vector_dimension = index_meta.get("vector_dimension")

        all_text_embeddings = []
        all_metadatas = []
        sparse_chunks = []

        if os.path.exists(emb_dir):
            for fname in os.listdir(emb_dir):
                if not fname.endswith('.json'):
                    continue
                original_filename = fname[:-5]
                emb_state = embedding_service.load_state(original_filename)
                if not emb_state or "embeddings" not in emb_state:
                    continue
                local_mode = emb_state.get("embedding_mode", "dense")
                if mode in {"dense", "hybrid"} and local_mode in {"dense", "hybrid"}:
                    vectors = embedding_service.load_vectors(original_filename)
                    if vectors:
                        for i, item in enumerate(emb_state["embeddings"]):
                            all_text_embeddings.append((item["content"], vectors[i]))
                            all_metadatas.append(item["metadata"])
                if mode in {"sparse", "hybrid"}:
                    for item in emb_state["embeddings"]:
                        sparse_chunks.append({
                            "content": item["content"],
                            "metadata": item["metadata"]
                        })

        has_dense_data = len(all_text_embeddings) > 0
        has_sparse_data = len(sparse_chunks) > 0
        if (mode == "dense" and not has_dense_data) or (mode == "sparse" and not has_sparse_data) or (mode == "hybrid" and not (has_dense_data or has_sparse_data)):
            if os.path.exists(db_path):
                shutil.rmtree(db_path)
            self._db_cache.pop(cache_key, None)
            self._sparse_cache.pop(cache_key, None)
            logger.info(f"No embedding data remaining, removed index at {db_path}")
            return

        os.makedirs(db_path, exist_ok=True)

        if mode in {"dense", "hybrid"} and has_dense_data:
            embeddings_fn = init_embeddings(
                provider=provider,
                model_name=model_name,
                vector_dimension=vector_dimension or None
            )
            if db_type == "FAISS":
                if os.path.exists(os.path.join(db_path, "index.faiss")):
                    os.remove(os.path.join(db_path, "index.faiss"))
                if os.path.exists(os.path.join(db_path, "index.pkl")):
                    os.remove(os.path.join(db_path, "index.pkl"))
                vector_db = FAISS.from_embeddings(all_text_embeddings, embeddings_fn, metadatas=all_metadatas)
                vector_db.save_local(db_path)
                self._db_cache[cache_key] = vector_db
            elif db_type == "Chroma":
                if os.path.exists(db_path):
                    shutil.rmtree(db_path)
                    os.makedirs(db_path, exist_ok=True)
                docs = [Document(page_content=te[0], metadata=m) for te, m in zip(all_text_embeddings, all_metadatas)]
                vector_db = Chroma.from_documents(docs, embeddings_fn, persist_directory=db_path)
                vector_db.persist()
                self._db_cache[cache_key] = vector_db

        if mode in {"sparse", "hybrid"} and has_sparse_data:
            sparse_index = self._build_sparse_index(sparse_chunks)
            self._save_sparse_index(db_path, sparse_index)
            self._sparse_cache[cache_key] = sparse_index

        self._save_index_meta(db_path, {
            "embedding_mode": mode,
            "embedding_provider": provider,
            "embedding_model": model_name,
            "vector_dimension": vector_dimension,
            "db_type": db_type,
            "db_name": db_name
        })

        logger.info(f"Rebuilt index ({db_type}/{db_name}) mode={mode}")

    def query(self, text: str, k: int = 3, db_type: str = "FAISS", db_name: str = "default"):
        # 兼容旧调用：默认走新的 search 接口并返回 Document 列表
        results = self.search(
            text=text,
            k=k,
            db_type=db_type,
            db_name=db_name
        )
        return [Document(page_content=r["content"], metadata=r["metadata"]) for r in results]

    def search(
        self,
        text: str,
        k: int = 5,
        db_type: str = "FAISS",
        db_name: str = "default",
        filenames: list = None,
        score_threshold: float = None,
        hybrid_alpha: float = 0.7
    ):
        filenames_set = set(filenames or [])
        cache_key = (db_type, db_name)
        db_path = os.path.join(self.save_dir, db_type, db_name)
        index_meta = self._load_index_meta(db_path) or {}
        mode = index_meta.get("embedding_mode", "dense")

        if mode == "sparse":
            sparse_hits = self._sparse_search(
                text=text,
                k=k,
                db_type=db_type,
                db_name=db_name,
                filenames_set=filenames_set,
                score_threshold=score_threshold
            )
            return sparse_hits
        if mode == "hybrid":
            dense_hits = self._dense_search(
                text=text,
                k=max(k * 3, 10),
                db_type=db_type,
                db_name=db_name,
                filenames_set=filenames_set,
                score_threshold=None,
                index_meta=index_meta
            )
            sparse_hits = self._sparse_search(
                text=text,
                k=max(k * 3, 10),
                db_type=db_type,
                db_name=db_name,
                filenames_set=filenames_set,
                score_threshold=None
            )
            return self._merge_hybrid_results(
                dense_hits,
                sparse_hits,
                k=k,
                hybrid_alpha=hybrid_alpha,
                score_threshold=score_threshold
            )

        # dense
        return self._dense_search(
            text=text,
            k=k,
            db_type=db_type,
            db_name=db_name,
            filenames_set=filenames_set,
            score_threshold=score_threshold,
            index_meta=index_meta
        )

    def _dense_search(
        self,
        text: str,
        k: int,
        db_type: str,
        db_name: str,
        filenames_set: set,
        score_threshold: float,
        index_meta: dict
    ):
        cache_key = (db_type, db_name)
        db_path = os.path.join(self.save_dir, db_type, db_name)

        db = self._db_cache.get(cache_key)
        if not db:
            if not os.path.exists(db_path):
                logger.warning(f"索引不存在: {db_path}")
                return []

            provider = index_meta.get("embedding_provider", "HuggingFace")
            model_name = index_meta.get("embedding_model", "BAAI/bge-m3")
            vector_dimension = index_meta.get("vector_dimension")
            embeddings = init_embeddings(
                provider=provider,
                model_name=model_name,
                vector_dimension=vector_dimension or None
            )
            if db_type == "FAISS":
                db = self._load_faiss(db_path, embeddings)
            elif db_type == "Chroma":
                db = Chroma(persist_directory=db_path, embedding_function=embeddings)
            else:
                return []
            self._db_cache[cache_key] = db

        # FAISS 返回距离，越小越相似，这里映射到 (0,1]
        pairs = db.similarity_search_with_score(text, k=k)
        results = []
        for doc, raw_score in pairs:
            score = 1.0 / (1.0 + float(raw_score))
            meta = doc.metadata or {}
            if filenames_set and meta.get("filename") not in filenames_set:
                continue
            if score_threshold is not None and score < score_threshold:
                continue
            results.append({
                "content": doc.page_content,
                "metadata": meta,
                "score": score,
                "retrieval_mode": "dense"
            })
        return results[:k]

    def _sparse_search(
        self,
        text: str,
        k: int,
        db_type: str,
        db_name: str,
        filenames_set: set,
        score_threshold: float
    ):
        cache_key = (db_type, db_name)
        sparse = self._sparse_cache.get(cache_key)
        if not sparse:
            db_path = os.path.join(self.save_dir, db_type, db_name)
            sparse = self._load_sparse_index(db_path)
            if not sparse:
                return []
            self._sparse_cache[cache_key] = sparse

        query_tokens = self._tokenize(text)
        if not query_tokens:
            return []

        N = sparse["N"]
        avgdl = sparse["avgdl"]
        idf = sparse["idf"]
        docs = sparse["docs"]
        k1 = sparse.get("k1", 1.5)
        b = sparse.get("b", 0.75)

        scored = []
        for doc in docs:
            tf_map = doc["tf"]
            dl = doc["dl"]
            score = 0.0
            for t in query_tokens:
                tf = tf_map.get(t, 0)
                if tf <= 0:
                    continue
                term_idf = idf.get(t, 0.0)
                denom = tf + k1 * (1 - b + b * dl / (avgdl or 1))
                score += term_idf * ((tf * (k1 + 1)) / denom)
            if score <= 0:
                continue

            meta = doc["metadata"] or {}
            if filenames_set and meta.get("filename") not in filenames_set:
                continue
            if score_threshold is not None and score < score_threshold:
                continue

            scored.append({
                "content": doc["content"],
                "metadata": meta,
                "score": float(score),
                "retrieval_mode": "sparse"
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def _merge_hybrid_results(self, dense_hits, sparse_hits, k: int, hybrid_alpha: float, score_threshold: float):
        alpha = min(max(hybrid_alpha, 0.0), 1.0)
        merged = {}

        def norm(results):
            if not results:
                return []
            scores = [r["score"] for r in results]
            lo, hi = min(scores), max(scores)
            if hi == lo:
                return [{**r, "norm_score": 1.0} for r in results]
            return [{**r, "norm_score": (r["score"] - lo) / (hi - lo)} for r in results]

        dense_norm = norm(dense_hits)
        sparse_norm = norm(sparse_hits)

        for r in dense_norm:
            key = self._result_key(r)
            merged[key] = {
                "content": r["content"],
                "metadata": r["metadata"],
                "dense_score": r["norm_score"],
                "sparse_score": 0.0
            }
        for r in sparse_norm:
            key = self._result_key(r)
            if key not in merged:
                merged[key] = {
                    "content": r["content"],
                    "metadata": r["metadata"],
                    "dense_score": 0.0,
                    "sparse_score": r["norm_score"]
                }
            else:
                merged[key]["sparse_score"] = r["norm_score"]

        out = []
        for item in merged.values():
            score = alpha * item["dense_score"] + (1 - alpha) * item["sparse_score"]
            if score_threshold is not None and score < score_threshold:
                continue
            out.append({
                "content": item["content"],
                "metadata": item["metadata"],
                "score": score,
                "retrieval_mode": "hybrid"
            })
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:k]

    def _result_key(self, r):
        meta = r.get("metadata") or {}
        return f"{meta.get('filename','')}-{meta.get('chunk_index','')}-{hash(r.get('content',''))}"

    def _build_sparse_index(self, chunks):
        tokenized_docs = []
        df = {}
        for c in chunks:
            tokens = self._tokenize(c["content"])
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            tokenized_docs.append({
                "content": c["content"],
                "metadata": c["metadata"],
                "tf": tf,
                "dl": len(tokens)
            })
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1

        N = len(tokenized_docs)
        idf = {}
        for t, dfi in df.items():
            idf[t] = math.log(1 + (N - dfi + 0.5) / (dfi + 0.5))

        avgdl = sum(d["dl"] for d in tokenized_docs) / (N or 1)
        return {
            "N": N,
            "avgdl": avgdl,
            "k1": 1.5,
            "b": 0.75,
            "idf": idf,
            "docs": tokenized_docs
        }

    def _tokenize(self, text: str):
        if not text:
            return []
        return [t.lower() for t in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text)]

    def _load_faiss(self, db_path: str, embeddings):
        return FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)

    def _has_valid_faiss_index(self, db_path: str) -> bool:
        return (
            os.path.exists(os.path.join(db_path, "index.faiss")) and
            os.path.exists(os.path.join(db_path, "index.pkl"))
        )

    def _clear_faiss_files(self, db_path: str):
        faiss_file = os.path.join(db_path, "index.faiss")
        pkl_file = os.path.join(db_path, "index.pkl")
        if os.path.exists(faiss_file):
            os.remove(faiss_file)
        if os.path.exists(pkl_file):
            os.remove(pkl_file)

    def _save_index_meta(self, db_path: str, meta: dict):
        path = os.path.join(db_path, self.INDEX_META_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _load_index_meta(self, db_path: str):
        path = os.path.join(db_path, self.INDEX_META_FILE)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_sparse_index(self, db_path: str, sparse_index: dict):
        path = os.path.join(db_path, self.SPARSE_INDEX_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sparse_index, f, ensure_ascii=False)

    def _load_sparse_index(self, db_path: str):
        path = os.path.join(db_path, self.SPARSE_INDEX_FILE)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


index_service = IndexService()
