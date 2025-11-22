from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlmodel import Session, select
from core.db.models import ExternalProfile
import logging

logger = logging.getLogger(__name__)
# in order to fetch from linkedin github the user related info for checking the profile is not fake
# or tampererd (though needs colab with linkedin and github)
class ProfileFetcher:
    def __init__(self, session: Session):
        self.session = session
        
    def fetch(self, url: str) -> Dict:
        # 1. Check Cache
        statement = select(ExternalProfile).where(ExternalProfile.url == url)
        profile = self.session.exec(statement).first()
        
        if profile:
            # Check TTL (30 days)
            if datetime.utcnow() - profile.last_fetched < timedelta(days=30):
                logger.info(f"Cache hit for {url}")
                return profile.content
            else:
                logger.info(f"Cache expired for {url}")
        
        # 2. Fetch New Data (Mock for now, real scraper would go here)
        logger.info(f"Fetching new data for {url}")
        content = self._mock_fetch(url)
        
        # 3. Update/Insert Cache
        if profile:
            profile.content = content
            profile.last_fetched = datetime.utcnow()
        else:
            platform = "linkedin" if "linkedin.com" in url else "github" if "github.com" in url else "other"
            profile = ExternalProfile(url=url, platform=platform, content=content)
            self.session.add(profile)
            
        self.session.commit()
        return content
        
    def _mock_fetch(self, url: str) -> Dict:
        # Simulate fetching data based on URL
        if "linkedin.com" in url:
            return {
                "source": "linkedin",
                "skills": ["Leadership", "Management", "Public Speaking"], # Mock additional skills
                "languages": ["English", "Spanish"]
            }
        elif "github.com" in url:
            return {
                "source": "github",
                "projects": [
                    {"name": "CV-Matcher", "stars": 150, "language": "Python"},
                    {"name": "React-Dashboard", "stars": 85, "language": "TypeScript"}
                ]
            }
        return {}
