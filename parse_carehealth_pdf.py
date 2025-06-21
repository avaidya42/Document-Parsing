import fitz  # PyMuPDF
import unicodedata
import re
import pdfplumber
from utils_common import text_space_cleaner
import pandas as pd

def extract_tables_from_pdf(pdf_path):
    tables = []
    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, 1):  # limiting extraction to first 5 pages
            found_tables = page.find_tables()
            for tab in found_tables.tables:
                df = tab.to_pandas()
                df = df.astype(str).map(text_space_cleaner)
                tables.append(df)
    return tables

def extract_unstructured_text_carehealth(pdf_path):
    text = ""
    capture = False
    start_marker = "Benefits"
    end_marker = "Other Term and Conditions"

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

def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    return key


def parse_table_data_carehealth(tables):
    extracted_data = {}

    field_mapping = {
    "policy no": "policy_no",
    "policy number": "policy_no",
    "name of policyholder": "policyholder_name",
    "cover type": "cover_type",
    "policy period start date": "policy_start_date",
    "policy period end date": "policy_end_date",
    "primary insured members": "primary_insured_members",
    "total sum insured": "total_sum_insured"
}

    for df in tables:
        # parsing header also as key value pairs
        if len(df.columns) >= 2:
            header_key = normalize_key(str(df.columns[0]))
            header_val = str(df.columns[1])
            if header_key in field_mapping:
                mapped_key = field_mapping[header_key]
                if mapped_key not in extracted_data:
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

# pdf_path = "GMC_Policy_2024_2025.pdf"

import json
from prompt_utils_common import get_llm_output
from output_schema_common import OutputFull
from utils_common import rec_modifier

def set_field(field_path: str, value: str, final: dict, source: str):
    keys = field_path.split(".")
    curr = final
    for key in keys[:-1]:
        curr = curr.setdefault(key, {})
    curr[keys[-1]] = value

def final_parser_carehealth(pdf_path):
    # extracting structured values from tables
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data_carehealth(tables)

    # extracting unstructured text and parse with LLM
    unstructured_text = extract_unstructured_text_carehealth(pdf_path)
    print(f"\n Total Characters: {len(unstructured_text)}")
    print(f" Approx. Tokens (estimate): {len(unstructured_text) // 4}")
    llm_output = get_llm_output(unstructured_text)
    
    # unpack llm_output dict and store in final
    final = {**llm_output}

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
    if "primary_insured_members" in structured_data:
        set_field("extra.primary_insured_members", structured_data["primary_insured_members"], final, "table")
    if "total_sum_insured" in structured_data:
        set_field("extra.total_sum_insured", structured_data["total_sum_insured"], final, "table")


    # clean values
    rec_modifier(final)
    
    return final


