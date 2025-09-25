import re
def clean_transcript(text: str) -> str:
    # Remove anything inside parentheses (including the parentheses)
    text = re.sub(r"\([^)]*\)", "", text)
    
    # Remove anything inside square brackets (including the brackets)
    text = re.sub(r"\[[^\]]*\]", "", text)
    
    # Remove anything inside curly braces (including the braces)
    text = re.sub(r"\{[^}]*\}", "", text)
    
    # Clean up extra spaces
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()