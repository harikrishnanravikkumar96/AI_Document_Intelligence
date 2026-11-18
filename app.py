
import streamlit as st
import fitz
import sqlite3
import json
import re
import io
import shutil
import requests
import base64
from datetime import datetime
from PIL import Image

# ---------------- CONFIGURATION ----------------

DB = "documents.db"

st.set_page_config(
    page_title="AI Document Intelligence",
    page_icon="📄",
    layout="wide"
)

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            extracted_text TEXT,
            fields TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_document(filename, text, fields):
    conn = sqlite3.connect(DB)

    conn.execute("""
        INSERT INTO documents
        (filename, extracted_text, fields, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        filename,
        text,
        json.dumps(fields, ensure_ascii=False),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


# ---------------- OCR ENGINE ----------------



def run_ocr(image):
    """
    Run Arabic + English OCR directly through Tesseract.
    Does not depend on pytesseract or pandas.
    """

    import subprocess
    import io
    from pathlib import Path

    tesseract_exe = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    tessdata_path = Path(__file__).parent / "tessdata"

    try:
        # Convert image to PNG bytes
        image_buffer = io.BytesIO()
        image.convert("RGB").save(image_buffer, format="PNG")
        image_bytes = image_buffer.getvalue()

        command = [
            tesseract_exe,
            "stdin",
            "stdout",
            "-l", "ara+eng",
            "--tessdata-dir", str(tessdata_path),
            "--psm", "3"
        ]

        result = subprocess.run(
            command,
            input=image_bytes,
            capture_output=True,
            timeout=120
        )

        if result.returncode != 0:
            return (
                "OCR error: "
                + result.stderr.decode("utf-8", errors="replace")
            )

        return result.stdout.decode(
            "utf-8",
            errors="replace"
        ).strip()

    except Exception as e:
        return f"OCR error: {str(e)}"



def extract_pdf(file):
    """
    Extract PDF content using Arabic + English Tesseract OCR.
    Falls back to embedded PDF text if OCR fails.
    """

    try:
        pdf_bytes = file.getvalue()

        doc = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        extracted_pages = []

        for page_number, page in enumerate(doc, start=1):

            # Render PDF page as a high-resolution image
            pix = page.get_pixmap(
                matrix=fitz.Matrix(4, 4),
                alpha=False
            )

            image = Image.open(
                io.BytesIO(pix.tobytes("png"))
            ).convert("RGB")

            # Always run OCR, even if embedded PDF text exists
            ocr_text = run_ocr(image)

            # Use OCR result when available
            if ocr_text and not ocr_text.startswith("OCR error:"):
                page_text = ocr_text
            else:
                # Fallback to embedded PDF text
                page_text = page.get_text("text").strip()

            extracted_pages.append(
                f"\n--- Page {page_number} ---\n{page_text}"
            )

        doc.close()

        return "\n".join(extracted_pages).strip()

    except Exception as e:
        return f"PDF extraction error: {str(e)}"



def extract_image(file):
    try:
        image = Image.open(
            io.BytesIO(file.getvalue())
        ).convert("RGB")

        return run_ocr(image)

    except Exception as e:
        return f"Image processing error: {str(e)}"


# ---------------- INFORMATION EXTRACTION ----------------

def extract_fields(text):

    fields = {}

    patterns = {
        "Passport Number":
            r"\bP[A-Z0-9]{6,12}\b",

        "Tenancy Contract":
            r"\bTWT-[A-Z0-9-]+\b",

        "Date":
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",

        "Salary":
            r"\b\d[\d,]*(?=\s*(?:درهم|AED))"
    }

    for name, pattern in patterns.items():

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        fields[name] = (
            match.group(0) if match else ""
        )

    return fields


# ---------------- LOCAL AI EXTRACTION ----------------


def ai_extract(text):

    prompt = f"""
You are a highly accurate document information extraction system.

Your task is to extract information from the OCR text of a document.
The document may contain Arabic and English text.
Arabic text is written from right to left.

IMPORTANT EXTRACTION RULES:

1. Extract ONLY information explicitly present in the document.
2. Never guess, assume, or invent information.
3. Do not confuse similar-looking Arabic or English digits.
4. Preserve names, passport numbers, ID numbers and reference numbers exactly as written.
5. Do not change dates or numbers to what you think they should be.
6. Do not confuse the sponsor with the sponsored person.
7. Use the surrounding field label to identify each value.
8. If a value is unclear or unreadable, return an empty string.
9. Do not use outside knowledge to complete missing information.
10. Return valid JSON only. No explanations or Markdown.

FIELD DEFINITIONS:

- sponsor_name: Name of the person sponsoring the application.
- nationality: Sponsor's nationality.
- sponsor_id: Sponsor's identification number.
- employer: Sponsor's employer or company.
- job_title: Sponsor's occupation or job title.
- salary: Sponsor's stated salary.
- tenancy_contract: Tenancy contract reference number.
- sponsored_person: Full name of the person being sponsored.
- relationship: Relationship between sponsor and sponsored person.
- date_of_birth: Sponsored person's date of birth.
- place_of_birth: Sponsored person's place of birth.
- passport_number: Sponsored person's passport number.
- passport_expiry: Passport expiry date.
- marital_status: Sponsored person's marital status.
- qualification: Sponsored person's educational qualification.

OUTPUT FORMAT:

{{
    "sponsor_name": "",
    "nationality": "",
    "sponsor_id": "",
    "employer": "",
    "job_title": "",
    "salary": "",
    "tenancy_contract": "",
    "sponsored_person": "",
    "relationship": "",
    "date_of_birth": "",
    "place_of_birth": "",
    "passport_number": "",
    "passport_expiry": "",
    "marital_status": "",
    "qualification": ""
}}

DOCUMENT OCR TEXT:
------------------
{text[:12000]}
------------------

Return only the JSON object.
"""

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0
                }
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        extracted_data = json.loads(result["response"])

        return extracted_data

    except requests.exceptions.ConnectionError:
        return {
            "error": "Ollama is not running. Start Ollama and retry."
        }

    except requests.exceptions.Timeout:
        return {
            "error": "AI extraction timed out. Try again."
        }

    except json.JSONDecodeError:
        return {
            "error": "AI returned invalid JSON. Please retry."
        }

    except Exception as e:
        return {
            "error": str(e)
        }



def ai_extract_pdf(file):

    try:
        doc = fitz.open(
            stream=file.getvalue(),
            filetype="pdf"
        )

        page = doc[0]

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
        )

        image_bytes = pix.tobytes("png")
        doc.close()

        image_base64 = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        prompt = """
You are a professional Arabic and English document extraction system.

TASK:
Read the supplied document image carefully and extract information
from the actual visible text.

IMPORTANT RULES:
1. Arabic is read from right to left.
2. Never guess or invent missing information.
3. Do not confuse labels with their neighboring values.
4. Preserve the original numbers exactly as printed.
5. Do not convert Gregorian dates into Hijri dates or vice versa.
6. Do not confuse passport numbers with tenancy contract numbers.
7. Preserve currency and salary units exactly.
8. If a field cannot be read, return an empty string.
9. Do not use outside knowledge.
10. Check every value against the visible document before responding.

Return valid JSON only, using these fields:

{
  "sponsor_name": "",
  "nationality": "",
  "sponsor_id": "",
  "employer": "",
  "job_title": "",
  "salary": "",
  "tenancy_contract": "",
  "sponsored_person": "",
  "relationship": "",
  "date_of_birth": "",
  "place_of_birth": "",
  "passport_number": "",
  "passport_expiry": "",
  "marital_status": "",
  "qualification": ""
}

For each field, extract only the value associated with its
corresponding label. Never substitute a different field's value.
"""

        response = requests.post(
            "http://localhost:11434/api/generate",

            json={
                "model": "gemma3:latest",
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "format": "json"
            },

            timeout=180
        )

        response.raise_for_status()

        return json.loads(
            response.json()["response"]
        )

    except Exception as e:

        return {
            "error": str(e)
        }

# ---------------- CER EVALUATION ----------------

def edit_distance(a, b):

    previous = list(range(len(b) + 1))

    for i, char_a in enumerate(a, 1):

        current = [i]

        for j, char_b in enumerate(b, 1):

            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (char_a != char_b)
                )
            )

        previous = current

    return previous[-1]


def calculate_cer(actual, predicted):

    if not actual:
        return None

    errors = edit_distance(actual, predicted)

    return errors / len(actual)


# ---------------- APPLICATION ----------------

init_db()

st.title("📄 AI Document Intelligence")

st.caption(
    "OCR | AI Information Extraction | "
    "Document Processing | Search"
)

tab1, tab2, tab3 = st.tabs([
    "📤 Upload & Extract",
    "🔍 Search Documents",
    "📊 Evaluation"
])


# =================================================
# TAB 1 - UPLOAD AND EXTRACTION
# =================================================

with tab1:

    st.subheader("Upload Document")

    uploaded = st.file_uploader(
        "Upload PDF, PNG or JPG",
        type=["pdf", "png", "jpg", "jpeg"]
    )

    if uploaded is not None:

        if uploaded.type == "application/pdf":

            text = extract_pdf(uploaded)

            st.info("PDF processing completed.")

        else:

            text = extract_image(uploaded)

            st.info("Image processing completed.")

        if text.startswith(
            ("PDF extraction error:", "Image processing error:")
        ):

            st.error(text)

        elif text.startswith("OCR unavailable:"):

            st.warning(text)

        elif text:

            st.success("Text extraction completed.")

        else:

            st.warning(
                "No text extracted. OCR may be required."
            )

        st.metric(
            "Extracted Character Count",
            len(text)
        )

        st.subheader("Extracted Document Text")

        edited_text = st.text_area(
            "Review and correct extracted text",
            value=text,
            height=250,
            key="document_text"
        )

        # Automatic information extraction

        fields = extract_fields(edited_text)

        st.subheader("Detected Information")

        for key, value in fields.items():

            fields[key] = st.text_input(
                key,
                value=value,
                key="field_" + key
            )

        # AI extraction

        st.subheader("AI Information Extraction")

        if st.button("🤖 Extract Using Gemma 3 Vision"):

            with st.spinner(
                "AI is analyzing the document..."
            ):

                result = ai_extract_pdf(uploaded)

                st.session_state["ai_result"] = result

        if "ai_result" in st.session_state:

            result = st.session_state["ai_result"]

            st.write("AI Extraction Result")

            st.json(result)

            if "error" not in result:

                fields.update(result)

        # Save document

        if st.button("💾 Save Document"):

            if not edited_text.strip():

                st.error("Cannot save an empty document.")

            else:

                save_document(
                    uploaded.name,
                    edited_text,
                    fields
                )

                st.success(
                    "Document saved successfully in SQLite!"
                )


# =================================================
# TAB 2 - DOCUMENT SEARCH
# =================================================

with tab2:

    st.subheader("Search Documents")

    query = st.text_input(
        "Search by filename, name, passport number or content"
    )

    conn = sqlite3.connect(DB)

    if query.strip():

        search = f"%{query}%"

        results = conn.execute("""
            SELECT id, filename, extracted_text,
                   fields, created_at
            FROM documents
            WHERE filename LIKE ?
               OR extracted_text LIKE ?
               OR fields LIKE ?
            ORDER BY id DESC
        """, (search, search, search)).fetchall()

    else:

        results = conn.execute("""
            SELECT id, filename, extracted_text,
                   fields, created_at
            FROM documents
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    st.metric(
        "Documents Found",
        len(results)
    )

    for row in results:

        with st.expander(
            f"{row[1]} | Document ID: {row[0]}"
        ):

            st.write("Uploaded:", row[4])

            st.text_area(
                "Extracted Content",
                row[2],
                height=150,
                key=f"search_text_{row[0]}"
            )

            try:

                st.json(json.loads(row[3]))

            except Exception:

                st.write(row[3])


# =================================================
# TAB 3 - MODEL EVALUATION
# =================================================

with tab3:

    st.subheader("OCR Model Evaluation")

    st.write(
        "Compare manually verified ground truth "
        "against extracted text."
    )

    actual = st.text_area(
        "Ground Truth Text"
    )

    predicted = st.text_area(
        "Predicted Extracted Text"
    )

    if st.button("Calculate Evaluation Metrics"):

        if not actual.strip():

            st.warning(
                "Please enter ground truth text."
            )

        else:

            cer = calculate_cer(
                actual,
                predicted
            )

            accuracy = max(0, 1 - cer)

            col1, col2 = st.columns(2)

            col1.metric(
                "Character Error Rate",
                f"{cer:.2%}"
            )

            col2.metric(
                "Approximate Character Accuracy",
                f"{accuracy:.2%}"
            )

            st.caption(
                "Accuracy is calculated as 1 - CER. "
                "This is a character-level metric, "
                "not field extraction accuracy."
            )


# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "AI Document Intelligence | "
    "Python | Streamlit | PyMuPDF | "
    "Tesseract OCR | Ollama | SQLite"
)
