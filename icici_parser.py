from prompt_utils_common import get_llm_output_amogh
from utils_common import rec_modifier, output_template
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
from typing import List,Dict
import fitz 
import unicodedata
import re
import pandas as pd
from utils_common import text_space_cleaner
import logging
import pdfplumber

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def extract_tables_from_pdf(pdf_path):
    tables = []
    with fitz.open(pdf_path) as doc:
        for page in doc[:5]:
            found_tables = page.find_tables()
            for tab in found_tables.tables:
                df = tab.to_pandas()
                df = df.astype(str).map(text_space_cleaner)
                tables.append(df)
        return tables


def find_heading_coordinates(pdf_path: str, headings: List[str]) -> Dict[str, Dict]:
    coords = {}
    normalized_targets = [normalize_key(h) for h in headings]

    for page_layout in extract_pages(pdf_path):
        page_num = page_layout.pageid - 1
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                raw_text = text_space_cleaner(element.get_text()).strip()
                norm_text = normalize_key(raw_text)
                for i, norm_target in enumerate(normalized_targets):
                    if norm_target in norm_text:
                        coords[headings[i]] = {
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


def extract_unstructured_text(pdf_path):
    def extract_with_markers(start_marker, end_marker):
        text = ""
        capture = False
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
                        return text_space_cleaner(text)  # Stop at first successful block
        return ""  

    text = extract_with_markers("Policy Coverage (What the policy covers?) (Policy Clause Number/s)", "Exclusions(What the policy not cover)")
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
    field_mapping = {
    "policy number": "policy_number",
    "policy no": "policy_number",
    "policy no.": "policy_number",
    "master policy number": "master_policy_number",
    "policy start date": "policy_start_date",
    "policy end date": "policy_end_date",
    "policy tenure": "policy_tenure",
    "policy type": "policy_type",
    "sum insured basis": "sum_insured_basis",
    "category": "category",
    "gstin": "gstin",
    "sac code": "sac_code",
    "policy issuance date": "policy_issuance_date",
    "policyholder name": "policy_holder_name",
    "policyholder": "policy_holder_name",  # new
    "tpa name": "tpa_name",
    "net premium": "net_premium",
    "gross premium": "gross_premium",
    "gst": "gst",
    "payment frequency": "payment_frequency",
    "room rent": "room_rent_limit",
    "icu limit": "icu_room_limit_metro"
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


def parse_icici(pdf_path):
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    

    final = output_template()  # moved up so it's accessible by set_field

    def set_field(path, value):
        keys = path.split(".")
        curr = final
        for key in keys[:-1]:
            if key not in curr or not isinstance(curr[key], dict):
                curr[key] = {}
            curr = curr[key]
        curr[keys[-1]] = value

    # Set all structured fields
    if "policy_number" in structured_data:
        set_field("extra.policy_number", structured_data["policy_number"])
    if "policy_holder_name" in structured_data:
        set_field("extra.name_policyholder", structured_data["policy_holder_name"])
    if "policy_start_date" in structured_data:
        set_field("extra.policy_start_date", structured_data["policy_start_date"])
    if "policy_end_date" in structured_data:
        set_field("extra.policy_end_date", structured_data["policy_end_date"])
    if "net_premium" in structured_data:
        set_field("premium_details.net_premium", structured_data["net_premium"])
    if "gst" in structured_data:
        set_field("premium_details.gst", structured_data["gst"])
    if "gross_premium" in structured_data:
        set_field("premium_details.gross_premium", structured_data["gross_premium"])
    if "payment_frequency" in structured_data:
        set_field("premium_details.payment_frequency", structured_data["payment_frequency"])
    if "room_rent_limit" in structured_data:
        set_field("room_rent.room_rent_limit", structured_data["room_rent_limit"])
    if "icu_room_limit_metro" in structured_data:
        set_field("room_rent.icu_room_limit_metro", structured_data["icu_room_limit_metro"])

    unstructured_text = extract_unstructured_text(pdf_path)

    print("\n📝 Unstructured Text Sent to LLM (First 50 lines):")

    for i, line in enumerate(unstructured_text.splitlines()):
        if i >= 50:
            print("... (truncated)")
            break   
        print(f"{i+1:02d}: {line}")
    
    print(f"\n🔢 Total Characters: {len(unstructured_text)}")
    print(f"🧠 Approx. Tokens (estimate): {len(unstructured_text) // 4}")

    

    llm_output = get_llm_output_amogh(unstructured_text)


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
        final["maternity"]["limit_normal_delivery"] = maternity.get("normal_delivery_metro", "")
        final["maternity"]["limit_C_Section"] = maternity.get("csection_delivery_metro", "")
        final["maternity"]["waiting_period"] = maternity.get("maternity_waiting_period", "")
        # final["maternity"]["no_of_deliveries"] = "2" if "first 2 children" in maternity.get("maternity_eligibility", "").lower() else ""
        final["maternity"]["complications_limit"] = maternity.get("complications_limit", "")
        final["maternity"]["pre_post_natal_expenses"] = maternity.get("pre_post_natal_expenses", "")
        final["maternity"]["twin_delivery_limit"] = maternity.get("twin_delivery_limit", "")
        final["maternity"]["infertility_treatment"] = maternity.get("infertility_treatment", "")
        final["maternity"]["well_baby_expenses"] = maternity.get("well_baby_expenses", "")
        final["maternity"]["well_mother_expenses"] = maternity.get("well_mother_expenses", "")
        final["maternity"]["maternity_eligibility"] = maternity.get("maternity_eligibility", "")

        
        pre_post = maternity.get("pre_post_natal_expenses", "")
        final["pre_and_post_natal_expenses_IPD"]["expenses_limit_IPD"] = pre_post
        final["pre_and_post_natal_expenses_IPD"]["applicability"] = pre_post
        final["pre_and_post_natal_expenses_OPD"]["expenses_limit_OPD"] = pre_post

    
    if "day_care" in llm_output:
        final["day_care"] = llm_output["day_care"]
    if "day_care" in llm_output:
        final["day_care_treatment"]["day_care_treatment"] = llm_output["day_care"].get("covered", "Not Applicable")

    
    modern = llm_output.get("modern_treatment", {})
    if modern:
        final["modern_treatment"] = modern
        if any("50%" in str(v).lower() or "covered" in str(v).lower() for v in modern.values()):
            final["medical_advancement_surgery"]["medical_advancement_surgery_limit"] = "Covered up to 50 % of SI."

    
    other = llm_output.get("other_covers", {})
    if other:
        final["other_covers"].update(other)
        lasik = other.get("lasik", "")
        if "+/-" in lasik or "lens" in lasik.lower():
            final["refractive_error_correction_expenses"]["eye_power"] = "7"
            final["refractive_error_correction_expenses"]["si_limit"] = lasik
        if "terrorism_cover" in other and "cover" in other["terrorism_cover"].lower():
            final["other_covers"]["terrorism_cover"] = "Covered"

    
    if "room_rent_limit" in structured_data:
        final["room_rent"]["room_rent_limit"] = structured_data.pop("room_rent_limit")
    if "icu_room_limit_metro" in structured_data:
        final["room_rent"]["icu_room_limit_metro"] = structured_data.pop("icu_room_limit_metro")

    for key in ["net_premium", "gst", "gross_premium", "payment_frequency"]:
        if key in structured_data:
            final["premium_details"][key] = structured_data.pop(key)

  
    rec_modifier(final)

    return final