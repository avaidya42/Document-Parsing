import fitz 
import unicodedata
import pdfplumber
import re
import pytesseract
from pdf2image import convert_from_path
from utils_common import text_space_cleaner,rec_modifier
import pandas as pd
import json
from prompt_utils_common import get_llm_output_nilay
from output_schema_common import OutputFull


def extract_tables_from_pdf(pdf_path):
    tables = []
    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc[:5], 1):  # limiting extraction to first 5 pages
            found_tables = page.find_tables()
            for tab in found_tables.tables:
                df = tab.to_pandas()
                df = df.astype(str).map(text_space_cleaner)
                tables.append(df)
    return tables

def extract_unstructured_text_nivabupa(pdf_path):
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
        return ""  # Nothing found

    # try primary markers first
    text = extract_with_markers("Benefit Structure", "Per Person premium Rater (Excluding GST)")
    
    # fallback to alternate markers if primary fails
    if not text.strip():
        text = extract_with_markers("Benefits Opted", "Policy Rater")

    return text


def normalize_key(key: str) -> str:
    key = unicodedata.normalize("NFKD", key)
    key = key.encode("ascii", "ignore").decode("utf-8")
    key = key.strip().lower()
    key = re.sub(r'[^a-z0-9 ]', '', key)
    key = re.sub(r'\s+', ' ', key)
    key = key.replace("’", "'")
    return key

# def parse_table_data(tables):
#     extracted_data = {}

#     field_mapping = {
#         "policy number": "policy_number",
#         "policyholders name": "name_policyholder",
#         "date and time of policy commencement": "policy_start_date",
#         "date and time of policy expiry": "policy_end_date",
#         "total no of lives": "primary_insured_members",
#         "aggregate sum insured": "total_sum_insured",
#         "listed day care treatment": "day_care_treatment",
#         "pre hospitalization medical expenses": "pre_hospitalization_period",
#         "post hospitalization medical expenses": "post_hospitalization_period",
#         "emergency ambulance" : "road_ambulance_limit",
#         "air ambulance" : "air_ambulance_limit",
#         "ayush treatment" : "ayush_treatment_limit"
#     }

#     for df in tables:
#         df.dropna(how="all", inplace=True)
#         df = df.astype(str).map(text_space_cleaner)

#         for _, row in df.iterrows():
#             try:
#                 key = normalize_key(str(row.iloc[0]))
#                 value = text_space_cleaner(str(row.iloc[1])) if len(row) > 1 else None
#                 if key in field_mapping and field_mapping[key] not in extracted_data:
#                     extracted_data[field_mapping[key]] = value
#             except Exception:
#                 continue

#     return extracted_data

def parse_table_data(tables):
    extracted_data = {}

    field_mapping = {
        "policy number": "policy_number",
        "policyholders name": "name_policyholder",
        "date and time of policy commencement": "policy_start_date",
        "date and time of policy expiry": "policy_end_date",
        "total no of lives" : "primary_insured_members",
        "aggregate sum insured": "total_sum_insured",
        "listed day care treatment": "day_care_treatment",
        "pre hospitalization medical expenses": "pre_hospitalization_period",
        "post hospitalization medical expenses": "post_hospitalization_period",
        "emergency ambulance": "road_ambulance_limit",
        "air ambulance": "air_ambulance_limit",
        "ayush treatment": "ayush_treatment_limit"
    }

    # print("\n DEBUG: Keys encountered in tables")
    for df in tables:
        df.dropna(how="all", inplace=True)
        df = df.astype(str).map(text_space_cleaner)

        for _, row in df.iterrows():
            try:
                raw_key = normalize_key(str(row.iloc[0]))
                # print("  -", raw_key)

                # Search for the first non-empty value after the key
                value = None
                for cell in row[1:]:
                    clean_cell = text_space_cleaner(str(cell))
                    if clean_cell and clean_cell.lower() != "none":
                        value = clean_cell
                        break

                if raw_key in field_mapping and field_mapping[raw_key] not in extracted_data:
                    extracted_data[field_mapping[raw_key]] = value
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

def final_parser_nivabupa(pdf_path):
    # try structured table extraction
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    # print("\n Extracted structured data from tables:")
    # if not structured_data:
    #     print(" No structured data was extracted.")
    # else:
    #     for k, v in structured_data.items():
    #         print(f"  {k}: {v}")

    # get unstructured text and table text (as fallback for LLM)
    unstructured_text = extract_unstructured_text_nivabupa(pdf_path)

    # print("\n Unstructured Text Sent to LLM (First 50 lines):")
    # for i, line in enumerate(unstructured_text.splitlines()):
    #     if i >= 50:
    #         print("... (truncated)")
    #         break
    #     print(f"{i+1:02d}: {line}")

    print(f"\n Total Characters: {len(unstructured_text)}")
    print(f" Approx. Tokens (estimate): {len(unstructured_text) // 4}")

    # get LLM output
    llm_output = get_llm_output_nilay(unstructured_text)

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
    if "primary_insured_members" in structured_data:
        set_field("extra.primary_insured_members", structured_data["primary_insured_members"])
    if "total_sum_insured" in structured_data:
        set_field("extra.total_sum_insured", structured_data["total_sum_insured"])
    if "day_care_treatment" in structured_data:
        set_field("day_care_treatment.day_care_treatment", structured_data["day_care_treatment"])
    if "pre_hospitalization_period" in structured_data:
        set_field("pre_hospitalization.pre_hospitalization_period",structured_data["pre_hospitalization_period"])
    if "post_hospitalization_period" in structured_data:
        set_field("post_hospitalization.post_hospitalization_period",structured_data["post_hospitalization_period"])
    if "road_ambulance_limit" in structured_data:
        set_field("road_ambulance.road_ambulance_limit", structured_data["road_ambulance_limit"])
    if "air_ambulance_limit" in structured_data:
        set_field("extra.air_ambulance_limit", structured_data["air_ambulance_limit"])
    if "ayush_treatment_limit" in structured_data:
        set_field("ayush_treatment.ayush_treatment_limit", structured_data["ayush_treatment_limit"])

    rec_modifier(final)

    return final
