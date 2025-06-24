from prompt_utils_common import get_llm_output_amogh
from utils_common import rec_modifier, remap_keys
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
    text = extract_with_markers("Stamp Duty", "Special Conditions (if any)")
    
    # fallback to alternate markers if primary fails
    # if not text.strip():
    #     text = extract_with_markers("Benefits Opted", "Policy Rater")
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
        # "total sum insured": "total_sum_insured",
        # "sum insured per member": "sum_insured_per_member",
        # "total sum insured": "total_sum_insured",
        "net premium": "net_premium",
        "gross premium": "gross_premium",
        "igst": "igst",
        "gstin": "gst_registration_no",
        "sac code": "sac_code",
        "category": "Category"
    }

    for df in tables:
        df.dropna(how="all", inplace=True)
        df = df.astype(str).applymap(text_space_cleaner)

        for _, row in df.iterrows():
            try:
                raw_key = row.iloc[0]
                raw_value = row.iloc[1] if len(row) > 1 else None
            except Exception as e:
                print(f"[ERROR accessing row]: {e}")
                continue

            key = normalize_key(str(raw_key))
            value = text_space_cleaner(str(raw_value)) if raw_value else None

            print(f"[DEBUG] Raw Key: '{raw_key}' → Normalized: '{key}'")
            print(f"[DEBUG] Raw Value: '{raw_value}' → Normalized: '{value}'")

            if key in field_mapping:
                mapped_field = field_mapping[key]
                if mapped_field not in extracted_data:
                    extracted_data[mapped_field] = value

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

    final = remap_keys(llm_output)

    final.setdefault("policy_info", {}).update(structured_data)
    rec_modifier(final)
    return final