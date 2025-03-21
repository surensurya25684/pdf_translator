import requests
import pandas as pd
from datetime import datetime
import os
import re
import time
import base64

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ----------------------------------------------
# Custom User-Agent per SEC rules
# ----------------------------------------------
# (Used for SEC JSON fetch requests, not Selenium)
HEADERS = {
    "User-Agent": "MSCI EDGAR Scraper (Contact: suren.surya@msci.com)"
}

# Base output directory for saving PDFs
BASE_OUTPUT_DIR = r"C:\Users\surysur\Downloads"

def sanitize_filename(name):
    """
    Remove characters that are not allowed in file/folder names.
    """
    return re.sub(r'[\\/*?:"<>|]', "", name)

def choose_year_range():
    """
    Prompt the user for a start and end year for 10-K filings.
    Returns (start_year, end_year) as integers.
    """
    print("\nEnter a start and end year for 10-K filings (e.g., 2018 and 2020):")
    start_year = input("Start year: ").strip()
    end_year = input("End year:   ").strip()
    try:
        start_year = int(start_year)
        end_year = int(end_year)
    except ValueError:
        print("Invalid input for years. Exiting.")
        exit(1)
    return start_year, end_year

def fetch_sec_json(cik_str, max_retries=3, delay=2):
    """
    Given a zero-padded CIK string (e.g., '0001156375'),
    fetch the SEC JSON from the submissions endpoint.
    Implements a retry mechanism: if a request fails, it will retry
    up to 'max_retries' times with a delay (in seconds) between attempts.
    Returns a dict or None if not found.
    """
    base_url = "https://data.sec.gov/submissions/CIK{}.json"
    url = base_url.format(cik_str)
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"  [WARNING] Attempt {attempt}: CIK JSON fetch returned {resp.status_code} for {url}")
        except Exception as ex:
            print(f"  [WARNING] Attempt {attempt}: Error fetching {url}: {ex}")
        
        if attempt < max_retries:
            print("  [INFO] Retrying...")
            time.sleep(delay)
    
    return None

def zero_pad_cik(cik):
    """
    Ensures the CIK is a zero-padded string of length 10.
    """
    try:
        val = int(cik)
        return f"{val:010d}"
    except ValueError:
        return str(cik).rjust(10, "0")

def create_driver():
    """
    Creates and returns a Selenium Chrome WebDriver instance in headless mode,
    with a custom User-Agent for all browser requests.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    # Set your custom User-Agent for Selenium-based traffic:
    options.add_argument('--user-agent=MSCI EDGAR Scraper (Contact: suren.surya@msci.com)')

    # If chromedriver is not in PATH, specify the 'executable_path' here:
    driver = webdriver.Chrome(options=options)
    return driver

def download_and_convert_filing(driver, download_link, save_path):
    """
    Uses Selenium with headless Chrome to load the URL, print the page to PDF via CDP,
    and save the PDF to the specified save_path.
    """
    try:
        driver.get(download_link)
        # Allow some time for the page to load fully.
        time.sleep(3)
        # Execute the printToPDF command via Chrome DevTools Protocol.
        pdf = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True})
        pdf_data = base64.b64decode(pdf.get("data", ""))
        if pdf_data:
            with open(save_path, "wb") as f:
                f.write(pdf_data)
            print(f"  [SUCCESS] Saved PDF to {save_path}")
        else:
            print(f"  [ERROR] No PDF data returned for {download_link}")
    except Exception as ex:
        print(f"  [ERROR] Exception during conversion for {download_link}: {ex}")

def main():
    print("Processing only 10-K filings.")
    start_year, end_year = choose_year_range()
    print(f"\nFiltering filings from year {start_year} to {end_year} (inclusive).")

    # Load the Excel file with company information
    input_file = r'C:\Users\surysur\OneDrive\OneDrive - MSCI Office 365\Meetings\10k_pdf.xlsx'
    df = pd.read_excel(input_file)
    df.columns = df.columns.str.strip()

    filings_to_process = []

    # Iterate over each company in the Excel file
    for idx, row in df.iterrows():
        cik_raw = row.get('CIK', None)
        company_name = row.get('Company Name', 'Unknown')
        if not cik_raw:
            print(f"\nRow {idx}: No CIK found for {company_name}. Skipping.")
            continue

        cik_padded = zero_pad_cik(cik_raw)
        print(f"\nProcessing {company_name} (CIK={cik_padded})...")

        sec_data = fetch_sec_json(cik_padded)
        if not sec_data or "filings" not in sec_data or "recent" not in sec_data["filings"]:
            print(f"  [ERROR] No filings data found for CIK={cik_padded}")
            continue

        recent = sec_data["filings"]["recent"]
        form_list    = recent.get("form", [])
        date_list    = recent.get("filingDate", [])
        accno_list   = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        # Filter for 10-K and 10-K/A filings within the specified year range
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
        print("No filings found in the specified year range.")
        return

    # Create a Selenium driver instance
    driver = create_driver()

    # Process each filing: create appropriate folder structure and save PDF
    for filing in filings_to_process:
        company_name = filing["company_name"]
        year = filing["year"]
        filing_date_str = filing["filing_date"]
        accno_str = filing["accession_number"]
        download_link = filing["download_link"]

        # Create company folder
        company_folder = os.path.join(BASE_OUTPUT_DIR, sanitize_filename(company_name))
        if not os.path.exists(company_folder):
            os.makedirs(company_folder)

        # Create year folder inside the company folder
        year_folder = os.path.join(company_folder, str(year))
        if not os.path.exists(year_folder):
            os.makedirs(year_folder)

        # Define the file name for the PDF
        file_name = f"10K_{filing_date_str}_{accno_str.replace('-', '')}.pdf"
        save_path = os.path.join(year_folder, file_name)

        print(f"  Converting filing from {download_link}")
        download_and_convert_filing(driver, download_link, save_path)

        # Add a short delay to avoid rapid-fire requests to the SEC
        time.sleep(2)

    driver.quit()

if __name__ == "__main__":
    main()
