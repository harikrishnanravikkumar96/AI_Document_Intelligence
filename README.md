# AI Document Intelligence

**OCR | AI Information Extraction | Document Processing | Search**

## Project Overview

AI Document Intelligence is a Python-based application designed to automate document processing.

Users can upload PDF documents, extract text from scanned documents using OCR, identify important information using an AI language model, and search previously processed documents.

The application supports Arabic and English text extraction.

## Key Features

### 1. Upload & Extract
- Upload PDF documents.
- Process PDF pages.
- Extract text from scanned documents.

### 2. OCR Text Extraction
- Uses Tesseract OCR.
- Supports Arabic and English language recognition.
- Uses PyMuPDF to process and render PDF pages.

### 3. AI Information Extraction
- Uses Ollama with Llama 3.1.
- Extracts important information from document text.
- Returns structured JSON output.
- Supports fields such as names, nationality, employer, salary, passport details and dates.

### 4. Document Search & Evaluation
- Stores document information using SQLite.
- Allows users to search previously processed documents.
- Provides an evaluation interface to review extraction results.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Programming Language | Python |
| PDF Processing | PyMuPDF |
| OCR Engine | Tesseract OCR |
| AI Model Runtime | Ollama |
| Language Model | Llama 3.1 |
| Database | SQLite |
| Output Format | JSON |

## Application Workflow

1. User uploads a PDF document.
2. PyMuPDF processes the PDF pages.
3. Tesseract OCR extracts Arabic and English text.
4. Extracted text is passed to the Llama 3.1 model through Ollama.
5. AI identifies important information and generates structured JSON.
6. Extracted information is stored in SQLite.
7. Users can search and review processed documents.

## Installation and Setup

### Prerequisites

- Python 3.11
- Git
- Ollama
- Tesseract OCR
- Arabic and English Tesseract language data

### 1. Clone the repository

```bash
git clone https://github.com/harikrishnanravikkumar96/AI_Document_Intelligence.git
cd AI_Document_Intelligence
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Ollama

Install Ollama and download the model:

```bash
ollama pull llama3.1:8b
```

Make sure Ollama is running before starting the application.

### 5. Configure Tesseract OCR

Install Tesseract OCR and ensure Arabic (`ara`) and English (`eng`) language data are available.

The application must be configured with the correct Tesseract executable and language-data paths for your system.

### 6. Run the application

```bash
python -m streamlit run app.py
```

The application will open in your browser.

## Project Objective

The objective is to reduce manual document processing, automate information extraction, and make document information easier to search and access.

## Current Limitations and Future Improvements

- Improve Arabic OCR accuracy, particularly for right-to-left text and numbers.
- Add field-level confidence scoring.
- Add human verification for uncertain extracted information.
- Improve validation of dates, identification numbers and passport details.
- Extend support to additional document formats.

## Developer

**Harikrishnan Kala Ravikkumar**

GitHub: https://github.com/harikrishnanravikkumar96

---

*This project is developed as an AI-powered document processing and information extraction application.*
