# Placeholder for additional imports or code
import os
import re
import fitz  # PyMuPDF
import docx
import logging
import nltk
import torch
import concurrent.futures
import argparse
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from dotenv import load_dotenv
import google.generativeai as genai

# Ensure NLTK resources are available
nltk.download("punkt", quiet=True)

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
    "bart": ModelConfig(model_id="facebook/bart-large-cnn", max_input_length=1024),
    "t5-large": ModelConfig(model_id="google/flan-t5-large", max_input_length=1024),
    "t5-base": ModelConfig(model_id="google/flan-t5-base", max_input_length=1024),
    "t5-small": ModelConfig(model_id="google/flan-t5-small", max_input_length=512),
    "gemini": ModelConfig(model_id="google/gemini-1.5-pro", max_input_length=8192)
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
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Initialize model caches
        self.tokenizers = {}
        self.models_loaded = {}
        
        # Configure API (with validation)
        self._configure_api(api_key)
    
    def _configure_api(self, api_key: Optional[str] = None) -> None:
        """Configure the Gemini API with proper error handling."""
        # Try environment variable if not provided
        if not api_key:
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            logger.warning("GEMINI API Key is missing. Gemini model will not be available.")
            self.gemini_available = False
        else:
            try:
                genai.configure(api_key=api_key)
                # Test connection with minimal request
                model = genai.GenerativeModel("gemini-1.5-pro")
                response = model.generate_content("Test")
                if response:
                    self.gemini_available = True
                    logger.info("Successfully connected to Gemini API")
                else:
                    logger.warning("Gemini connection test failed")
                    self.gemini_available = False
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")
                self.gemini_available = False
    
    def load_model(self, model_name: str) -> bool:
        """Load model and tokenizer with error handling."""
        if model_name not in MODEL_CONFIGS:
            logger.error(f"Invalid model. Available: {', '.join(MODEL_CONFIGS.keys())}")
            return False
        
        if model_name == "gemini" and not self.gemini_available:
            logger.error("Gemini API is not configured or unavailable")
            return False
            
        if model_name not in self.tokenizers or model_name not in self.models_loaded:
            try:
                logger.info(f"Loading model: {model_name}...")
                model_config = MODEL_CONFIGS[model_name]
                
                if model_name != "gemini":
                    self.tokenizers[model_name] = AutoTokenizer.from_pretrained(model_config.model_id)
                    self.models_loaded[model_name] = AutoModelForSeq2SeqLM.from_pretrained(
                        model_config.model_id
                    ).to(self.device)
                
                return True
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                return False
        
        return True  # Already loaded
    
    def extract_headings(self, text: str) -> List[str]:
        """Extract structural headings with improved pattern matching."""
        heading_pattern = r"\b(?:" + "|".join(HEADING_CATEGORIES) + r")\b"
        headings = re.findall(heading_pattern, text, re.IGNORECASE)
        
        # De-duplicate and preserve order
        seen = set()
        unique_headings = [h for h in headings if not (h.lower() in seen or seen.add(h.lower()))]
        
        return unique_headings if unique_headings else ["General Summary"]
    
    def format_summary(self, text: str, style: str = "bullet") -> str:
        """Format text into structured output with multiple style options."""
        if style == "bullet":
            bullet_points = [f"• {point.strip()}" for point in text.split("\n") if point.strip()]
            return "\n".join(bullet_points)
        elif style == "paragraph":
            return text
        elif style == "numbered":
            points = [point.strip() for point in text.split("\n") if point.strip()]
            return "\n".join([f"{i+1}. {point}" for i, point in enumerate(points)])
        else:
            return text
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from various file formats with improved error handling."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return ""
            
        ext = os.path.splitext(file_path)[-1].lower()
        
        try:
            if ext == ".pdf":
                return self._extract_text_from_pdf(file_path)
            elif ext == ".docx":
                return self._extract_text_from_docx(file_path)
            elif ext == ".txt":
                return self._extract_text_from_txt(file_path)
            else:
                logger.error(f"Unsupported file format: {ext}")
                return ""
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return ""
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF with improved memory handling."""
        try:
            text_chunks = []
            with fitz.open(file_path) as pdf:
                for page_num, page in enumerate(pdf):
                    try:
                        text_chunks.append(page.get_text("text"))
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
            
            return "\n".join(text_chunks)
        except Exception as e:
            logger.error(f"PDF Extraction Error: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
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
        
        logger.error(f"Could not decode file with any of the attempted encodings")
        return ""
    
    def process_documents(self, files: List[str]) -> Dict[str, str]:
        """Process multiple documents with parallel execution."""
        if not files:
            logger.warning("No files provided for processing")
            return {}
            
        extracted_texts = {}
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(self.extract_text, file): file for file in files}
            
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
        if not text.strip():
            return []
            
        sentences = nltk.sent_tokenize(text)
        chunks, current_chunk = [], []
        token_count = 0

        for sentence in sentences:
            # Skip empty sentences
            if not sentence.strip():
                continue
                
            sentence_tokens = len(tokenizer.encode(sentence, add_special_tokens=False))

            if token_count + sentence_tokens <= max_tokens:
                current_chunk.append(sentence)
                token_count += sentence_tokens
            else:
                chunks.append(" ".join(current_chunk))
                
                # Add overlap by keeping some sentences from the previous chunk
                overlap_sentences = []
                overlap_tokens = 0
                
                # Add sentences from the end of previous chunk until we reach overlap limit
                for s in reversed(current_chunk):
                    s_tokens = len(tokenizer.encode(s, add_special_tokens=False))
                    if overlap_tokens + s_tokens <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                # Start a new chunk with overlap sentences plus current sentence
                current_chunk = overlap_sentences + [sentence]
                token_count = overlap_tokens + sentence_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
    
    def summarize_with_gemini(self, text: str) -> str:
        """Generate summary using Gemini with improved prompting."""
        if not self.gemini_available:
            return "Gemini API is not configured or unavailable"
            
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            
            prompt = (
                "Provide a comprehensive summary of the following document. "
                "Focus on key facts, findings, and conclusions. "
                "Organize the summary in a clear structure. "
                "Keep the Headings bold style. "
                "Use bullet points for clarity. "
                "Use a formal tone. "
                "keep the headings in bold style. and centerd "
                "Avoid unnecessary jargon. "
                
                "Text to summarize:\n\n"
                f"{text}"
            )
            
            response = model.generate_content(prompt)
            return response.text if response.text else "No response from Gemini."
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"Gemini API error: {str(e)}"
    
    def summarize_text(self, text: str, model_name: str = "gemini", 
                       format_style: str = "bullet") -> str:
        """Generate a summary with specified model and formatting."""
        if not text.strip():
            return "No text found for summarization."

        logger.info(f"Using model: {model_name}")
        if model_name == "gemini":
            if not self.gemini_available:
                return "Gemini model is not available or API is not configured."
            return self.format_summary(self.summarize_with_gemini(text), style=format_style)

        # For transformer models (BART, T5, etc.)
        if not self.load_model(model_name):
            return "Model loading failed. Cannot summarize."

        tokenizer = self.tokenizers[model_name]
        model = self.models_loaded[model_name]
        model_config = MODEL_CONFIGS[model_name]

        chunks = self.split_text_smart(text, tokenizer, max_tokens=model_config.max_input_length)
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

            decoded = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            summaries.append(decoded.strip())

        full_summary = "\n".join(summaries)
        return self.format_summary(full_summary, style=format_style)


        # Extract headings and format summary
        headings = self.extract_headings(text)
        sections = []
        
        # If we have multiple headings, attempt to segment the summary
        if len(headings) > 1 and len(raw_summary.split()) > 30 * len(headings):
            # Rough segmentation based on summary length and number of headings
            sentences = nltk.sent_tokenize(raw_summary)
            sentences_per_section = max(2, len(sentences) // len(headings))
            
            for i, heading in enumerate(headings):
                start_idx = i * sentences_per_section
                end_idx = (i + 1) * sentences_per_section if i < len(headings) - 1 else len(sentences)
                section_text = " ".join(sentences[start_idx:end_idx])
                formatted_section = self.format_summary(section_text, format_style)
                sections.append(f"**{heading}**\n{formatted_section}")
        else:
            # Single section if we can't meaningfully segment
            formatted_summary = self.format_summary(raw_summary, format_style)
            sections.append(f"**{headings[0]}**\n{formatted_summary}")
        
        return "\n\n".join(sections)
    
    def summarize_large_text(self, text: str, model_name: str = "gemini", 
                             format_style: str = "bullet") -> str:
        """Handle large text summarization with parallel processing."""
        if model_name == "gemini":
            # For Gemini, we can use its high token limit
            return self.summarize_with_gemini(text)
        
        # For other models, split and process in parallel
        if not self.load_model(model_name):
            return f"Failed to load model: {model_name}"
        
        tokenizer = self.tokenizers[model_name]
        config = MODEL_CONFIGS[model_name]
        
        chunks = self.split_text_smart(text, tokenizer, config.max_input_length)
        
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
                    logger.error(f"Timeout summarizing chunk {future_to_chunk[future]}")
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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Document Summarization Tool")
    parser.add_argument(
        "--files", "-f", nargs="+", required=True,
        help="Paths to documents for summarization (PDF, DOCX, TXT)"
    )
    parser.add_argument(
        "--model", "-m", default="gemini", choices=list(MODEL_CONFIGS.keys()),
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
        help="Gemini API key (if not set in environment variable)"
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
        summary = summarizer.summarize_text(text, model_name=args.model, format_style=args.format)
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
            print(f"{'='*50}\n")
            print(summary)
            print("\n")


if __name__ == "__main__":
    main()