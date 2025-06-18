from prompt_utils_common import get_llm_output
from utils_common import rec_modifier, remap_keys


import fitz  # PyMuPDF
import unicodedata
import re
from utils_common import text_space_cleaner
import pandas as pd

def extract_tables_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    tables = []
    for page in doc:
        found_tables = page.find_tables()
        for tab in found_tables.tables:
            df = tab.to_pandas()
            df = df.astype(str).applymap(text_space_cleaner)
            tables.append(df)
    return tables

def extract_unstructured_text(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text("text")  # alternative rendering mode


    text = text_space_cleaner(text)
    print("\n📃 Extracted Text Sample:\n", text[:1000])  # Add this line to debug
    return text


def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    return key

def parse_table_data(tables):
    extracted_data = {}

    # Support for both GHI and GPA
    field_mapping = {
        "policy no": "policy_no",
        "policy number": "policy_no",
        "policyholder name": "policyholder_name",
        "policyholder": "policyholder_name",
        "policy period start date": "start_date",
        "start date & time of policy": "start_date",
        "expiry date & time of policy": "end_date",
        "policy period end date": "end_date",
        "product name": "product_name",
        "product code": "product_code",
        "policy issued date & time": "issued_date",
        "issuing office": "issuing_office",
        "policy servicing office": "servicing_office",
        "sum insured": "sum_insured",
        "sum insured per member": "sum_insured_per_member",
        "total sum insured": "total_sum_insured",
        "net premium": "net_premium",
        "gross premium": "gross_premium",
        "igst": "igst",
        "gstin": "gst_registration_no",
        "sac code": "sac_code",
        "category": "Category"
    }

    for df in tables:
        df.dropna(how="all", inplace=True)
        df = df.astype(str).applymap(text_space_cleaner)

        for _, row in df.iterrows():
            try:
                raw_key = row.iloc[0]
                raw_value = row.iloc[1] if len(row) > 1 else None
            except Exception as e:
                print(f"[ERROR accessing row]: {e}")
                continue

            key = normalize_key(str(raw_key))
            value = text_space_cleaner(str(raw_value)) if raw_value else None

            print(f"[DEBUG] Raw Key: '{raw_key}' → Normalized: '{key}'")
            print(f"[DEBUG] Raw Value: '{raw_value}' → Normalized: '{value}'")

            if key in field_mapping:
                mapped_field = field_mapping[key]
                if mapped_field not in extracted_data:
                    extracted_data[mapped_field] = value

    return extracted_data

def parse_aditya(pdf_path):
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)
    unstructured_text = extract_unstructured_text(pdf_path)
    llm_output = get_llm_output(unstructured_text)

    final = remap_keys(llm_output)
    final.setdefault("policy_info", {}).update(structured_data)
    rec_modifier(final)
    return final