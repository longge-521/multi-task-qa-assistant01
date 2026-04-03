import logging
from langchain_openai import ChatOpenAI
from src.config import settings

logger = logging.getLogger(__name__)

_embeddings_cache = {}


def init_llm(model_name="deepseek-chat"):
    api_key = settings.DEEPSEEK_API_KEY
    api_base = settings.DEEPSEEK_API_BASE

    if not api_key or api_key == "sk-please_replace_me":
        raise ValueError("Please set a valid DEEPSEEK_API_KEY in the .env file.")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=api_base,
        max_tokens=2048,
        temperature=0.1 if model_name == "deepseek-chat" else 1.0,
        streaming=True,
    )
    return llm


def init_embeddings(provider="HuggingFace", model_name="BAAI/bge-m3", vector_dimension=None):
    """
    根据提供者和模型名称初始化 Embeddings，使用缓存避免重复加载大模型。
    """
    cache_key = f"{provider}:{model_name}:{vector_dimension or 'default'}"
    if cache_key in _embeddings_cache:
        return _embeddings_cache[cache_key]

    logger.info(f"Loading embeddings model: {provider}/{model_name} (first time, will be cached)")

    if provider == "HuggingFace":
        from langchain_huggingface import HuggingFaceEmbeddings
        instance = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    elif provider == "OpenAI":
        from langchain_openai import OpenAIEmbeddings
        kwargs = {"model": model_name}
        if vector_dimension:
            kwargs["dimensions"] = vector_dimension
        instance = OpenAIEmbeddings(**kwargs)
    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        instance = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

    _embeddings_cache[cache_key] = instance
    logger.info(f"Embeddings model cached: {cache_key}")
    return instance
