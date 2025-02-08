import streamlit as st
import fitz  # PyMuPDF for extracting text from PDFs
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import os

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    with fitz.open(file_path) as doc:
        text = "\n".join([page.get_text("text") for page in doc])
    return text

# Function to translate extracted text
def translate_text(text, target_language):
    translator = GoogleTranslator(source="auto", target=target_language)
    return translator.translate(text)

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
st.title("📄 PDF Translator")

# Option 1: File Uploader
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

# Option 2: File Path Input
file_path = st.text_input("Or enter the PDF file path manually:")

# Select Target Language
target_language = st.selectbox("Select target language", ["fr", "es", "de", "zh", "hi", "ar"])

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
        st.error("File path is invalid. Please check and try again.")

if pdf_source:
    if st.button("Translate PDF"):
        with st.spinner("Processing..."):
            if isinstance(pdf_source, str):  # If file path is used
                extracted_text = extract_text_from_pdf(pdf_source)
            else:  # If uploaded file is used
                extracted_text = extract_text_from_pdf(pdf_source)

            translated_text = translate_text(extracted_text, target_language)
            translated_pdf = create_translated_pdf(translated_text)

            st.success("✅ Translation completed!")
            st.download_button(
                label="📥 Download Translated PDF",
                data=translated_pdf,
                file_name="translated_document.pdf",
                mime="application/pdf",
            )
