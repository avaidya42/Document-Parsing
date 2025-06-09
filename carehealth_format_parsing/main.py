import json
from parsing_utils import extract_tables_from_pdf, extract_unstructured_text, parse_table_data
from prompt_utils import get_llm_output
from output_schema import OutputFull
from utils import rec_modifier

def final_parser(pdf_path, output_path="llm_result.json"):
    # extracting structured values from tables
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    # extracting unstructured text and parse with LLM
    unstructured_text = extract_unstructured_text(pdf_path)
    llm_output = get_llm_output(unstructured_text)
    
    # unpack llm_output dict and store in final
    final = {**llm_output}

    if "policy_no" in structured_data:
        final["policy_details"]["policy_number"] = structured_data["policy_number"]
    if "name_policyholder" in structured_data:
        final["policy_details"]["name_policyholder"] = structured_data["name_policyholder"]
    if "policy_start_date" in structured_data:
        final["policy_details"]["policy_start_date"] = structured_data["policy_start_date"]
    if "policy_end_date" in structured_data:
        final["policy_details"]["policy_end_date"] = structured_data["policy_end_date"]
    if "sum_insured" in structured_data:
        final["corporate_buffer"]["total_sum_insured"] = structured_data["total_sum_insured"]
    if "primary_insured_members" in structured_data:
        final["corporate_buffer"]["primary_insured_members"] = structured_data["primary_insured_members"]

    # clean values
    rec_modifier(final)

    # dump in json file
    with open(output_path, "w") as f:
        json.dump(final, f, indent=4)

    print(f" Final parsed data written to {output_path}")
    return final

if __name__ == "__main__":
    final_parser("Care Health Insurance Ltd/GHF-9906-8604-2025-116580/1. MCUBE ADVISORS__POLICY COPY.pdf")
