import os
import re
import fitz  # PyMuPDF for PDF handling
import docx
import logging
import nltk
import torch
import concurrent.futures
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from dotenv import load_dotenv
import google.generativeai as genai
import requests
import pytesseract
from pdf2image import convert_from_path
import tempfile
import openai
from sentence_transformers import SentenceTransformer, util
import tiktoken

nltk.download("punkt_tab")

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for summarization models."""
    model_id: str
    max_input_length: int = 1024
    max_output_length: int = 1050
    min_output_length: int = 50
    length_penalty: float = 2.0
    num_beams: int = 7
    no_repeat_ngram_size: int = 3
    temperature: float = 0.7
    top_k: int = 50
    top_p: float = 0.9
    do_sample: bool = True


# Enhanced model configurations
MODEL_CONFIGS = {
    "gemini": ModelConfig(model_id="google/gemini-1.5-pro", max_input_length=8192),
    "openai": ModelConfig(model_id="gpt-3.5-turbo", max_input_length=4096),
    "openrouter": ModelConfig(model_id="mistralai/mistral-7b-instruct", max_input_length=4096)
}

# Heading categories to extract (configurable)
HEADING_CATEGORIES = [
    "Introduction", "Overview", "Background", "Methodology",
    "Challenges", "Benefits", "Impact", "Results", "Discussion",
    "Future Scope", "Conclusion", "Recommendations"
]


class DocumentSummarizer:
    """Main class for document summarization operations."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the summarizer with optional API key."""
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")

        # Initialize model caches
        self.tokenizers = {}
        self.models_loaded = {}
        self.active_model = None
        
        # Initialize API keys
        self.gemini_key = None
        self.openai_key = None
        self.openrouter_key = None
        
        # Configure API (with validation)
        self._configure_apis()
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.doc_chunks = []
        self.doc_embeddings = []

    def load_document(self, file_bytes: bytes, filename: str):
        """Load a document from bytes and build the knowledge base."""
        ext = filename.split(".")[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            text = self.extract_text(temp_path)
            if text:
                self.build_knowledge_base(text)
        finally:
            os.remove(temp_path)

    def _configure_apis(self):
        """Configure APIs from environment variables."""
        load_dotenv()

        self.gemini_available = False
        self.openai_available = False
        self.openrouter_available = False
        self.active_model = None

        # Initialize tokenizers for local models
        self.tokenizers = {
            'openai': tiktoken.get_encoding("cl100k_base"),
            # Add other local models if needed
        }

        # 🧠 Try Gemini First
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                model = genai.GenerativeModel("gemini-1.5-pro")
                test_response = model.generate_content("Ping")
                if test_response:
                    self.gemini_available = True
                    self.active_model = "gemini"
                    logger.info("✅ Gemini API successfully configured.")
            except Exception as e:
                logger.warning(f"❌ Gemini config failed: {e}")

        # Try OpenRouter
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if self.openrouter_key:
            try:
                test_response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://example.com",
                        "X-Title": "DocSummarizer"
                    },
                    json={
                        "model": "mistralai/mistral-7b-instruct",
                        "messages": [{"role": "user", "content": "Ping"}]
                    },
                    timeout=10
                )
                if test_response.ok:
                    self.openrouter_available = True
                    if not self.active_model:
                        self.active_model = "openrouter"
                    logger.info("✅ OpenRouter API successfully configured.")
            except Exception as e:
                logger.warning(f"❌ OpenRouter config failed: {e}")

        # Try OpenAI
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if self.openai_key:
            try:
                openai.api_key = self.openai_key
                self.openai_available = True
                if not self.active_model:
                    self.active_model = "openai"
                logger.info("✅ OpenAI API key loaded.")
            except Exception as e:
                logger.warning(f"❌ OpenAI config failed: {e}")

        # If no APIs are available, log a warning
        if not (self.gemini_available or self.openai_available or self.openrouter_available):
            logger.warning(
                "❗ No API keys configured. Please set API in .env file.")

    def load_model(self, model_name: str) -> bool:
        """Load model and tokenizer with error handling."""
        if model_name not in MODEL_CONFIGS:
            logger.error(
                f"Invalid model name: {model_name}. Available: {', '.join(MODEL_CONFIGS.keys())}")
            return False

        # For API-based models – no need to load locally
        if model_name == "gemini":
            if not self.gemini_available:
                logger.error("❌ Gemini API is not available or not configured")
                return False
            logger.info("✅ Gemini model selected – no loading needed")
            return True

        if model_name == "openai":
            if not self.openai_available:
                logger.error("❌ OpenAI API is not available or not configured")
                return False
            logger.info("✅ OpenAI model selected – no loading needed")
            return True

        if model_name == "openrouter":
            if not self.openrouter_available:
                logger.error("❌ OpenRouter API is not available or not configured")
                return False
            logger.info("✅ OpenRouter model selected – no loading needed")
            return True

        # HuggingFace models only
        if model_name not in self.tokenizers or model_name not in self.models_loaded:
            try:
                logger.info(f"🔄 Loading HuggingFace model: {model_name}")
                model_config = MODEL_CONFIGS[model_name]
                self.tokenizers[model_name] = AutoTokenizer.from_pretrained(model_config.model_id)
                self.models_loaded[model_name] = AutoModelForSeq2SeqLM.from_pretrained(
                    model_config.model_id
                ).to(self.device)
                logger.info(f"✅ Loaded model: {model_name}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to load model {model_name}: {e}")
                return False

        return True  # Already loaded

    def extract_headings(self, text: str) -> List[str]:
        logger.info("Extracting structural headings from text.")
        """Extract structural headings with improved pattern matching."""
        heading_pattern = r"\b(?:" + "|".join(HEADING_CATEGORIES) + r")\b"
        headings = re.findall(heading_pattern, text, re.IGNORECASE)

        # De-duplicate and preserve order
        seen = set()
        unique_headings = [h for h in headings if not (
            h.lower() in seen or seen.add(h.lower()))]

        return unique_headings if unique_headings else ["General Summary"]

    def format_summary(self, text: str, style: str = "bullet") -> str:
        logger.info(f"Formatting summary with style: {style}")
        """Format text into structured output with multiple style options."""
        if style == "bullet":
            bullet_points = [
                f"• {point.strip()}" for point in text.split("\n") if point.strip()]
            return "\n".join(bullet_points)
        elif style == "paragraph":
            return text
        elif style == "numbered":
            points = [point.strip()
                      for point in text.split("\n") if point.strip()]
            return "\n".join([f"{i+1}. {point}" for i, point in enumerate(points)])
        else:
            return text

    def extract_text(self, file_path: str) -> str:
        """Extract text from various file formats with improved error handling."""
        logger.info(f"Extracting text from {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return ""

        ext = os.path.splitext(file_path)[-1].lower()

        try:
            if ext == ".pdf":
                return self.extract_text_from_pdf(file_path)
            elif ext == ".docx":
                return self.extract_text_from_docx(file_path)
            elif ext == ".txt":
                return self.extract_text_from_txt(file_path)
            else:
                logger.error(f"Unsupported file format: {ext}")
                return ""
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return ""

    def extract_text_from_pdf(self, file_path: str) -> str:
        logger.info(f"Extracting text from PDF: {file_path}")
        """Extract text from PDF with improved memory handling and OCR for scanned pages."""
        try:
            text_chunks = []
            with fitz.open(file_path) as pdf:
                for page_num, page in enumerate(pdf):
                    try:
                        # Extract text from the page
                        page_text = page.get_text("text")
                        if page_text.strip():  # If text is found, add it to the chunks
                            text_chunks.append(page_text)
                        else:
                            # If no text, handle as a scanned page and perform OCR
                            images = convert_from_path(
                                file_path, first_page=page_num + 1, last_page=page_num + 1
                            )
                            for img in images:
                                # Convert to grayscale
                                gray_img = img.convert("L")
                                bw_img = gray_img.point(
                                    lambda x: 0 if x < 180 else 255, "1")  # Binarize
                                ocr_text = pytesseract.image_to_string(
                                    bw_img) + "\n"
                                text_chunks.append(ocr_text)
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract text from page {page_num}: {e}")

            return "\n".join(text_chunks)
        except Exception as e:
            logger.error(f"PDF Extraction Error: {e}")
            return ""

    def extract_text_from_docx(self, file_path: str) -> str:
        logger.info(f"Extracting text from DOCX: {file_path}")
        """Extract text from DOCX with enhanced structure preservation."""
        try:
            doc = docx.Document(file_path)

            # Preserve paragraph breaks better
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())

            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error(f"DOCX Extraction Error: {e}")
            return ""

    def extract_text_from_txt(self, file_path: str) -> str:
        logger.info(f"Extracting text from TXT: {file_path}")
        """Extract text from TXT with encoding fallbacks."""
        encodings = ['utf-8', 'latin-1', 'ascii']

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    return file.read().strip()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"TXT Extraction Error: {e}")
                return ""

        logger.error(
            "Could not decode file with any of the attempted encodings")
        return ""

    def process_documents(self, files: List[str]) -> Dict[str, str]:
        logger.info("Processing multiple documents in parallel.")
        """Process multiple documents with parallel execution."""
        if not files:
            logger.warning("No files provided for processing")
            return {}

        extracted_texts = {}

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(
                self.extract_text, file): file for file in files}

            for future in concurrent.futures.as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    text = future.result()
                    if text:
                        extracted_texts[file] = text
                except Exception as e:
                    logger.error(f"Failed to process {file}: {e}")

        return extracted_texts

    def split_text_smart(self, text: str, tokenizer: Any, max_tokens: int = 1024,
                         overlap: int = 100) -> List[str]:
        """Split text with sentence awareness and overlap between chunks."""
        logger.info("🔪 Splitting text into manageable chunks with overlap.")

        if not text.strip():
            logger.warning("⚠️ Input text is empty. Skipping split.")
            return []

        sentences = nltk.sent_tokenize(text)
        chunks, current_chunk = [], []
        token_count = 0

        for sentence in sentences:
            if not sentence.strip():
                continue

            sentence_tokens = len(tokenizer.encode(sentence, add_special_tokens=False))

            if token_count + sentence_tokens <= max_tokens:
                current_chunk.append(sentence)
                token_count += sentence_tokens
            else:
                chunks.append(" ".join(current_chunk))

                # Prepare overlap
                overlap_sentences = []
                overlap_tokens = 0
                for s in reversed(current_chunk):
                    s_tokens = len(tokenizer.encode(s, add_special_tokens=False))
                    if overlap_tokens + s_tokens <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break

                # New chunk begins
                current_chunk = overlap_sentences + [sentence]
                token_count = overlap_tokens + sentence_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def summarize_with_openrouter(self, text: str) -> str:
        """Generate summary using OpenRouter with improved prompting."""
        logger.info("Summarizing text with OpenRouter API.")
        if not self.openrouter_available:
            return "OpenRouter API is not configured or available."

        try:
            prompt = (
                "Provide a comprehensive summary of the following document. "
                "Focus on key facts, findings, and conclusions. "
                "Organize the summary in a clear structure. "
                "Use bullet points for clarity. "
                "Use a formal tone. "
                "Avoid unnecessary jargon. "
                "Text to summarize:\n\n"
                f"{text}"
            )
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://example.com",
                    "X-Title": "DocSummarizer"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenRouter Error: {e}")
            return f"OpenRouter API error: {str(e)}"

    def summarize_with_gemini(self, text: str) -> str:
        """Generate summary using Gemini with improved prompting."""
        logger.info("Summarizing text with Gemini API.")
        if not self.gemini_available:
            return "Gemini API is not configured or unavailable"

        try:
            model = genai.GenerativeModel("gemini-1.5-pro")

            prompt = (
                "Provide a comprehensive summary of the following document. "
                "Focus on key facts, findings, and conclusions. "
                "Organize the summary in a clear structure. "
                "Use bullet points for clarity. "
                "Use a formal tone. "
                "Avoid unnecessary jargon. "
                "Text to summarize:\n\n"
                f"{text}"
            )

            response = model.generate_content(prompt)
            return response.text if response.text else "No response from Gemini."
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"Gemini API error: {str(e)}"

    def summarize_with_openai(self, text: str) -> str:
        """Generate summary using OpenAI GPT with improved prompting."""
        logger.info("Summarizing text with OpenAI API.")
        from openai import OpenAI
        
        client = OpenAI(api_key=self.openai_key)

        if not self.openai_available:
            return "OpenAI API is not configured or available"

        try:
            prompt = (
                "Summarize the following document in a formal tone, using bullet points and clear structure. "
                "Avoid jargon, and highlight key points, findings, and conclusion:\n\n"
                f"{text}"
            )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI Error: {e}")
            return f"OpenAI API error: {str(e)}"

    def summarize_text(self, text: str, model_name: str = None,
                       format_style: str = "bullet") -> str:
        """Generate a summary with specified model and formatting."""
        logger.info(f"Summarizing text with model: {model_name or self.active_model}")
        if not text.strip():
            return "No text found for summarization."

        # Use the provided model_name or fall back to active_model
        model_to_use = model_name or self.active_model
        if not model_to_use:
            return "❌ No model available. Please configure Gemini, OpenAI, or OpenRouter."

        # Handle API-based models directly
        if model_to_use == "openrouter":
            if not self.openrouter_available:
                logger.warning("OpenRouter API not available, trying fallback...")
                if self.gemini_available:
                    model_to_use = "gemini"
                elif self.openai_available:
                    model_to_use = "openai"
                else:
                    return "OpenRouter API not available and no fallback models."
            else:
                summary = self.summarize_with_openrouter(text)
                return self.format_summary(summary, style=format_style)

        if model_to_use == "gemini":
            if not self.gemini_available:
                logger.warning("Gemini API not available, trying fallback...")
                if self.openai_available:
                    model_to_use = "openai"
                elif self.openrouter_available:
                    model_to_use = "openrouter"
                else:
                    return "Gemini API not available and no fallback models."
            else:
                summary = self.summarize_with_gemini(text)
                return self.format_summary(summary, style=format_style)

        if model_to_use == "openai":
            if not self.openai_available:
                logger.warning("OpenAI API not available, trying fallback...")
                if self.gemini_available:
                    model_to_use = "gemini"
                elif self.openrouter_available:
                    model_to_use = "openrouter"
                else:
                    return "OpenAI API not available and no fallback models."
            else:
                summary = self.summarize_with_openai(text)
                return self.format_summary(summary, style=format_style)

        # For local models (not API-based)
        if model_to_use not in self.tokenizers or model_to_use not in self.models_loaded:
            if not self.load_model(model_to_use):
                return f"Failed to load model: {model_to_use}"

        tokenizer = self.tokenizers[model_to_use]
        model = self.models_loaded[model_to_use]
        model_config = MODEL_CONFIGS[model_to_use]

        chunks = self.split_text_smart(
            text, tokenizer, max_tokens=model_config.max_input_length)
        summaries = []

        for chunk in chunks:
            inputs = tokenizer.encode(chunk, return_tensors="pt", truncation=True,
                                      max_length=model_config.max_input_length).to(self.device)

            with torch.no_grad():
                summary_ids = model.generate(
                    inputs,
                    max_length=model_config.max_output_length,
                    min_length=model_config.min_output_length,
                    num_beams=model_config.num_beams,
                    length_penalty=model_config.length_penalty,
                    no_repeat_ngram_size=model_config.no_repeat_ngram_size,
                    temperature=model_config.temperature,
                    top_k=model_config.top_k,
                    top_p=model_config.top_p,
                    do_sample=model_config.do_sample,
                    early_stopping=True
                )

            decoded = tokenizer.decode(
                summary_ids[0], skip_special_tokens=True)
            summaries.append(decoded.strip())

        full_summary = "\n".join(summaries)
        return self.format_summary(full_summary, style=format_style)

    def summarize_large_text(self, text: str, model_name: str,
                             format_style: str = "bullet") -> str:
        """Handle large text summarization with parallel processing."""
        if model_name == "gemini":
            # For Gemini, we can use its high token limit
            return self.summarize_with_gemini(text)
        elif model_name == "openai":
            # For OpenAI, we can also use its high token limit
            return self.summarize_with_openai(text)
        elif model_name == "openrouter":
            # For OpenRouter, we can use its high token limit
            return self.summarize_with_openrouter(text)
        

        # For other models, split and process in parallel
        if not self.load_model(model_name):
            return f"Failed to load model: {model_name}"

        tokenizer = self.tokenizers[model_name]
        config = MODEL_CONFIGS[model_name]

        chunks = self.split_text_smart(
            text, tokenizer, config.max_input_length)

        if not chunks:
            return "Failed to split text into processable chunks"

        logger.info(f"Split text into {len(chunks)} chunks")

        # Process chunks with timeout protection
        summaries = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_chunk = {
                executor.submit(self.summarize_text, chunk, model_name, "paragraph"): i
                for i, chunk in enumerate(chunks)
            }

            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    summary = future.result(timeout=120)  # 2-minute timeout
                    if summary and not summary.startswith("Summarization error"):
                        summaries.append(summary)
                except concurrent.futures.TimeoutError:
                    logger.error(
                        f"Timeout summarizing chunk {future_to_chunk[future]}")
                except Exception as e:
                    logger.error(f"Error summarizing chunk: {e}")

        if not summaries:
            return "Failed to generate summaries for any chunks"

        # Combine chunk summaries
        combined_summary = "\n".join(summaries)

        # If combined summary is still large, summarize once more
        if len(combined_summary.split()) > 1000:
            logger.info("Combined summary still large, summarizing again")
            return self.summarize_text(combined_summary, model_name, format_style)

        return self.format_summary(combined_summary, format_style)

    def build_knowledge_base(self, text: str):
        """Split text and build in-memory vector index"""
        logger.info(f"📄 Document length: {len(text)}")

        # Smart fallback for very short documents
        if len(text.strip().split()) < 50:
            self.doc_chunks = [text.strip()]
        else:
            # Use tiktoken for splitting instead of embedder
            tokenizer = tiktoken.get_encoding("cl100k_base")
            self.doc_chunks = self.split_text_smart(text, tokenizer, max_tokens=150)

        if not self.doc_chunks:
            logger.warning("⚠️ No chunks were created. Falling back to full text as one chunk.")
            self.doc_chunks = [text.strip()]

        logger.info(f"📦 Chunks created: {len(self.doc_chunks)}")

        # Create vector embeddings for chunks
        self.doc_embeddings = self.embedder.encode(self.doc_chunks, convert_to_tensor=True)
        logger.info(f"✅ Knowledge base created with {len(self.doc_chunks)} chunks.")

    def retrieve_relevant_chunks(self, query: str, top_k=3) -> List[str]:
        """Return top-k relevant chunks for the query"""
        if not self.doc_chunks:
            return []

        query_embedding = self.embedder.encode(query, convert_to_tensor=True)
        hits = util.semantic_search(query_embedding, self.doc_embeddings, top_k=top_k)
        top_chunks = [self.doc_chunks[hit['corpus_id']] for hit in hits[0]]
        return top_chunks

    def answer_question(self, question: str, model_name: str = "openrouter") -> str:
        """Answer question using retrieved context and chosen model"""
        context_chunks = self.retrieve_relevant_chunks(question, top_k=3)
        context = "\n\n".join(context_chunks)

        prompt = (
            "Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        if model_name == "gemini" and self.gemini_available:
            try:
                model = genai.GenerativeModel("gemini-1.5-pro")
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                return f"Gemini QA error: {e}"

        elif model_name == "openai" and self.openai_available:
            try:
                client = openai.OpenAI(api_key=self.openai_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"OpenAI QA error: {e}"

        elif model_name == "openrouter" and self.openrouter_available:
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "mistralai/mistral-7b-instruct",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that answers based on provided context."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }

                response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                        headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            except Exception as e:
                return f"OpenRouter QA error: {e}"

        return "No available model to answer the question."

 
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Document Summarization Tool")
    parser.add_argument(
        "--files", "-f", nargs="+", required=True,
        help="Paths to documents for summarization (PDF, DOCX, TXT)"
    )
    parser.add_argument(
        "--model", "-m", required=True, choices=["gemini", "openai", "openrouter"],
        help="Model to use for summarization"
    )

    parser.add_argument(
        "--format", "-fmt", default="bullet", choices=["bullet", "paragraph", "numbered"],
        help="Output format style"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output file path (if not specified, prints to console)"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API key (if not set in environment variable)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def main():
    """Main entry point for CLI usage."""
    args = parse_args()

    # Set verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize summarizer
    summarizer = DocumentSummarizer(api_key=args.api_key)

    # Process documents
    print(f"Processing {len(args.files)} document(s)...")
    extracted_texts = summarizer.process_documents(args.files)

    # Generate summaries
    results = {}
    for file_path, text in extracted_texts.items():
        print(f"Summarizing: {os.path.basename(file_path)}")
        summary = summarizer.summarize_text(
            text, model_name=args.model, format_style=args.format)
        results[file_path] = summary

    # Output results
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            for file_path, summary in results.items():
                f.write(f"## Summary of {os.path.basename(file_path)}\n\n")
                f.write(summary)
                f.write("\n\n" + "-"*40 + "\n\n")
        print(f"Summaries written to {args.output}")
    else:
        for file_path, summary in results.items():
            print(f"\n{'='*50}")
            print(f"SUMMARY OF: {os.path.basename(file_path)}")
            print(f"{ '='*50}\n")
            print(summary)
            print("\n")


if __name__ == "__main__":
    main()