import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
import re
import time
import base64
import tempfile
import zipfile

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Fallback: automatically install chromedriver if needed
import chromedriver_autoinstaller

# ----------------------------------------------
# Custom User-Agent per SEC rules
# ----------------------------------------------
HEADERS = {
    "User-Agent": "MSCI EDGAR Scraper (Contact: suren.surya@msci.com)"
}

def sanitize_filename(name):
    """Remove characters that are not allowed in file/folder names."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def fetch_sec_json(cik_str, max_retries=3, delay=2):
    """
    Given a zero-padded CIK string (e.g., '0001156375'),
    fetch the SEC JSON from the submissions endpoint.
    """
    base_url = "https://data.sec.gov/submissions/CIK{}.json"
    url = base_url.format(cik_str)
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.warning(f"Attempt {attempt}: CIK JSON fetch returned {resp.status_code} for {url}")
        except Exception as ex:
            st.warning(f"Attempt {attempt}: Error fetching {url}: {ex}")
        
        if attempt < max_retries:
            time.sleep(delay)
    
    return None

def zero_pad_cik(cik):
    """Ensures the CIK is a zero-padded string of length 10."""
    try:
        val = int(cik)
        return f"{val:010d}"
    except ValueError:
        return str(cik).rjust(10, "0")

def create_driver():
    """
    Attempts to create and return a Selenium Chrome WebDriver instance using multiple methods.
    First it tries using Selenium's Service with webdriver-manager.
    If that fails, it falls back to using chromedriver_autoinstaller.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--user-agent=MSCI EDGAR Scraper (Contact: suren.surya@msci.com)')
    
    # If necessary, set the binary location for Chrome/Chromium.
    # Uncomment and adjust the following line if your deployment environment requires it.
    # options.binary_location = '/usr/bin/chromium-browser'
    
    try:
        st.write("Trying to create Chrome driver using webdriver-manager Service...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        st.write("Chrome driver successfully launched via webdriver-manager!")
        return driver
    except Exception as e:
        st.error(f"First method failed: {e}. Trying alternative method with chromedriver_autoinstaller...")
        try:
            # This will install chromedriver if not already installed and add it to PATH.
            chromedriver_autoinstaller.install()
            driver = webdriver.Chrome(options=options)
            st.write("Chrome driver successfully launched via chromedriver_autoinstaller!")
            return driver
        except Exception as e2:
            st.error(f"Alternative method failed: {e2}")
            raise Exception("All attempts to create Chrome driver failed.")

def download_and_convert_filing(driver, download_link, save_path):
    """
    Uses Selenium with headless Chrome to load the URL, print the page to PDF via CDP,
    and save the PDF to the specified save_path.
    """
    try:
        driver.get(download_link)
        time.sleep(3)  # Allow time for page to load
        pdf = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True})
        pdf_data = base64.b64decode(pdf.get("data", ""))
        if pdf_data:
            with open(save_path, "wb") as f:
                f.write(pdf_data)
            st.info(f"Saved PDF: {save_path}")
        else:
            st.error(f"No PDF data returned for {download_link}")
    except Exception as ex:
        st.error(f"Exception during conversion for {download_link}: {ex}")

def process_filings(excel_data, start_year, end_year, output_dir):
    """Process the SEC filings from the uploaded Excel file."""
    df = pd.read_excel(excel_data)
    df.columns = df.columns.str.strip()

    filings_to_process = []

    for idx, row in df.iterrows():
        cik_raw = row.get('CIK', None)
        company_name = row.get('Company Name', 'Unknown')
        if not cik_raw:
            st.warning(f"Row {idx}: No CIK found for {company_name}. Skipping.")
            continue

        cik_padded = zero_pad_cik(cik_raw)
        st.write(f"Processing {company_name} (CIK={cik_padded})...")
        sec_data = fetch_sec_json(cik_padded)
        if not sec_data or "filings" not in sec_data or "recent" not in sec_data["filings"]:
            st.error(f"No filings data found for CIK={cik_padded}")
            continue

        recent = sec_data["filings"]["recent"]
        form_list    = recent.get("form", [])
        date_list    = recent.get("filingDate", [])
        accno_list   = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        for i in range(len(form_list)):
            form_type = form_list[i]
            if form_type not in ["10-K", "10-K/A"]:
                continue
            filing_date_str = date_list[i]
            try:
                fdate = datetime.strptime(filing_date_str, "%Y-%m-%d")
            except ValueError:
                continue
            if fdate.year < start_year or fdate.year > end_year:
                continue

            primary_doc = primary_docs[i] if i < len(primary_docs) else ""
            accno_str = accno_list[i]
            accno_nodashes = accno_str.replace('-', '')
            download_link = f"https://www.sec.gov/Archives/edgar/data/{int(cik_padded)}/{accno_nodashes}/{primary_doc}"
            filings_to_process.append({
                "company_name": company_name,
                "year": fdate.year,
                "filing_date": filing_date_str,
                "accession_number": accno_str,
                "download_link": download_link
            })

    if not filings_to_process:
        st.error("No filings found in the specified year range.")
        return

    driver = create_driver()
    for filing in filings_to_process:
        company_name = filing["company_name"]
        year = filing["year"]
        filing_date_str = filing["filing_date"]
        accno_str = filing["accession_number"]
        download_link = filing["download_link"]

        # Create folder structure
        company_folder = os.path.join(output_dir, sanitize_filename(company_name))
        os.makedirs(company_folder, exist_ok=True)
        year_folder = os.path.join(company_folder, str(year))
        os.makedirs(year_folder, exist_ok=True)
        file_name = f"10K_{filing_date_str}_{accno_str.replace('-', '')}.pdf"
        save_path = os.path.join(year_folder, file_name)

        st.write(f"Converting filing from {download_link}")
        download_and_convert_filing(driver, download_link, save_path)
        time.sleep(2)  # Delay between requests

    driver.quit()

def zip_directory(directory_path, zip_path):
    """Zip the entire directory."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, directory_path)
                zipf.write(filepath, arcname)

# --- Streamlit App ---
st.title("SEC 10-K Filings Downloader & PDF Converter")

st.markdown("""
This app downloads 10-K and 10-K/A filings from the SEC website based on a user-defined year range and an Excel file containing company information.
""")

st.sidebar.header("Configuration")
start_year = st.sidebar.number_input("Start Year", min_value=1900, max_value=datetime.now().year, value=2018, step=1)
end_year = st.sidebar.number_input("End Year", min_value=1900, max_value=datetime.now().year, value=2020, step=1)

excel_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"])

if st.button("Process Filings"):
    if excel_file is None:
        st.error("Please upload an Excel file before processing.")
    elif start_year > end_year:
        st.error("Start year must be less than or equal to End year.")
    else:
        output_dir = tempfile.mkdtemp(prefix="sec_filings_")
        st.write(f"Processing filings between {start_year} and {end_year}...")
        process_filings(excel_file, start_year, end_year, output_dir)

        zip_path = os.path.join(output_dir, "sec_filings.zip")
        zip_directory(output_dir, zip_path)
        st.success("Processing complete!")

        with open(zip_path, "rb") as f:
            st.download_button(
                label="Download All PDFs (ZIP)",
                data=f,
                file_name="sec_filings.zip",
                mime="application/zip"
            )
