from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
import os

def get_llm(**kwargs) -> BaseChatModel:
    """
    Factory function to get an LLM instance.
    Uses LLM_MODEL environment variable to determine the model.
    Supports Ollama, OpenAI (ChatGPT), and Google (Gemini).
    
    Args:
        **kwargs: Additional arguments to pass to the model constructor
        
    Returns:
        BaseChatModel: An instance of a LangChain chat model
    """
    model_name = os.getenv("LLM_MODEL", "llama3")
    # Check environment variable for base URL if needed, otherwise default to localhost
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print("model_name", model_name)
    if model_name.startswith("gpt"):
        return ChatOpenAI(model=model_name, **kwargs)
    elif model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(model=model_name, **kwargs)
    else:
        return ChatOllama(
            model=model_name,
            base_url=base_url,
            **kwargs
        )
