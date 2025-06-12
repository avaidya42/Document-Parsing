import fitz  # PyMuPDF
import unicodedata
import re
from utils import text_space_cleaner
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

from utils import text_space_cleaner
from parsing_utils import normalize_key

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


