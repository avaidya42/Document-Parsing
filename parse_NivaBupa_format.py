import fitz 
import unicodedata
import re
import pytesseract
from pdf2image import convert_from_path
from utils_common import text_space_cleaner
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

import json
# from parsing_utils import extract_tables_from_pdf, extract_unstructured_text, parse_table_data, extract_text_from_scanned_pdf
from prompt_utils_common import get_llm_output
from output_schema_common import OutputFull
from utils_common import rec_modifier

def final_parser_nivabupa(pdf_path):
    # try structured table extraction
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    # get unstructured text and table text (as fallback for LLM)
    unstructured_text = extract_unstructured_text(pdf_path)
    table_text = "\n".join(df.to_string(index=False) for df in tables)
    unstructured_text += "\n\n" + table_text

    # get LLM output
    llm_output = get_llm_output(unstructured_text)

    # merge LLM and table-based structured data
    final = {**llm_output}

    def set_field(path, value):
        keys = path.split(".")
        curr = final
        for key in keys[:-1]:
            if key not in curr or not isinstance(curr[key], dict):
                curr[key] = {}
            curr = curr[key]
        curr[keys[-1]] = value

    if "policy_number" in structured_data:
        set_field("extra.policy_number", structured_data["policy_number"])

    if "name_policyholder" in structured_data:
        set_field("extra.name_policyholder", structured_data["name_policyholder"])

    if "policy_start_date" in structured_data:
        set_field("extra.policy_start_date", structured_data["policy_start_date"])

    if "policy_end_date" in structured_data:
        set_field("extra.policy_end_date", structured_data["policy_end_date"])

    if "sum_insured" in structured_data:
        set_field("corporate_buffer.sum_insured", structured_data["sum_insured"])

    if "day_care_treatment" in structured_data:
        set_field("day_care_treatment.day_care_treatment", structured_data["day_care_treatment"])

    rec_modifier(final)

    return final
