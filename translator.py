import streamlit as st
import fitz  # PyMuPDF for extracting text from PDFs
import pdfplumber  # Extract text from image-based PDFs
import pytesseract  # OCR for images
from PIL import Image
import io
import os
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Set Tesseract path if needed (Windows users may need this)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Function to extract text from PDF using PyMuPDF
def extract_text_from_pdf(file_source):
    try:
        if isinstance(file_source, str):  # If file path
            if not os.path.exists(file_source):
                raise FileNotFoundError(f"File not found: {file_source}")
            doc = fitz.open(file_source)
        else:  # If uploaded file (BytesIO)
            doc = fitz.open(stream=file_source.read(), filetype="pdf")

        text = "\n".join([page.get_text("text") for page in doc])
        doc.close()

        return text if text.strip() else None  # Return None if no text found

    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return None

# Function to perform OCR on image-based PDFs using pdfplumber
def ocr_pdf(file_source):
    try:
        ocr_text = ""

        if isinstance(file_source, str):
            pdf = pdfplumber.open(file_source)
        else:
            pdf = pdfplumber.open(io.BytesIO(file_source.read()))

        for page in pdf.pages:
            # Extract images from the page
            for img in page.images:
                image = Image.open(io.BytesIO(img["stream"].getvalue()))
                text = pytesseract.image_to_string(image)
                ocr_text += text + "\n"

        pdf.close()
        return ocr_text if ocr_text.strip() else None

    except Exception as e:
        st.error(f"Error during OCR: {e}")
        return None

# Function to translate extracted text
def translate_text(text, target_language):
    if not text.strip():
        return "⚠️ No text found for translation."

    translator = GoogleTranslator(source="auto", target=target_language)
    
    try:
        translated_text = translator.translate(text)
        return translated_text if translated_text else "⚠️ Translation failed."
    except Exception as e:
        st.error(f"Error during translation: {e}")
        return "⚠️ Translation error."

# Function to create a translated PDF
def create_translated_pdf(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 12)

    y_position = 750  # Initial position for writing text

    for line in text.split("\n"):
        if y_position < 50:  # Start new page if needed
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y_position = 750
        pdf.drawString(50, y_position, line)
        y_position -= 20

    pdf.save()
    buffer.seek(0)
    return buffer

# Streamlit UI
st.title("📄 PDF Translator (With OCR)")

# Option 1: File Uploader
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

# Option 2: File Path Input
file_path = st.text_input("Or enter the PDF file path manually:")

# Select Target Language
target_language = st.selectbox(
    "Select target language",
    ["en", "fr", "es", "de", "zh", "hi", "ar"],  # Added English (en)
    format_func=lambda x: {
        "en": "English",
        "fr": "French",
        "es": "Spanish",
        "de": "German",
        "zh": "Chinese",
        "hi": "Hindi",
        "ar": "Arabic",
    }[x]  # Display full language names
)

# Determine which input to use
pdf_source = None
if uploaded_file:
    pdf_source = uploaded_file
    st.success("Using uploaded file.")
elif file_path:
    if os.path.exists(file_path):
        pdf_source = file_path
        st.success("Using file from path.")
    else:
        st.error("⚠️ File path is invalid. Please check and try again.")

if pdf_source:
    if st.button("Translate PDF"):
        try:
            with st.spinner("Processing..."):
                # Step 1: Try extracting text normally
                extracted_text = extract_text_from_pdf(pdf_source)

                # Step 2: If no text found, use OCR
                if not extracted_text:
                    st.warning("⚠️ No text found, trying OCR...")
                    extracted_text = ocr_pdf(pdf_source)

                if extracted_text:
                    st.text_area("Extracted Text Preview (First 500 chars):", extracted_text[:500])

                    translated_text = translate_text(extracted_text, target_language)
                    st.text_area("Translated Text Preview (First 500 chars):", translated_text[:500])

                    translated_pdf = create_translated_pdf(translated_text)

                    st.success("✅ Translation completed!")
                    st.download_button(
                        label="📥 Download Translated PDF",
                        data=translated_pdf,
                        file_name="translated_document.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.error("⚠️ No text could be extracted from PDF, even with OCR.")

        except FileNotFoundError as e:
            st.error(f"⚠️ Error: {e}")
