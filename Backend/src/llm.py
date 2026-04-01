import os
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

def init_llm(model_name="deepseek-chat"):
    """
    Initialize the DeepSeek LLM through Langchain's ChatOpenAI compatible interface.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    
    if not api_key or api_key == "sk-please_replace_me":
        raise ValueError("Please set a valid DEEPSEEK_API_KEY in the .env file.")

    # Using provided model_name (deepseek-chat or deepseek-reasoner)
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=api_base,
        max_tokens=2048,
        temperature=0.1 if model_name == "deepseek-chat" else 1.0, # Reasoner usually recommends temp=1.0 or 0
    )
    return llm

def init_embeddings():
    """
    Initialize HuggingFace bge-m3 embeddings.
    """
    model_name = "BAAI/bge-m3"
    model_kwargs = {'device': 'cpu'} # Change to 'cuda' if GPU is available
    encode_kwargs = {'normalize_embeddings': True}
    
    hf_bge_embeddings = HuggingFaceBgeEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    return hf_bge_embeddings
