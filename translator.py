import streamlit as st
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = "\n".join([page.get_text("text") for page in doc])
    return text

# Function to translate text
def translate_text(text, target_language):
    translator = GoogleTranslator(source="auto", target=target_language)
    return translator.translate(text)

# Function to create a translated PDF
def create_translated_pdf(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 12)

    y_position = 750  # Initial Y position for text

    for line in text.split("\n"):
        if y_position < 50:  # If close to bottom, start a new page
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y_position = 750
        pdf.drawString(50, y_position, line)
        y_position -= 20

    pdf.save()
    buffer.seek(0)
    return buffer

# Streamlit UI
st.title("PDF Translator")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
target_language = st.selectbox("Select target language", ["fr", "es", "de", "zh", "hi", "ar"])

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    if st.button("Translate PDF"):
        with st.spinner("Translating..."):
            extracted_text = extract_text_from_pdf(uploaded_file)
            translated_text = translate_text(extracted_text, target_language)

            translated_pdf = create_translated_pdf(translated_text)

            st.success("Translation completed!")
            st.download_button(
                label="Download Translated PDF",
                data=translated_pdf,
                file_name="translated_document.pdf",
                mime="application/pdf",
            )
