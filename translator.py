import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import io
from PIL import Image
import pytesseract

# Load environment variables
load_dotenv()

# Initialize OpenAI client with the API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Function to extract text from PDF (handles both text-based and image-based PDFs)
def extract_text_from_pdf(uploaded_file):
    pdf_text = ""
    try:
        pdf_reader = PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            try:
                pdf_text += page.extract_text()
            except:
                st.warning("Could not extract text directly from page. Attempting OCR...")
                # If direct text extraction fails, attempt OCR
                try:
                    # Convert PDF page to image
                    image = Image.open(io.BytesIO(page.extract_image().data)) # corrected line

                    # Perform OCR using Tesseract
                    pdf_text += pytesseract.image_to_string(image)
                except Exception as ocr_err:
                    st.error(f"OCR failed on this page: {ocr_err}")
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

    return pdf_text

# Function to translate text using OpenAI
def translate_text(text, target_language="English"):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Or any other suitable model
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the following text to {target_language}."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error translating text: {e}")
        return None

# Streamlit app
def main():
    st.title("PDF Translator")

    # File uploader
    uploaded_file = st.file_uploader("Upload your PDF file", type="pdf")

    if uploaded_file is not None:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(uploaded_file)

        if pdf_text:
            # Target language selection
            target_language = st.selectbox("Select target language", ["English", "Spanish", "French", "German"])

            # Translate the text
            translated_text = translate_text(pdf_text, target_language)

            if translated_text:
                # Display translated text
                st.subheader("Translated Text:")
                st.write(translated_text)

                # Offer download button
                st.download_button(
                    label="Download Translated Text",
                    data=translated_text.encode('utf-8'),
                    file_name="translated_document.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
