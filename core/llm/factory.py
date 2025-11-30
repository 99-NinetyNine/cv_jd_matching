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
    
    if model_name == "mock":
        from langchain_core.messages import AIMessage
        from langchain_community.chat_models import FakeListChatModel
        # Return a FakeListChatModel that returns a valid JSON string for a Resume
        # We need it to return enough responses for the loop
        mock_resume = {
            "basics": {
                "name": "Mock User",
                "label": "Developer",
                "email": "mock@example.com",
                "summary": "Experienced mock developer.",
                "location": {"city": "Mock City", "countryCode": "US"},
                "profiles": []
            },
            "work": [
                {
                    "name": "Mock Corp",
                    "position": "Senior Mock",
                    "startDate": "2020-01",
                    "endDate": "Present",
                    "summary": "Did mock things.",
                    "highlights": ["Mocked a lot"]
                }
            ],
            "education": [],
            "skills": [{"name": "Mocking", "keywords": ["Jest", "Pytest"]}],
            "projects": [],
            "awards": [],
            "certificates": [],
            "publications": [],
            "languages": [],
            "interests": [],
            "references": [],
            "volunteer": []
        }
        import json
        return FakeListChatModel(responses=[json.dumps(mock_resume)] * 100)

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

def get_embeddings(**kwargs) -> Embeddings:
    """
    Factory function to get an Embeddings instance.
    Uses LLM_MODEL environment variable to determine the model.
    
    Args:
        **kwargs: Additional arguments to pass to the model constructor
        
    Returns:
        Embeddings: An instance of a LangChain embeddings model
    """
    model_name = os.getenv("LLM_MODEL", "llama3")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    if model_name.startswith("gpt"):
        return OpenAIEmbeddings(model="text-embedding-3-small", **kwargs) # Default to small for cost/speed
    elif model_name.startswith("gemini"):
        return GoogleGenerativeAIEmbeddings(model="models/embedding-001", **kwargs)
    else:
        return OllamaEmbeddings(
            model=model_name,
            base_url=base_url,
            **kwargs
        )