from pydantic import BaseModel

class SummarizeRequest(BaseModel):
    text: str
    model: str ="gemini"  # Default to 'gemini' model

