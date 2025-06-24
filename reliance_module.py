import fitz  # PyMuPDF
import re
import unicodedata
import pdfplumber
import pandas as pd

from utils_common import text_space_cleaner, rec_modifier
from output_schema_common import OutputFull
from prompt_utils_common import get_llm_output_atreya 


# --- Table Extraction ---
def extract_tables_from_pdf(pdf_path):
    tables = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            found_tables = page.find_tables()
            for table in found_tables.tables:
                df = table.to_pandas()
                df = df.astype(str).map(text_space_cleaner)
                tables.append(df)
    return tables

# --- Key Normalizer ---
def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    return key

# --- Parse Structured Fields ---
def parse_table_data(tables):
    structured_data = {}
    field_mapping = {
        "policy number": "policy_number",
        "policyholder name": "name_policyholder",
        "cover type": "cover_type",
        "policy start date": "policy_start_date",
        "policy end date": "policy_end_date",
        "insured members": "primary_insured_members",
        "total sum insured RS": "total_sum_insured"
    }

    for df in tables:
        if len(df.columns) >= 2:
            for _, row in df.iterrows():
                row = row.dropna()
                if len(row) < 2:
                    continue
                raw_key, raw_val = str(row.iloc[0]), str(row.iloc[1])
                key = normalize_key(raw_key)
                if key in field_mapping:
                    structured_data[field_mapping[key]] = raw_val.strip()

    return structured_data

import fitz  # PyMuPDF
def extract_unstructured_text_reliance(pdf_path):
    text = ""
    capture = False
    start_marker = "Policyholder Details"
    end_marker = "Schedule of Members"

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
    
# --- Set Field in Output Schema ---
def set_field(field_path: str, value: str, final: dict):
    keys = field_path.split(".")
    curr = final
    for key in keys[:-1]:
        curr = curr.setdefault(key, {})
    curr[keys[-1]] = value

def final_parser_reliance(pdf_path):
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    unstructured_text = extract_unstructured_text_reliance(pdf_path)
    

    llm_output = get_llm_output_atreya(unstructured_text)

    final = {**llm_output}

    for key, value in structured_data.items():
        set_field(f"extra.{key}", value, final)

    rec_modifier(final)
    return final

