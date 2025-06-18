import fitz
import pytesseract
import re
import unicodedata
from pdf2image import convert_from_path
from utils_common import text_space_cleaner
from typing import List, Dict
import pandas as pd
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

def find_heading_coordinates(pdf_path: str, headings: List[str]) -> Dict[str, Dict]:
    coords = {}
    for page_layout in extract_pages(pdf_path):
        page_num = page_layout.pageid - 1
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text = text_space_cleaner(element.get_text()).strip()
                if text in headings:
                    coords[text] = {
                        "page": page_num,
                        "bbox": element.bbox
                    }
    return coords

def extract_text_near_heading(pdf_path: str, heading_coords: Dict[str, Dict], offset_x: float = 50.0) -> Dict[str, str]:
    doc = fitz.open(pdf_path)
    extracted = {}

    for heading, info in heading_coords.items():
        page = doc[info["page"]]
        x0, y0, x1, y1 = info["bbox"]
        text_instances = page.get_text("dict")["blocks"]
        for block in text_instances:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_x, span_y = span["bbox"][0], span["bbox"][1]
                    if abs(span_y - y0) < 10 and span_x > x1 and span_x < x1 + offset_x:
                        extracted[heading] = span["text"]
                        break
    return extracted

def extract_unstructured_text(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text_space_cleaner(text)

def extract_text_from_scanned_pdf(pdf_path):
    pages = convert_from_path(pdf_path, dpi=300)
    full_text = ""
    for page_image in pages:
        text = pytesseract.image_to_string(page_image)
        full_text += text + "\n"
    return text_space_cleaner(full_text)

def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    return key

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


def parse_table_data(tables):
    extracted_data = {}

    field_mapping = {
        "name of the insured/proposer": "name_policyholder",
        "period of insurance": ["policy_start_date", "policy_end_date"],
        "total sum insured": "sum_insured",
        "total no of insured persons covered": "total_number_insured"
    }

    for df in tables:
        df.dropna(how="all", inplace=True)
        df = df.astype(str).map(text_space_cleaner)

        for _, row in df.iterrows():
            try:
                key_raw = row.iloc[0]
                key = normalize_key(key_raw)

                # Map field name
                if key in field_mapping:
                    mapped = field_mapping[key]

                    # Handle 3-column case like [key, ':', value]
                    value = ""
                    if len(row) > 2 and row.iloc[1].strip() == ":":
                        value = row.iloc[2]
                    elif len(row) > 1:
                        value = row.iloc[1]

                    value = text_space_cleaner(value)

                    # Handle date range parsing if needed
                    if isinstance(mapped, list) and "to" in value:
                        parts = [v.strip() for v in value.split("to")]
                        if len(parts) == 2:
                            extracted_data[mapped[0]] = parts[0]
                            extracted_data[mapped[1]] = parts[1]
                    else:
                        extracted_data[mapped] = value

            except Exception as e:
                continue

    return extracted_data

import json
# from parsing_utils import (
#     extract_tables_from_pdf,
#     extract_unstructured_text,
#     parse_table_data,
#     find_heading_coordinates,
#     extract_text_near_heading
# )
from prompt_utils_common import get_llm_output
from output_schema_common import OutputFull
from utils_common import rec_modifier

def set_field(path, value, final):
    keys = path.split(".")
    curr = final
    for key in keys[:-1]:
        if key not in curr or not isinstance(curr[key], dict):
            curr[key] = {}
        curr = curr[key]
    curr[keys[-1]] = value

def final_parser_SBIgeneral(pdf_path):
    field_source = {}

    # table data
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)
    for k in structured_data:
        field_source[k] = "table"

    # heading-based extraction
    heading_targets = ["Policy No", "Total Sum Insured"]
    heading_coords = find_heading_coordinates(pdf_path, heading_targets)
    heading_data = extract_text_near_heading(pdf_path, heading_coords)

    if "Policy No" in heading_data:
        structured_data["policy_number"] = heading_data["Policy No"]
        field_source["policy_number"] = "heading"

    if "Total Sum Insured" in heading_data:
        structured_data["sum_insured"] = heading_data["Total Sum Insured"]
        field_source["sum_insured"] = "heading"

    # extract unstructured content for LLM
    unstructured_text = extract_unstructured_text(pdf_path)
    table_text = "\n".join(df.to_string(index=False) for df in tables)
    unstructured_text += "\n\n" + table_text
    llm_output = get_llm_output(unstructured_text)

    final = {**llm_output}
    if "policy_number" in structured_data:
        set_field("extra.policy_number", structured_data["policy_number"], final)
    if "name_policyholder" in structured_data:
        set_field("extra.name_policyholder", structured_data["name_policyholder"], final)
    if "policy_start_date" in structured_data:
        set_field("extra.policy_start_date", structured_data["policy_start_date"], final)
    if "policy_end_date" in structured_data:
        set_field("extra.policy_end_date", structured_data["policy_end_date"], final)
    if "sum_insured" in structured_data:
        set_field("corporate_buffer.sum_insured", structured_data["sum_insured"], final)
    if "total_number_insured" in structured_data:
        set_field("extra.total_number_insured", structured_data["total_number_insured"], final)

    rec_modifier(final)

    return final

