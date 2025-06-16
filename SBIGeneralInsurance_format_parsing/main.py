import json
from parsing_utils import (
    extract_tables_from_pdf,
    extract_unstructured_text,
    parse_table_data,
    find_heading_coordinates,
    extract_text_near_heading
)
from prompt_utils import get_llm_output
from output_schema import OutputFull
from utils import rec_modifier

def set_field(path, value, final):
    keys = path.split(".")
    curr = final
    for key in keys[:-1]:
        if key not in curr or not isinstance(curr[key], dict):
            curr[key] = {}
        curr = curr[key]
    curr[keys[-1]] = value

def final_parser(pdf_path, output_path="llm_result.json"):
    field_source = {}

    # table data
    tables = extract_tables_from_pdf(pdf_path)
    structured_data = parse_table_data(tables)
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
    unstructured_text = extract_unstructured_text(pdf_path)
    table_text = "\n".join(df.to_string(index=False) for df in tables)
    unstructured_text += "\n\n" + table_text
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
    if "sum_insured" in structured_data:
        set_field("corporate_buffer.sum_insured", structured_data["sum_insured"], final)
    if "total_number_insured" in structured_data:
        set_field("extra.total_number_insured", structured_data["total_number_insured"], final)

    rec_modifier(final)

    with open(output_path, "w") as f:
        json.dump(final, f, indent=4)

    print(f"✅ Final parsed data written to {output_path}")

    return final

if __name__ == "__main__":
    final_parser("SBI General Insurance/GHF-1113-8604-2025-114132/GMC policy copy.pdf")
