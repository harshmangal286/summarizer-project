from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
import tempfile
import os
from app.services import DocumentSummarizer

app = FastAPI()
router = APIRouter()

# ✅ Backend Storage for Summaries
summary_store = {}

# ✅ Available Summarization Models
AVAILABLE_MODELS = [
    "gemini", "openai", "mistralai/mistral-7b-instruct",
    "bart", "t5-large", "t5-base", "t5-small"
]

# ✅ Create one instance of the summarizer
summarizer = DocumentSummarizer()

@router.post("/summarize")
async def summarize_document(model: str, file: UploadFile = File(...)):
    """
    Handles file upload and summarization.
    """
    if model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model. Choose from: {', '.join(AVAILABLE_MODELS)}")

    ext = file.filename.split(".")[-1].lower()
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    # ✅ Save uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name
        print(f"✅ Temp file created: {temp_path}")

    try:
        # ✅ Extract text using instance method
        text = summarizer.extract_text(temp_path)
    finally:
        os.remove(temp_path)

    if not text.strip():
        raise HTTPException(status_code=400, detail="No readable text extracted from document.")

    print(f"📄 Text Extracted (first 500 chars):\n{text[:500]}")

    # ✅ Use summarize_text to trigger all logic including extract_headings, format_summary
    summary = summarizer.summarize_text(text, model_name=model, format_style="bullet")

    print(f"📜 Final Summary Output:\n{summary}")

    # ✅ Store and return summary
    summary_id = len(summary_store) + 1
    summary_store[summary_id] = {
        "file_name": file.filename,
        "model_used": model,
        "summary": summary,
        "created_at": os.path.getmtime(temp_path),
        "document_text": text
    }

    return {
        "summary_url": f"http://127.0.0.1:8000/get_summary/{summary_id}",
        "model_used": model,
        "summary": summary
    }

@router.get("/get_summary/{summary_id}")
async def get_summary(summary_id: int):
    """Fetch summary from in-memory store."""
    if summary_id not in summary_store:
        raise HTTPException(status_code=404, detail="Summary not found.")
    return summary_store[summary_id]

# Mount router
app.include_router(router)
