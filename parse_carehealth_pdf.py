import fitz  # PyMuPDF
import unicodedata
import re
from utils_common import text_space_cleaner
# from parsing_utils import normalize_key
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
        "policy no": "policy_no",
        "name of policyholder": "policyholder_name",
        "cover type": "cover_type",
        "policy period start date": "start_date",
        "policy period end date": "end_date",
        "primary insured members": "primary_insured_members",
        "total sum insured": "sum_insured"
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
            except:
                continue

    return extracted_data

# pdf_path = "GMC_Policy_2024_2025.pdf"

import json
# from parsing_utils import extract_tables_from_pdf, extract_unstructured_text, parse_table_data
from prompt_utils_common import get_llm_output
from output_schema_common import OutputFull
from utils_common import rec_modifier

def final_parser(pdf_path):
    # extracting structured values from tables
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    # extracting unstructured text and parse with LLM
    unstructured_text = extract_unstructured_text(pdf_path)
    llm_output = get_llm_output(unstructured_text)
    
    # unpack llm_output dict and store in final
    final = {**llm_output}

    if "policy_no" in structured_data:
        final["extra"]["policy_number"] = structured_data["policy_number"]
    if "name_policyholder" in structured_data:
        final["extra"]["name_policyholder"] = structured_data["name_policyholder"]
    if "policy_start_date" in structured_data:
        final["extra"]["policy_start_date"] = structured_data["policy_start_date"]
    if "policy_end_date" in structured_data:
        final["extra"]["policy_end_date"] = structured_data["policy_end_date"]
    if "sum_insured" in structured_data:
        final["corporate_buffer"]["total_sum_insured"] = structured_data["total_sum_insured"]
    if "primary_insured_members" in structured_data:
        final["extra"]["primary_insured_members"] = structured_data["primary_insured_members"]

    # clean values
    rec_modifier(final)

    return final


