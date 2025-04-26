# import os
# import fitz  # PyMuPDF
# import docx
# import logging
# import nltk
# import torch
# import concurrent.futures
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
# from dotenv import load_dotenv
# import google.generativeai as genai

# nltk.download("punkt")

# # ✅ Logging Configuration
# logging.basicConfig(level=logging.INFO)

# # ✅ Load API Key
# load_dotenv()
# api_key = os.getenv("GEMINI_API_KEY")
# if not api_key:
#     raise ValueError("🚨 GEMINI API Key is missing. Set GEMINI_API_KEY as an environment variable.")

# genai.configure(api_key=api_key)

# # ✅ Model Mapping
# models = {
#     "bart": "facebook/bart-large-cnn",
#     "t5-large": "google/flan-t5-large",
#     "t5-base": "google/flan-t5-base",
#     "t5-small": "google/flan-t5-small",
#     "gemini": "google/gemini-1.5-pro"
# }

# # ✅ Device Selection
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# logging.info(f"✅ Using device: {device}")

# # ✅ Lazy Load Models
# tokenizers, models_loaded = {}, {}

# def load_model(model_name):
#     """Loads model and tokenizer dynamically."""
#     if model_name not in models:
#         raise ValueError(f"❌ Invalid model. Available: {', '.join(models.keys())}")

#     if model_name not in tokenizers or model_name not in models_loaded:
#         logging.info(f"📥 Loading model: {model_name}...")
#         tokenizers[model_name] = AutoTokenizer.from_pretrained(models[model_name])
#         models_loaded[model_name] = AutoModelForSeq2SeqLM.from_pretrained(models[model_name]).to(device)

# # ✅ Extract Structured Headings
# def extract_headings(text):
#     """Extracts structured headings based on keywords."""
#     headings = re.findall(r"\b(?:Introduction|Overview|Challenges|Benefits|Impact|Future Scope|Conclusion)\b", text, re.IGNORECASE)
#     return list(set(headings)) if headings else ["General Summary"]

# # ✅ Format Summaries Under Headings
# def format_summary(text):
#     """Formats text into structured bullet points."""
#     bullet_points = [f"• {point.strip()}" for point in text.split("\n") if point.strip()]
#     return "\n".join(bullet_points)

# # ✅ Text Extraction Functions
# def extract_text_from_pdf(file_path):
#     """Memory-efficient PDF text extraction."""
#     try:
#         with fitz.open(file_path) as pdf:
#             return "\n".join(page.get_text("text") for page in pdf)
#     except Exception as e:
#         logging.error(f"❌ PDF Extraction Error: {e}")
#         return ""

# def extract_text_from_docx(file_path):
#     """Extracts text from a DOCX file."""
#     try:
#         return "\n".join(para.text for para in docx.Document(file_path).paragraphs if para.text.strip())
#     except Exception as e:
#         logging.error(f"❌ DOCX Extraction Error: {e}")
#         return ""

# def extract_text_from_txt(file_path):
#     """Extracts text from a TXT file."""
#     try:
#         with open(file_path, "r", encoding="utf-8") as file:
#             return file.read().strip()
#     except Exception as e:
#         logging.error(f"❌ TXT Extraction Error: {e}")
#         return ""

# def process_documents(files):
#     """Batch process PDFs & DOCX."""
#     extracted_texts = {}
    
#     for file in files:
#         ext = os.path.splitext(file)[-1].lower()
#         if ext == ".pdf":
#             extracted_texts[file] = extract_text_from_pdf(file)
#         elif ext == ".docx":
#             extracted_texts[file] = extract_text_from_docx(file)
#         elif ext == ".txt":
#             extracted_texts[file] = extract_text_from_txt(file)
    
#     return extracted_texts

# # ✅ Gemini API Summarization
# def summarize_with_gemini(text):
#     """Handles Gemini API calls with error handling."""
#     try:
#         model = genai.GenerativeModel("gemini-1.5-pro")
#         response = model.generate_content(f"Summarize this text:\n{text}")
#         return response.text if response.text else "❌ No response from Gemini."
#     except Exception as e:
#         logging.error(f"🚨 Gemini API Error: {e}")
#         return "❌ Gemini API is currently unavailable. Please try again later."

# # ✅ Text Chunking (Smart Splitting)
# def split_text_smart(text, tokenizer, max_tokens=1024):
#     """Smart splitting based on actual token count."""
#     sentences = nltk.sent_tokenize(text)
#     chunks, current_chunk = [], []
#     token_count = 0

#     for sentence in sentences:
#         sentence_tokens = len(tokenizer.encode(sentence, add_special_tokens=False))

#         if token_count + sentence_tokens <= max_tokens:
#             current_chunk.append(sentence)
#             token_count += sentence_tokens
#         else:
#             chunks.append(" ".join(current_chunk))
#             current_chunk = [sentence]
#             token_count = sentence_tokens

#     if current_chunk:
#         chunks.append(" ".join(current_chunk))

#     return chunks

# # ✅ Summarization Function with Headings
# def summarize_text(text, model_name="gemini"):
#     """Summarizes text under structured headings."""
#     if not text.strip():
#         return "⚠️ No text found for summarization."

#     logging.info(f"🛠 Model requested: {model_name}")

#     if model_name == "gemini":
#         return summarize_with_gemini(text)

#     if model_name not in models:
#         return f"❌ Invalid model. Choose from: {', '.join(models.keys())}"

#     load_model(model_name)
#     tokenizer, model = tokenizers[model_name], models_loaded[model_name]

#     max_input_length = 1024
#     input_tokens = tokenizer(text, return_tensors="pt", truncation=True)
#     input_length = input_tokens["input_ids"].shape[1]

#     if input_length > max_input_length:
#         logging.warning(f"⚠️ Input too long ({input_length} tokens). Splitting text.")
#         return summarize_large_text_parallel(text, model_name)

#     inputs = tokenizer(text, return_tensors="pt", max_length=max_input_length, truncation=True).to(device)
#     summary_ids = model.generate(
#         inputs["input_ids"], max_length=1050, min_length=50,
#         length_penalty=2.0, num_beams=7, no_repeat_ngram_size=3,
#         temperature=0.7, top_k=50, top_p=0.9, early_stopping=True, do_sample=True
#     )

#     raw_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

#     # ✅ Extract headings & format summary under sections
#     headings = extract_headings(text)
#     structured_summary = "\n\n".join([f"**{heading}**\n{format_summary(raw_summary)}" for heading in headings])

#     return structured_summary

# # ✅ Efficient Parallel Summarization for Large Documents
# def summarize_large_text_parallel(text, model_name="gemini"):
#     """Splits long text and summarizes each chunk separately."""
#     chunks = split_text_smart(text)

#     with concurrent.futures.ProcessPoolExecutor() as executor:
#         if model_name == "gemini":
#             summaries = list(executor.map(summarize_with_gemini, chunks))
#         else:
#             summaries = list(executor.map(lambda chunk: summarize_text(chunk, model_name), chunks))

#     return "\n\n".join(summaries)
