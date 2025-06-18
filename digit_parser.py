import json
# from parsing_utils import extract_tables_from_pdf, extract_unstructured_text, parse_table_data
from prompt_utils_common import get_llm_output
from utils_common import rec_modifier, output_template




import fitz  # PyMuPDF
import unicodedata
import re
from utils_common import text_space_cleaner
import pandas as pd
import logging

# Suppress debug messages unless explicitly enabled
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


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
    unstructured_text = extract_unstructured_text(pdf_path)
    llm_output = get_llm_output(unstructured_text)

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

    # Step 2: Maternity
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

    # Step 3: Day care treatment
    day_care = llm_output.get("day_care", {})
    if day_care:
        final["day_care_treatment"]["day_care_treatment"] = day_care.get("covered", "Not Applicable")

    # Step 4: Modern treatments
    modern = llm_output.get("modern_treatment", {})
    if modern:
        if "modern_treatment" not in final:
            final["modern_treatment"] = {}
        final["modern_treatment"].update(modern)
        if any("50%" in str(v) for v in modern.values()):
            final["medical_advancement_surgery"]["medical_advancement_surgery_limit"] = "Covered up to 50 % of SI."

    # Step 5: LASIK logic from "other_covers"
    other = llm_output.get("other_covers", {})
    lasik = other.get("lasik", "")
    if "+/-" in lasik or "lens" in lasik.lower():
        final["refractive_error_correction_expenses"]["eye_power"] = "7"
        final["refractive_error_correction_expenses"]["si_limit"] = lasik

    # Step 6: Other Covers: Terrorism
    if "other_covers" not in final:
        final["other_covers"] = {}
    if "terrorism_cover" in other and "cover" in other["terrorism_cover"].lower():
        final["other_covers"]["terrorism_cover"] = "Covered"

    # # Step 7: Merge structured table data
    # final["policy_info"].update(structured_data)

    # Step 8: Clean unwanted fields from structured mapping
    # for k in ["start_date", "end_date", "master_policy_no"]:
    #     final["policy_info"].pop(k, None)

    # Step 9: Normalize final output
    rec_modifier(final)
    return final
