import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock missing modules
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
sys.modules["langchain_core.prompts"] = MagicMock()
sys.modules["langchain_core.language_models"] = MagicMock()
sys.modules["langchain_core.language_models.chat_models"] = MagicMock()
sys.modules["langchain_core.embeddings"] = MagicMock()
sys.modules["langchain_ollama"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()

from core.matching.semantic_matcher import HybridMatcher
@pytest.fixture
def mock_components():
    with patch("core.matching.semantic_matcher.get_embeddings") as mock_emb, \
         patch("core.matching.semantic_matcher.get_llm") as mock_llm, \
         patch("core.matching.semantic_matcher.redis_client") as mock_redis:
        
        mock_emb.return_value.embed_query.return_value = [0.1] * 768
        mock_redis.get.return_value = None
        yield mock_emb, mock_llm, mock_redis

def test_matcher_skills_score(mock_components):
    matcher = HybridMatcher(reranker_model=None) # Disable reranker for unit test
    
    cv_skills = ["Python", "FastAPI", "Docker"]
    job_skills = ["Python", "Django", "Docker", "Kubernetes"]
    
    score = matcher._calculate_skills_score(cv_skills, job_skills)
    # Intersection: Python, Docker (2)
    # Union/Job Set: 4
    # Score: 2/4 = 0.5
    assert score == 0.5

def test_match_logic(mock_components):
    matcher = HybridMatcher(reranker_model=None)
    matcher.reranker = None # Ensure it's None
    
    cv_data = {
        "skills": [{"name": "Python"}],
        "work": [{"company": "A", "position": "Dev"}],
        "embedding": [0.1] * 768
    }
    
    job_candidates = [
        {
            "job_id": "1",
            "title": "Python Dev",
            "skills": ["Python"],
            "embedding": [0.1] * 768
        }
    ]
    
    matches = matcher.match(cv_data, job_candidates)
    assert len(matches) == 1
    assert matches[0]["job_id"] == "1"
    # Semantic score should be 1.0 (identical vectors)
    # Skills score should be 1.0
    # Experience score should be 1.0
    # Final score: 0.5*1 + 0.3*1 + 0.2*1 = 1.0
    assert matches[0]["match_score"] > 0.9
