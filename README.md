

# 📄 Document Summarizer

A powerful and flexible **Document Summarizer** built with **Python**, **FastAPI**, and **React.js**.  
It supports summarizing documents (PDF, DOCX, TXT) using **Google Gemini**, with structured outputs, adjustable summary lengths, and advanced features like **Sentiment Analysis**, **Named Entity Recognition (NER)**, and **Multi-Language Translation**.

---

## ✨ Features

- **Multi-Document Summarization**  
  ➔ Upload and summarize multiple PDFs, DOCX, or TXT files.

- **Topic-Aware Summarization**  
  ➔ Structured, section-wise summaries for better readability.

- **Key Information Extraction**  
  ➔ Extract important names, quotes, and entities using NER.

- **Real-Time Summarization (Streaming)**  
  ➔ Progressive summarization for large documents.

- **User-Friendly Interface**  
  ➔ Upload, preview, and print summarized documents.

---

## 🛠️ Tech Stack

| Frontend  | Backend  | AI Model |
|:---------:|:--------:|:--------:|
| React.js  | FastAPI   | Google Gemini |

---

## 📦 Installation

### Backend (FastAPI)

```bash
git clone https://github.com/your-username/document-summarizer.git
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (React.js)

```bash
cd frontend
npm install
npm start
```

---

## 🧩 Backend Dependencies

- **FastAPI** – API framework
- **Uvicorn** – ASGI server
- **Pydantic** – Data validation
- **pdfplumber** – PDF text extraction
- **pdfminer.six** – Advanced PDF parsing
- **pymupdf** – Lightweight PDF handling
- **python-docx** – DOCX text extraction
- **nltk** – Natural Language Processing (NER, Sentiment Analysis)
- **transformers** – HuggingFace transformers (for future extensions if needed)
- **torch** – PyTorch backend for models
- **openai** – (Optional) OpenAI model usage (future-proof)
- **google-generativeai** – Google Gemini API
- **dotenv** – Environment variable management
- **requests** – HTTP requests
- **services** – Custom service layer
- **python-multipart** – Handling file uploads

---

## 📂 Folder Structure

```
document-summarizer/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── utils/
│   ├── main.py
│   ├── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   ├── package.json
├── README.md
```

---

## ⚙️ Core Functionality

- **Text Extraction** from PDFs, DOCX, and TXT files.
- **Smart Chunking** for better summarization of long documents.
- **Gemini Model Summarization** for generating high-quality summaries.
- **Summary Download & Printing** options available.

---

## 🚀 Future Improvements

- Add User Authentication (Login/Signup)
- Document Summarization History
- Support for OCR (Image-to-Text Summarization)
- Offline Mode (without API dependency)

---

## 📢 Demo

> 🔗 [Live Demo Link (Coming Soon)](https://your-demo-link.com)

---

## 🙌 Credits

- Google Gemini API
- FastAPI
- React.js
- HuggingFace Transformers

---

## 📬 Contact
- **Email**: harshmangal286@gmail.com
