import fitz
import pytesseract
import pdfplumber
import re
import unicodedata
from pdf2image import convert_from_path
import json
from prompt_utils_common import get_llm_output
from output_schema_common import OutputFull
from utils_common import text_space_cleaner, rec_modifier
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
    extracted = {}   
    with fitz.open(pdf_path) as doc:

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

def extract_unstructured_text_sbigeneral(pdf_path):
    text = ""
    capture = False
    start_marker = "Additional Conditions"
    end_marker = "Premium Computation"

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

def extract_tables_from_pdf(pdf_path):
    tables = []
    with fitz.open(pdf_path) as doc:
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
        "name of the insured proposer": "name_policyholder",
        "period of insurance": ["policy_start_date", "policy_end_date"],
        "no of primary insured persons covered": "primary_insured_members",
        "total sum insured": "total_sum_insured",
        "total no of insured persons covered": "total_number_insured",
        "corporate buffer": "corporate_buffer_limit",
        "maternity": "maternity_normal_limit",
        "maternity (caesarean)": "maternity_c_section_limit",
        "prenatal and postnatal combined": "pre_post_natal_ipd_limit",
        "ambulance only": "road_ambulance_limit",
        "pre hospitalization": "pre_hospitalization_period",
        "post hospitalization": "post_hospitalization_period",
        "copay": "co_pay_combined"
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


def set_field(path, value, final, source="llm"):
    # print(f" Setting field {path} from {source}: {value}")
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

    # print("\n Extracted structured data from tables:")
    # if not structured_data:
    #     print(" No structured data was extracted.")
    # else:
    #     for k, v in structured_data.items():
    #         print(f"  {k}: {v}")

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
    unstructured_text = extract_unstructured_text_sbigeneral(pdf_path)

    # print("\n Unstructured Text Sent to LLM (First 50 lines):")
    # for i, line in enumerate(unstructured_text.splitlines()):
    #     if i >= 50:
    #         print("... (truncated)")
    #         break
    #     print(f"{i+1:02d}: {line}")

    print(f"\n Total Characters: {len(unstructured_text)}")
    print(f" Approx. Tokens (estimate): {len(unstructured_text) // 4}")

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
    if "primary_insured_members" in structured_data:
        set_field("extra.primary_insured_members", structured_data["primary_insured_members"], final)
    if "total_sum_insured" in structured_data:
        set_field("extra.total_sum_insured", structured_data["total_sum_insured"], final)
    if "total_number_insured" in structured_data:
        set_field("extra.total_number_insured", structured_data["total_number_insured"], final)
    if "corporate_buffer_limit" in structured_data:
        set_field("corporate_buffer.sum_insured", structured_data["corporate_buffer_limit"], final)
    if "maternity_normal_limit" in structured_data:
        set_field("maternity_expenses.limit_normal_delivery", structured_data["maternity_normal_limit"], final)
    if "maternity_c_section_limit" in structured_data:
        set_field("maternity_expenses.limit_C_Section", structured_data["maternity_c_section_limit"], final)
    if "pre_post_natal_ipd_limit" in structured_data:
        set_field("pre_and_post_natal_expenses_IPD.expenses_limit_IPD", structured_data["pre_post_natal_ipd_limit"], final)
        set_field("pre_and_post_natal_expenses_IPD.applicability", "As per table - IPD basis", final)
    if "road_ambulance_limit" in structured_data:
        set_field("road_ambulance.road_ambulance_limit", structured_data["road_ambulance_limit"], final)
    if "pre_hospitalization_period" in structured_data:
        set_field("pre_hospitalization.pre_hospitalization_period", structured_data["pre_hospitalization_period"], final)
    if "post_hospitalization_period" in structured_data:
        set_field("post_hospitalization.post_hospitalization_period", structured_data["post_hospitalization_period"], final)
    if "co_pay_combined" in structured_data:
        raw = structured_data["co_pay_combined"]
        set_field("co_pay.policy_co_payment_factor", raw, final)
        set_field("co_pay.co_pay_type", "Network / Non-network distinction", final)


    rec_modifier(final)

    return final

