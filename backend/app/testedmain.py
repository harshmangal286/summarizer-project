# from fastapi import FastAPI, File, UploadFile, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from app.testedservices import summarize_text, extract_text_from_pdf, extract_text_from_docx,summarize_with_gemini
# import tempfile
# from app.routes import router
# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,  # ✅ Fixed typo
#     allow_methods=["*"],
#     allow_headers=["*"]
# )
# app.include_router(router)
# @app.post("/summarize")
# async def summarize_file(file: UploadFile = File(...), model: str ="t5-small"):  
#     """Handles file upload, extracts text, and summarizes content."""
#     file_type = file.filename.split(".")[-1].lower()

#     if file_type not in ["pdf", "docx"]:
#         raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a PDF or DOCX.")

#     with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
#         temp_file.write(await file.read())
#         temp_file_path = temp_file.name

#     text = extract_text_from_pdf(temp_file_path) if file_type == "pdf" else extract_text_from_docx(temp_file_path)

#     if not text.strip():
#         raise HTTPException(status_code=400, detail="No text found in the document.")

#     summary = summarize_text(text, model)  

#     return {"summary": summary}
