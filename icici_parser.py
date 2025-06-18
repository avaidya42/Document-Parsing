# from parsing_utils import extract_tables_from_pdf, extract_unstructured_text, parse_table_data
from prompt_utils_common import get_llm_output
from utils_common import rec_modifier, output_template



import fitz  # PyMuPDF
import unicodedata
import re
import pandas as pd
from utils_common import text_space_cleaner
import logging

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
    "policy number": "policy_number",
    "master policy number": "master_policy_number",
    "policy start date": "policy_start_date",
    "policy end date": "policy_end_date",
    "policy tenure": "policy_tenure",
    "policy type": "policy_type",
    "sum insured": "sum_insured",
    "sum insured basis": "sum_insured_basis",
    "category": "category",
    "gstin": "gstin",
    "sac code": "sac_code",
    "policy issuance date": "policy_issuance_date",
    "policyholder name": "policy_holder_name",
    "tpa name": "tpa_name",

    # ✅ Add these to capture premium & rent info
    "net premium": "net_premium",
    "gross premium": "gross_premium",
    "gst": "gst",
    "payment frequency": "payment_frequency",

    # ✅ Critical for room rent logic
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
    unstructured_text = extract_unstructured_text(pdf_path)
    llm_output = get_llm_output(unstructured_text)

    final = output_template()

    # Skip LLM-driven nested mappings for these sections (handled separately)
    skip_keys = {"maternity", "modern_treatment", "day_care", "other_covers"}
    for section, values in llm_output.items():
        if section in skip_keys:
            continue
        if section not in final:
            final[section] = values
        elif isinstance(values, dict):
            final[section].update(values)

    # ---------- Maternity ----------
    maternity = llm_output.get("maternity", {})
    if maternity:
        final["maternity"]["limit_normal_delivery"] = maternity.get("normal_delivery_metro", "")
        final["maternity"]["limit_C_Section"] = maternity.get("csection_delivery_metro", "")
        final["maternity"]["waiting_period"] = maternity.get("maternity_waiting_period", "")
        final["maternity"]["no_of_deliveries"] = "2" if "first 2 children" in maternity.get("maternity_eligibility", "").lower() else ""
        final["maternity"]["complications_limit"] = maternity.get("complications_limit", "")
        final["maternity"]["pre_post_natal_expenses"] = maternity.get("pre_post_natal_expenses", "")
        final["maternity"]["twin_delivery_limit"] = maternity.get("twin_delivery_limit", "")
        final["maternity"]["infertility_treatment"] = maternity.get("infertility_treatment", "")
        final["maternity"]["well_baby_expenses"] = maternity.get("well_baby_expenses", "")
        final["maternity"]["well_mother_expenses"] = maternity.get("well_mother_expenses", "")
        final["maternity"]["maternity_eligibility"] = maternity.get("maternity_eligibility", "")

        # Map pre/post to other fields as well
        pre_post = maternity.get("pre_post_natal_expenses", "")
        final["pre_and_post_natal_expenses_IPD"]["expenses_limit_IPD"] = pre_post
        final["pre_and_post_natal_expenses_IPD"]["applicability"] = pre_post
        final["pre_and_post_natal_expenses_OPD"]["expenses_limit_OPD"] = pre_post

    # ---------- Day Care ----------
    if "day_care" in llm_output:
        final["day_care"] = llm_output["day_care"]
    if "day_care" in llm_output:
        final["day_care_treatment"]["day_care_treatment"] = llm_output["day_care"].get("covered", "Not Applicable")

    # ---------- Modern Treatments ----------
    modern = llm_output.get("modern_treatment", {})
    if modern:
        final["modern_treatment"] = modern
        if any("50%" in str(v).lower() or "covered" in str(v).lower() for v in modern.values()):
            final["medical_advancement_surgery"]["medical_advancement_surgery_limit"] = "Covered up to 50 % of SI."

    # ---------- Other Covers ----------
    other = llm_output.get("other_covers", {})
    if other:
        final["other_covers"].update(other)
        lasik = other.get("lasik", "")
        if "+/-" in lasik or "lens" in lasik.lower():
            final["refractive_error_correction_expenses"]["eye_power"] = "7"
            final["refractive_error_correction_expenses"]["si_limit"] = lasik
        if "terrorism_cover" in other and "cover" in other["terrorism_cover"].lower():
            final["other_covers"]["terrorism_cover"] = "Covered"

    # ---------- Merge Structured Data ----------
    # → Move key fields from structured table output into correct sections
    if "room_rent_limit" in structured_data:
        final["room_rent"]["room_rent_limit"] = structured_data.pop("room_rent_limit")
    if "icu_room_limit_metro" in structured_data:
        final["room_rent"]["icu_room_limit_metro"] = structured_data.pop("icu_room_limit_metro")

    for key in ["net_premium", "gst", "gross_premium", "payment_frequency"]:
        if key in structured_data:
            final["premium_details"][key] = structured_data.pop(key)

    # final["policy_info"].update(structured_data)

    # # ---------- Cleanup redundant keys ----------
    # for redundant_key in ["start_date", "end_date", "master_policy_no"]:
    #     final["policy_info"].pop(redundant_key, None)

    # ---------- Normalize nulls/None/cleanup ----------
    rec_modifier(final)

    return final