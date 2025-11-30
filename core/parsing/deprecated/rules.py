import re
from typing import List, Dict, Any
# DEPRECATED

class RegexRules:
    # Patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'(\+?\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}'
    LINKEDIN_PATTERN = r'linkedin\.com/in/[a-zA-Z0-9_-]+'
    GITHUB_PATTERN = r'github\.com/[a-zA-Z0-9_-]+'
    
    # Date patterns for work experience (e.g., "Jan 2020 - Present", "01/2020 - 02/2021")
    DATE_RANGE_PATTERN = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}/\d{4})\s*(?:-|to|–)\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}/\d{4}|Present|Current|Now)'

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        return list(set(re.findall(RegexRules.EMAIL_PATTERN, text)))

    @staticmethod
    def extract_phones(text: str) -> List[str]:
        return list(set(re.findall(RegexRules.PHONE_PATTERN, text)))

    @staticmethod
    def extract_links(text: str) -> Dict[str, str]:
        links = {}
        linkedin = re.search(RegexRules.LINKEDIN_PATTERN, text, re.IGNORECASE)
        if linkedin:
            links['linkedin'] = "https://" + linkedin.group(0)
            
        github = re.search(RegexRules.GITHUB_PATTERN, text, re.IGNORECASE)
        if github:
            links['github'] = "https://" + github.group(0)
            
        return links

    @staticmethod
    def extract_dates(text: str) -> List[str]:
        # This is a simple extraction, might need more context to map to specific roles
        matches = re.findall(RegexRules.DATE_RANGE_PATTERN, text, re.IGNORECASE)
        return [f"{m[0]} - {m[1]}" for m in matches]
