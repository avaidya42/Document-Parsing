import json
from prompt_utils_common import get_llm_output_amogh
from utils_common import rec_modifier, output_template
import fitz
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
from typing import List,Dict
import unicodedata
import re
from utils_common import text_space_cleaner
import pandas as pd
import logging
import pdfplumber

def clean_output_dict(data):
    if isinstance(data, dict):
        return {k: clean_output_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_output_dict(item) for item in data]
    elif isinstance(data, str):
        cleaned = data.strip().strip('",}').strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned
    else:
        return data


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

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def extract_tables_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
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
    capture = False
    start_marker = "Sum Insured and Room Rent Restriction"
    end_marker = "Other Terms and Conditions(Applicable to all Packages)"

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


def parse_table_data(tables):
    extracted_data = {}

    field_mapping = {
        "policy number": "policy_no",
        "policy start date": "start_date",
        "policy valid upto date": "end_date",
        "policy type": "policy_type",
        "policy tenure": "policy_tenure",
        "master policy number": "master_policy_no",
        "tpa name": "tpa_name",
        "gstin": "gst_registration_no",
        "sac code": "sac_code",
        "category": "Category"
    }

    for df in tables:
        df.dropna(how="all", inplace=True)
        df = df.astype(str).map(text_space_cleaner)

        for _, row in df.iterrows():
            try:
                raw_key = row.iloc[0]
                raw_value = row.iloc[1] if len(row) > 1 else None
            except Exception as e:
                logger.warning(f"[ERROR accessing row]: {e}")
                continue

            key = normalize_key(str(raw_key))
            value = text_space_cleaner(str(raw_value)) if raw_value else None

            logger.debug(f"[DEBUG] Raw Key: '{raw_key}' → Normalized: '{key}'")
            logger.debug(f"[DEBUG] Raw Value: '{raw_value}' → Normalized: '{value}'")

            if key in field_mapping:
                mapped_field = field_mapping[key]
                if mapped_field not in extracted_data:
                    extracted_data[mapped_field] = value

    return extracted_data


def parse_digit_pdf(pdf_path):
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    field_source = {}

    print("\n Extracted structured data from tables:")
    if not structured_data:
        print(" No structured data was extracted.")
    else:
        for k, v in structured_data.items():
            print(f"  {k}: {v}")

    for k in structured_data:
        field_source[k] = "table"

    heading_targets = ["Policy No", "Total Sum Insured"]
    heading_coords = find_heading_coordinates(pdf_path, heading_targets)
    heading_data = extract_text_near_heading(pdf_path, heading_coords)

    if "Policy No" in heading_data:
        structured_data["policy_number"] = heading_data["Policy No"]
        field_source["policy_number"] = "heading"

    unstructured_text = extract_unstructured_text(pdf_path)

    print("\n Unstructured Text Sent to LLM (First 50 lines):")
    for i, line in enumerate(unstructured_text.splitlines()):
        if i >= 50:
            print("... (truncated)")
            break
        print(f"{i+1:02d}: {line}")
    
    print(f"\n Total Characters: {len(unstructured_text)}")
    print(f" Approx. Tokens (estimate): {len(unstructured_text) // 4}")

    llm_output = clean_output_dict(get_llm_output_amogh(unstructured_text))

    final = output_template()

    # Step 1: Merge non-special fields
    skip_keys = {"maternity", "modern_treatment", "day_care", "other_covers"}
    for section, values in llm_output.items():
        if section in skip_keys:
            continue
        if section not in final:
            final[section] = values
        elif isinstance(values, dict):
            final[section].update(values)

    maternity = llm_output.get("maternity", {})
    if maternity:
        final["maternity_expenses"]["limit_normal_delivery"] = maternity.get("normal_delivery_metro", "")
        final["maternity_expenses"]["limit_C_Section"] = maternity.get("csection_delivery_metro", "")
        final["maternity_expenses"]["waiting_period"] = maternity.get("maternity_waiting_period", "")
        final["maternity_expenses"]["no_of_deliveries"] = "2" if "first 2 children" in maternity.get("maternity_eligibility", "").lower() else ""

        pre_post = maternity.get("pre_post_natal_expenses", "")
        final["pre_and_post_natal_expenses_IPD"]["expenses_limit_IPD"] = pre_post
        final["pre_and_post_natal_expenses_IPD"]["applicability"] = pre_post
        final["pre_and_post_natal_expenses_OPD"]["expenses_limit_OPD"] = pre_post

        final["maternity_expenses_additional"] = {
            "twin_delivery_limit": maternity.get("twin_delivery_limit", ""),
            "infertility_treatment": maternity.get("infertility_treatment", ""),
            "well_baby_expenses": maternity.get("well_baby_expenses", ""),
            "well_mother_expenses": maternity.get("well_mother_expenses", ""),
            "maternity_eligibility": maternity.get("maternity_eligibility", "")
        }

    
    day_care = llm_output.get("day_care", {})
    if day_care:
        final["day_care_treatment"]["day_care_treatment"] = day_care.get("covered", "Not Applicable")

   
    modern = llm_output.get("modern_treatment", {})
    if modern:
        if "modern_treatment" not in final:
            final["modern_treatment"] = {}
        final["modern_treatment"].update(modern)
        if any("50%" in str(v) for v in modern.values()):
            final["medical_advancement_surgery"]["medical_advancement_surgery_limit"] = "Covered up to 50 % of SI."

    
    other = llm_output.get("other_covers", {})
    lasik = other.get("lasik", "")
    if "+/-" in lasik or "lens" in lasik.lower():
        final["refractive_error_correction_expenses"]["eye_power"] = "7"
        final["refractive_error_correction_expenses"]["si_limit"] = lasik

    
    if "other_covers" not in final:
        final["other_covers"] = {}
    if "terrorism_cover" in other and "cover" in other["terrorism_cover"].lower():
        final["other_covers"]["terrorism_cover"] = "Covered"

    def set_field(path, value):
            keys = path.split(".")
            curr = final
            for key in keys[:-1]:
                if key not in curr or not isinstance(curr[key], dict):
                    curr[key] = {}
                curr = curr[key]
            curr[keys[-1]] = value


# Inject structured data into final output
    if "start_date" in structured_data:
        set_field("extra.policy_start_date", structured_data["start_date"])
    if "end_date" in structured_data:
        set_field("extra.policy_end_date", structured_data["end_date"])
    if "policy_type" in structured_data:
        set_field("extra.cover_type", structured_data["policy_type"])
    if "master_policy_no" in structured_data:
        set_field("extra.policy_number", structured_data["master_policy_no"])  # if policy_number is empty
    if "tpa_name" in structured_data:
        set_field("extra.tpa_name", structured_data["tpa_name"])


    rec_modifier(final)
    return final