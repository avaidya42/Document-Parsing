import fitz  # PyMuPDF
import unicodedata
import re
import pdfplumber
from utils_common import text_space_cleaner
import pandas as pd
from output_schema_common import OutputFull
from prompt_utils_common import get_llm_output_atreya 

from utils_common import rec_modifier

# -----------------------------
# Table Extraction Utilities
# -----------------------------
def extract_tables_from_pdf(pdf_path):
    tables = []
    with fitz.open(pdf_path) as doc:
        for page in doc:  # ✅ Don't use range
            found_tables = page.find_tables()
            for tab in found_tables.tables:
                df = tab.to_pandas()
                df = df.astype(str).map(text_space_cleaner)
                tables.append(df)
    return tables

# -----------------------------
# Unstructured Text Extraction
# -----------------------------
def extract_unstructured_text_new_india(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text_space_cleaner(text)

# -----------------------------
# Table Field Mapping & Normalization
# -----------------------------
def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    return key

def parse_table_data_new_india(tables):
    extracted_data = {}

    field_mapping = {
    "policy number": "policy_number",
    "policy no": "policy_number",
    "name of policyholder": "name_policyholder",
    "cover type": "cover_type",
    "policy period start date": "policy_start_date",
    "policy period end date": "policy_end_date",
    "total sum insured": "total_sum_insured",
    "pan no": "pan_number",
    "gstin": "gstin",
   
}

    for df in tables:
        if len(df.columns) >= 2:
            # Try to parse headers as a key-value pair
            header_key = normalize_key(str(df.columns[0]))
            header_val = str(df.columns[1])
            if header_key in field_mapping:
                mapped_key = field_mapping[header_key]
                extracted_data[mapped_key] = header_val.strip()

        for _, row in df.iterrows():
            row = row.dropna()
            if len(row) < 2:
                continue
            for i in range(len(row) - 1):
                raw_key = str(row.iloc[i])
                raw_val = str(row.iloc[i + 1])
                key = normalize_key(raw_key)
                if key in field_mapping:
                    mapped_key = field_mapping[key]
                    if mapped_key not in extracted_data:
                        extracted_data[mapped_key] = raw_val.strip()

    return extracted_data

# -----------------------------
# Final Parser
# -----------------------------
def set_field(field_path: str, value: str, final: dict):
    keys = field_path.split(".")
    curr = final
    for key in keys[:-1]:
        curr = curr.setdefault(key, {})
    curr[keys[-1]] = value

def final_parser_new_india(pdf_path):
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data_new_india(tables)

    unstructured_text = extract_unstructured_text_new_india(pdf_path)
    print(f"\n Total Characters: {len(unstructured_text)}")
    print(f" Approx. Tokens (estimate): {len(unstructured_text)  // 4 }")
    

    # Fallback regex extraction if table doesn't provide policy number
    if "policy_number" not in structured_data:
        match = re.search(r'Policy\s+(?:Number|No)\s*[:\-]?\s*([A-Z0-9\-]+)', unstructured_text, re.IGNORECASE)
        if match:
            structured_data["policy_number"] = match.group(1).strip()

    # LLM extraction from unstructured text
    llm_output = get_llm_output_atreya(unstructured_text)
    final = {**llm_output}

    # Structured table field mapping
    table_field_to_output_path = {
        "policy_number": "extra.policy_number",
        "name_policyholder": "extra.name_policyholder",
        "cover_type": "extra.cover_type",
        "policy_start_date": "extra.policy_start_date",
        "policy_end_date": "extra.policy_end_date",
        "total_sum_insured": "extra.total_sum_insured",
        "no_of_persons_covered": "extra.no_of_persons_covered",
        "pan_number": "extra.pan_number",
        "gstin": "extra.gstin"
    }

    def set_field(field_path: str, value: str, final: dict):
        keys = field_path.split(".")
        curr = final
        for key in keys[:-1]:
            curr = curr.setdefault(key, {})
        curr[keys[-1]] = value

    for field, path in table_field_to_output_path.items():
        val = structured_data.get(field, "").strip()
        if val and val != ":":
            set_field(path, val, final)

    rec_modifier(final)
    return final

   
