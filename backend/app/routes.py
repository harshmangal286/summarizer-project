from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
import tempfile
import os
from app.services import DocumentSummarizer

app = FastAPI()
router = APIRouter()

# ✅ Backend Storage for Summaries
summary_store = {}

# ✅ Available Summarization Models
AVAILABLE_MODELS = ["gemini",
                    "bart",
                    "t5-large",
                    "t5-base",
                    "t5-small"]  # Extend this list if needed

@router.post("/summarize")
async def summarize_document(file: UploadFile = File(...), model: str = "gemini"):
    """
    Handles file upload and summarization.
    User can select a model: 'gemini' (default) or 'openai'.
    """
    if model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model. Choose from: {', '.join(AVAILABLE_MODELS)}")

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF or DOCX.")

    # ✅ Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name
        print(f"✅ File saved at: {temp_file_path}")  # Debugging: Check file path

    # ✅ Extract text
    text = DocumentSummarizer.extract_text_from_pdf(temp_file_path) if file_extension == "pdf" else DocumentSummarizer.extract_text_from_docx(temp_file_path)
    
    # ✅ Remove temporary file
    os.remove(temp_file_path)

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text found in the uploaded document.")

    print(f"📄 Extracted Text:\n{text[:500]}")  # Debugging: Print first 500 characters

    # ✅ Summarize extracted text using the selected model
    if model == "gemini":
        summary =  DocumentSummarizer.summarize_with_gemini(text)
    elif model == "openai":
        summary = summarize_with_openai(text)

    print(f"📜 Generated Summary:\n{summary}")  # Debugging: Print summary in console

    # ✅ Store summary in backend storage
    summary_id = len(summary_store) + 1
    summary_store[summary_id] = {
        "file_name": file.filename,
        "model_used": model,
        "summary": summary
    }

    # ✅ Generate Summary URL
    summary_url = f"http://127.0.0.1:8000/get_summary/{summary_id}"
    print(f"🔗 Summary available at: {summary_url}")  # Debugging: Print URL

    return {"summary_url": summary_url, "model_used": model, "summary": summary}


@router.get("/get_summary/{summary_id}")
async def get_summary(summary_id: int):
    """Retrieve stored summary by ID."""
    if summary_id not in summary_store:
        raise HTTPException(status_code=404, detail="Summary not found.")
    
    return summary_store[summary_id]
