import fitz  # PyMuPDF
import unicodedata
import re
import pdfplumber
import pandas as pd

from utils_common import text_space_cleaner
from prompt_utils_common import get_llm_output_atreya 

from output_schema_common import OutputFull
from utils_common import rec_modifier

# Normalize and clean table keys
def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    return key

# Extract tables using fitz (PyMuPDF)
def extract_tables_from_pdf_tata(pdf_path):
    import fitz  # PyMuPDF
    tables = []
    STOP_MARKER = "Annexure : List of Insured Persons"

    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text()
            if STOP_MARKER.lower() in text.lower():
                break  # 🛑 STOP parsing further pages

            found_tables = page.find_tables()
            for tab in found_tables.tables:
                df = tab.to_pandas()
                df = df.astype(str).map(text_space_cleaner)
                tables.append(df)

    return tables



# Define key mapping for structured fields from table
TATA_FIELD_MAPPING = {
    "policy no": "policy_no",
    "policy number": "policy_no",
    "name of policyholder": "policyholder_name",
    "cover type": "cover_type",
    "policy period start date": "policy_start_date",
    "policy period end date": "policy_end_date",
    "primary insured persons": "primary_insured_persons",
    "total sum insured": "total_sum_insured"
}

# Parse structured table data
def parse_table_data_tata(tables):
    extracted_data = {}

    for df in tables:
        # Extract from headers
        if len(df.columns) >= 2:
            header_key = normalize_key(str(df.columns[0]))
            header_val = str(df.columns[1])
            if header_key in TATA_FIELD_MAPPING:
                mapped_key = TATA_FIELD_MAPPING[header_key]
                extracted_data[mapped_key] = header_val.strip()

        # Extract from rows
        for _, row in df.iterrows():
            row = row.dropna()
            if len(row) < 2:
                continue
            for i in range(len(row) - 1):
                raw_key = str(row.iloc[i])
                raw_val = str(row.iloc[i + 1])
                key = normalize_key(raw_key)
                if key in TATA_FIELD_MAPPING:
                    mapped_key = TATA_FIELD_MAPPING[key]
                    if mapped_key not in extracted_data:
                        extracted_data[mapped_key] = raw_val.strip()
    return extracted_data

import fitz  # PyMuPDF
def extract_unstructured_text_tata(pdf_path):
    text = ""
    capture = False
    start_marker = "Details Of Coverage"
    end_marker = "Annexure : List of Insured Persons"

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().splitlines()
            for line in lines:
                cleaned_line = line.strip()

                if not capture and start_marker.lower() in cleaned_line.lower():
                    capture = True

                if capture:
                    text += cleaned_line + "\n"

                if capture and end_marker.lower() in cleaned_line.lower():
                    capture = False
                    break  # stop scanning current page but continue with others if needed

    return text_space_cleaner(text)
    

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text



# Utility to set nested keys
def set_field(field_path: str, value: str, final: dict, source: str):
    keys = field_path.split(".")
    curr = final
    for key in keys[:-1]:
        curr = curr.setdefault(key, {})
    curr[keys[-1]] = value

def final_parser_tata(pdf_path):
    tables = extract_tables_from_pdf_tata(pdf_path)
    structured_data = parse_table_data_tata(tables)

    unstructured_text = extract_unstructured_text_tata(pdf_path)
    llm_output = get_llm_output_atreya(unstructured_text)

    final = {**llm_output}

    # ✅ Extract raw text for custom regex
    raw_text = extract_text_from_pdf(pdf_path)

    # ✅ Accurate Corporate Buffer extraction
    buffer_match = re.search(
        r"Corporate\s+Buffer\s*[:\-]?\s*(?:INR|₹)?\s*([\d,]+)",
        raw_text,
        re.IGNORECASE
    )
    if buffer_match:
        buffer_amount = buffer_match.group(1).replace(",", "").strip()
        set_field("corporate_buffer.sum_insured", buffer_amount, final, "text")

    # ✅ Add structured fields to "extra"
    if "policy_no" in structured_data:
        set_field("extra.policy_number", structured_data["policy_no"], final, "table")
    if "policyholder_name" in structured_data:
        set_field("extra.name_policyholder", structured_data["policyholder_name"], final, "table")
    if "cover_type" in structured_data:
        set_field("extra.cover_type", structured_data["cover_type"], final, "table")
    if "policy_start_date" in structured_data:
        set_field("extra.policy_start_date", structured_data["policy_start_date"], final, "table")
    if "policy_end_date" in structured_data:
        set_field("extra.policy_end_date", structured_data["policy_end_date"], final, "table")
    if "primary_insured_persons" in structured_data:
        set_field("extra.primary_insured_persons", structured_data["primary_insured_perons"], final, "table")
    if "total_sum_insured" in structured_data:
        set_field("extra.total_sum_insured", structured_data["total_sum_insured"], final, "table")

    # ✅ Final cleanup
    rec_modifier(final)
    return final
