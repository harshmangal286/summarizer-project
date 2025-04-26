from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services import DocumentSummarizer
import tempfile
import os
from app.routes import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/summarize")
async def summarize_file(
    file: UploadFile = File(...),
    model: str = "gemini",
    summary_length: str = "medium"
):
    file_type = file.filename.split(".")[-1].lower()

    if file_type not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a PDF, DOCX, or TXT.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    try:
        # 🔑 Instantiate summarizer with API key
        api_key = os.getenv("GEMINI_API_KEY", "")
        summarizer = DocumentSummarizer(api_key=api_key)

        # 🧠 Extract text
        if file_type == "pdf":
            text = summarizer.extract_text_from_pdf(temp_file_path)
        elif file_type == "docx":
            text = summarizer.extract_text_from_docx(temp_file_path)
        elif file_type == "txt":
            text = summarizer.extract_text_from_txt(temp_file_path)

        if not text.strip():
            raise HTTPException(status_code=400, detail="No text found in the document.")

        # 🪄 Summarize
        if model == "gemini":
            summary = summarizer.summarize_with_gemini(text)#, summary_length=summary_length
        elif model == "openai":
            summary = summarizer.summarize_with_openai(text )#,summary_length=summary_length
        else:
            raise HTTPException(status_code=400, detail="Invalid model. Choose 'gemini' or 'openai'.")

        print(f"📜 Generated Summary:\n{summary}")
        return {"summary": summary}

    finally:
        os.remove(temp_file_path)
        print(f"✅ Temporary file removed: {temp_file_path}")

app.include_router(router)
