import io
import streamlit as st
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from googletrans import Translator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# Set the Poppler path (update this path if your bin folder is elsewhere)
POPPLER_PATH = r"C:\py\Release-24.08.0-0\bin"

def extract_text_from_pdf(file_bytes, poppler_path=None):
    """
    Extract text from each page of the PDF.
    For pages with no extractable text, apply OCR.
    Returns a list of strings (one per page).
    """
    extracted_pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                extracted_pages.append(text)
            else:
                st.info(f"Page {i+1}: No text detected, applying OCR...")
                try:
                    images = convert_from_bytes(
                        file_bytes,
                        first_page=i+1,
                        last_page=i+1,
                        poppler_path=poppler_path
                    )
                except Exception as e:
                    st.error(f"Error converting page {i+1}: {e}")
                    images = []
                if images:
                    ocr_text = pytesseract.image_to_string(images[0])
                    extracted_pages.append(ocr_text)
                else:
                    extracted_pages.append("")
    return extracted_pages

def translate_text_list(text_list, target_lang):
    """
    Translate each string in text_list to target_lang using googletrans.
    """
    translator = Translator()
    translated_pages = []
    for i, text in enumerate(text_list):
        try:
            translation = translator.translate(text, dest=target_lang)
            translated_pages.append(translation.text)
        except Exception as e:
            st.error(f"Translation failed on page {i+1}: {e}")
            translated_pages.append(text)
    return translated_pages

def create_pdf(translated_pages):
    """
    Generate a PDF with each translated page on a separate PDF page.
    Note: The original formatting is approximated by preserving line breaks.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 0.5 * inch

    for page_text in translated_pages:
        text_object = c.beginText(margin, height - margin)
        text_object.setFont("Helvetica", 10)
        # Split text into lines (you may improve text wrapping as needed)
        lines = page_text.split('\n')
        for line in lines:
            # If the text reaches the bottom margin, start a new page section.
            if text_object.getY() < margin:
                c.drawText(text_object)
                c.showPage()
                text_object = c.beginText(margin, height - margin)
                text_object.setFont("Helvetica", 10)
            text_object.textLine(line)
        c.drawText(text_object)
        c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit App ---
st.title("PDF Translator")
st.markdown("""
This tool allows you to upload a PDF (text-based or scanned) and translate its content into your desired language.
""")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

# Allow the user to select the target language (using ISO codes, e.g., 'en' for English)
target_language = st.selectbox(
    "Select target language", 
    options=["en", "es", "fr", "de", "it"],
    index=0,
    help="Select the language code for translation (default is English 'en')"
)

if uploaded_file:
    file_bytes = uploaded_file.read()

    st.info("Extracting text from PDF...")
    extracted_pages = extract_text_from_pdf(file_bytes, poppler_path=POPPLER_PATH)
    
    st.info("Translating text...")
    translated_pages = translate_text_list(extracted_pages, target_language)
    
    st.info("Generating translated PDF...")
    translated_pdf_buffer = create_pdf(translated_pages)
    
    st.success("Translation complete!")
    st.download_button(
        label="Download Translated PDF",
        data=translated_pdf_buffer,
        file_name="translated.pdf",
        mime="application/pdf"
    )
