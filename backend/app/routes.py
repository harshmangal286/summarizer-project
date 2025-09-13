from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import tempfile
import os
from app.services import DocumentSummarizer

router = APIRouter()

# ✅ Backend Storage for Summaries
summary_store = {}

# ✅ Available Summarization Models - UI display names
AVAILABLE_MODELS = [
    "gemini", "openai", "mistralai/mistral-7b-instruct",
    "bart", "t5-large", "t5-base", "t5-small"
]

# ✅ Map UI model names to actual service names
MODEL_SERVICE_MAPPING = {
    "mistralai/mistral-7b-instruct": "openrouter",
    "gemini": "gemini",
    "openai": "openai",
    "bart": "bart",
    "t5-large": "t5-large", 
    "t5-base": "t5-base",
    "t5-small": "t5-small"
}

# ✅ Create one instance of the summarizer
summarizer = DocumentSummarizer()


@router.post("/summarize")
async def summarize_document(model: str = Form(...), file: UploadFile = File(...)):
    """
    Handles file upload and summarization.
    """
    if model not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400, detail=f"Invalid model. Choose from: {', '.join(AVAILABLE_MODELS)}")

    # ✅ Map the UI model name to the actual service name
    service_name = MODEL_SERVICE_MAPPING.get(model)
    if not service_name:
        raise HTTPException(status_code=400, detail=f"Invalid model mapping for: {model}")

    ext = file.filename.split(".")[-1].lower()
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(
            status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

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
        raise HTTPException(
            status_code=400, detail="No readable text extracted from document.")

    print(f"📄 Text Extracted (first 500 chars):\n{text[:500]}")
    
    

    # ✅ Use the mapped service name instead of the UI model name
    summary = summarizer.summarize_text(
        text, model_name=service_name, format_style="bullet")

    print(f"📜 Final Summary Output:\n{summary}")

    # ✅ Store and return summary
    summary_id = len(summary_store) + 1
    summary_store[summary_id] = {
        "file_name": file.filename,
        "model_used": model,  # Store the original UI model name
        "service_used": service_name,  # Store the actual service used
        "summary": summary,
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


@router.post("/chat")
async def chat_endpoint(
    question: str = Form(...),
    file: UploadFile = File(None),
    model: str = Form("openrouter")  # Default to openrouter for chat
):
    try:
        if file:
            file_bytes = await file.read()
            summarizer.load_document(file_bytes, file.filename)

        # Map the model name if provided, otherwise use default
        service_name = MODEL_SERVICE_MAPPING.get(model, "openrouter")
        
        raw_answer = summarizer.answer_question(question, model_name=service_name)

        # Normalize answer to a string
        answer_text = None
        if isinstance(raw_answer, str):
            answer_text = raw_answer
        elif isinstance(raw_answer, dict):
            try:
                answer_text = (
                    raw_answer.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            except Exception:
                answer_text = "Error parsing response from model."
        
        if not answer_text:
            answer_text = "No answer generated."

        return {"answer": answer_text}

    except Exception as e:
        return {"error": str(e)}