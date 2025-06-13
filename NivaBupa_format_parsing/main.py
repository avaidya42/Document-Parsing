import json
from parsing_utils import extract_tables_from_pdf, extract_unstructured_text, parse_table_data, extract_text_from_scanned_pdf
from prompt_utils import get_llm_output
from output_schema import OutputFull
from utils import rec_modifier

def final_parser(pdf_path, output_path="llm_result.json"):
    # try structured table extraction
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)

    # get unstructured text and table text (as fallback for LLM)
    unstructured_text = extract_unstructured_text(pdf_path)
    table_text = "\n".join(df.to_string(index=False) for df in tables)
    unstructured_text += "\n\n" + table_text

    # get LLM output
    llm_output = get_llm_output(unstructured_text)

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

    if "sum_insured" in structured_data:
        set_field("corporate_buffer.sum_insured", structured_data["sum_insured"])

    if "day_care_treatment" in structured_data:
        set_field("day_care_treatment.day_care_treatment", structured_data["day_care_treatment"])

    rec_modifier(final)

    with open(output_path, "w") as f:
        json.dump(final, f, indent=4)

    print(f"Final parsed data written to {output_path}")
    return final

if __name__ == "__main__":
    final_parser("Niva Bupa Health Insurance/GHF-9906-8604-2025-114461/Current Policy Copy.pdf")