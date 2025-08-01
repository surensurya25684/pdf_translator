import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

st.set_page_config(page_title="Website Last Updated Checker", layout="centered")

st.title("🔍 Website Last Updated Checker")
st.markdown("Paste any URL below to analyze when it was last updated using 4 methods.")

url = st.text_input("📥 Enter a company page URL", placeholder="https://example.com/page")

if url:
    with st.spinner("Checking..."):

        # Method 1: HTTP Header
        def get_last_modified_header(url):
            try:
                response = requests.head(url, allow_redirects=True, timeout=10)
                return response.headers.get("Last-Modified", None)
            except:
                return None

        # Method 2: HTML Text Scraping
        def find_possible_timestamp_text(url):
            matches = []
            try:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")
                texts = soup.find_all(text=True)
                for text in texts:
                    if any(kw in text.lower() for kw in ["last updated", "updated on", "published", "modified", "posted on"]):
                        cleaned = text.strip().replace("\n", " ")
                        if len(cleaned) < 120:
                            matches.append(cleaned)
                return matches
            except:
                return []

        # Method 3: JSON-LD Structured Metadata
        def extract_json_ld_dates(url):
            dates = {}
            try:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")
                scripts = soup.find_all("script", type="application/ld+json")
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            for key in ["datePublished", "dateModified", "uploadDate"]:
                                if key in data:
                                    dates[key] = data[key]
                    except:
                        continue
            except:
                pass
            return dates

        # Method 4: Wayback Machine API
        def get_wayback_snapshots(url):
            try:
                api_url = f"https://archive.org/wayback/available?url={url}"
                response = requests.get(api_url, timeout=10).json()
                snapshot = response.get("archived_snapshots", {}).get("closest", {})
                if snapshot:
                    return snapshot["timestamp"], snapshot["url"]
                else:
                    return None, None
            except:
                return None, None

        # Run all 4 methods
        header = get_last_modified_header(url)
        html_texts = find_possible_timestamp_text(url)
        jsonld = extract_json_ld_dates(url)
        wayback_date, wayback_url = get_wayback_snapshots(url)

    # Display results
    st.subheader("🛠 Results:")

    st.markdown("### 🟡 Method 1: HTTP Header")
    if header:
        st.success(f"**Last-Modified:** {header}")
    else:
        st.info("No `Last-Modified` header found.")

    st.markdown("### 🟡 Method 2: Page Text Content")
    if html_texts:
        for t in html_texts:
            st.success(f"📌 {t}")
    else:
        st.info("No readable update timestamps found in HTML text.")

    st.markdown("### 🟡 Method 3: Structured Metadata (JSON-LD)")
    if jsonld:
        for k, v in jsonld.items():
            st.success(f"**{k}:** {v}")
    else:
        st.info("No structured JSON-LD date fields found.")

    st.markdown("### 🟡 Method 4: Wayback Machine")
    if wayback_date:
        st.success(f"Closest Snapshot: {wayback_date}")
        st.markdown(f"[📎 View Snapshot]({wayback_url})")
    else:
        st.info("No Wayback Machine snapshot found.")
