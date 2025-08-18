from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router   # ✅ import your router


app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return {"message": "Backend is running!"}
# ✅ Backend Storage for Summarie

@app.post("/summarize")
async def summarize_document(model: str, file: UploadFile = File(...)):
    """
    Handles file upload and summarization.
    """
    if model not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400, detail=f"Invalid model. Choose from: {', '.join(AVAILABLE_MODELS)}")

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

    # ✅ Use summarize_text to trigger all logic including extract_headings, format_summary
    summary = summarizer.summarize_text(
        text, model_name=model, format_style="bullet")

    print(f"📜 Final Summary Output:\n{summary}")

    # ✅ Store and return summary
    summary_id = len(summary_store) + 1
    summary_store[summary_id] = {
        "file_name": file.filename,
        "model_used": model,
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
    file: UploadFile = File(None)
):
    try:
        # If user attached a file, read its text and load into summarizer
        if file:
            file_bytes = await file.read()
            summarizer.load_document(file_bytes, file.filename)

        # Call your QA method
        answer = summarizer.answer_question(question)

        return {"choices": [{"message": {"content": answer}}]}

    except Exception as e:
        return {"error": str(e)}
# ✅ register your routes here
app.include_router(router)
