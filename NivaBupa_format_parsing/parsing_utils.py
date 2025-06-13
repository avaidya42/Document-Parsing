import fitz 
import unicodedata
import re
import pytesseract
from pdf2image import convert_from_path
from utils import text_space_cleaner
import pandas as pd

def extract_tables_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    tables = []
    for page in doc:
        found_tables = page.find_tables()
        for tab in found_tables.tables:
            df = tab.to_pandas()
            df = df.astype(str).map(text_space_cleaner)
            tables.append(df)
    return tables

def extract_unstructured_text(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text_space_cleaner(text)

def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    return key

def parse_table_data(tables):
    extracted_data = {}

    field_mapping = {
        "policy number": "policy_number",
        "policyholder's name": "name_policyholder",
        "date and time of policy commencement": "policy_start_date",
        "date and time of policy expiry": "policy_end_date",
        "aggregate sum insured": "sum_insured",
        "listed day care treatment": "day_care_treatment",
        "pre hospitalization medical expenses ": "pre_hospitalization_period",
        "post hospitalization medical expenses ": "post_hospitalization_period"
    }

    for df in tables:
        df.dropna(how="all", inplace=True)
        df = df.astype(str).map(text_space_cleaner)

        for _, row in df.iterrows():
            try:
                key = normalize_key(str(row.iloc[0]))
                value = text_space_cleaner(str(row.iloc[1])) if len(row) > 1 else None
                if key in field_mapping and field_mapping[key] not in extracted_data:
                    extracted_data[field_mapping[key]] = value
            except Exception:
                continue

    return extracted_data

def extract_text_from_scanned_pdf(pdf_path):
    pages = convert_from_path(pdf_path, dpi=300)
    full_text = ""
    for page_image in pages:
        text = pytesseract.image_to_string(page_image)
        full_text += text + "\n"
    return text_space_cleaner(full_text)



