from prompt_utils_common import get_llm_output_amogh
# from utils_common import rec_modifier, remap_keys
from utils_common import rec_modifier
import pdfplumber
import fitz  # PyMuPDF
import unicodedata
import re
from utils_common import text_space_cleaner
import pandas as pd

def extract_tables_from_pdf(pdf_path):
    tables = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            found_tables = page.find_tables()
            for tab in found_tables.tables:
                df = tab.to_pandas()
                df = df.astype(str).applymap(text_space_cleaner)
                tables.append(df)
    return tables

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
        return ""  # Nothing found

    # try primary markers first
    text = extract_with_markers("Consolidated Stamp Duty paid vide E-challan GRN ", "Lasik surgery")
    
    # fallback to alternate markers if primary fails
    if not text.strip():
        text = extract_with_markers("Consolidated Stamp Duty paid vide E-challan GRN ", "Special Conditions (if any)")
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
        # "policy no": "policy_no",
        "policy number": "policy_no",
        "policyholder name": "policyholder_name",
        "policyholder": "policyholder_name",
        "policy period start date": "start_date",
        "start date & time of policy": "start_date",
        "expiry date & time of policy": "end_date",
        "policy period end date": "end_date",
        "product name": "product_name",
        "product code": "product_code",
        "policy issued date & time": "issued_date",
        "issuing office": "issuing_office",
        "policy servicing office": "servicing_office",
        "net premium": "net_premium",
        "gross premium": "gross_premium",
        "igst": "igst",
        "gstin": "gst_registration_no",
        "sac code": "sac_code",
        "category": "Category",
        "policy number": "policy_number",
        "start date time of policy from 0000 hrs of 12042024": "policy_start_date",
        "expiry date time of policy to midnight 2359 hrs of 11042025": "policy_end_date",
        "policy issued date time": "issued_date",

    }

    # for df in tables:
    #     df.dropna(how="all", inplace=True)
    #     df = df.astype(str).applymap(text_space_cleaner)

    #     for _, row in df.iterrows():
    #         try:
    #             raw_key = row.iloc[0]
    #             raw_value = row.iloc[1] if len(row) > 1 else None
    #         except Exception as e:
    #             print(f"[ERROR accessing row]: {e}")
    #             continue

    #         key = normalize_key(str(raw_key))
    #         value = text_space_cleaner(str(raw_value)) if raw_value else None

    #         print(f"[DEBUG] Raw Key: '{raw_key}' → Normalized: '{key}'")
    #         print(f"[DEBUG] Raw Value: '{raw_value}' → Normalized: '{value}'")

    #         if key in field_mapping:
    #             mapped_field = field_mapping[key]
    #             if mapped_field not in extracted_data:
    #                 extracted_data[mapped_field] = value

    # return extracted_data
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


def parse_aditya(pdf_path):
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)
    unstructured_text = extract_unstructured_text(pdf_path)

    print("\n Unstructured Text Sent to LLM (First 50 lines):")
    for i, line in enumerate(unstructured_text.splitlines()):
        if i >= 50:
            print("... (truncated)")
            break
        print(f"{i+1:02d}: {line}")
    
    print(f"\n Total Characters: {len(unstructured_text)}")
    print(f" Approx. Tokens (estimate): {len(unstructured_text) // 4}")

    llm_output = get_llm_output_amogh(unstructured_text)

    # final = remap_keys(llm_output)
    final = {**llm_output}

    final.setdefault("policy_info", {}).update(structured_data)
    rec_modifier(final)
    # return final
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
