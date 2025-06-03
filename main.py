import json
from parsing_utils import extract_text_near_heading, find_heading_coordinates, \
    extract_text_with_coordinates, get_headings, output, table_loader_first
from prompt_utils import prompt_field_unmatched_policy
from utils import rec_modifier, remove_days, remove_plusminus


def parsing(pdf_path: str = "coverage_documents/PDF1.pdf", llm_parse: bool = False):
    actual_headings = get_headings()
    text_with_coords = extract_text_with_coordinates(pdf_path)
    unstructured_text = ""
    con = False
    con2 = False
    for i in range(max(text_with_coords.keys()) + 1):
        for item in text_with_coords[i]:
            # print(item['text'])
            if not con:
                if "claim conditions" == item['text'].lower():
                    con = True
                    unstructured_text += item['text'] + "\n"
            else:
                if "quote disclaim" in item['text'].lower():
                    # con2 = True
                    # break
                    pass
                unstructured_text += item['text'] + "\n"
        if con2:
            break
    # print("===\n", unstructured_text, "\n===")
    heading_coords = find_heading_coordinates(text_with_coords, actual_headings)
    actual_headings = get_headings()
    extracted_data = extract_text_near_heading(text_with_coords, actual_headings, heading_coords)
    # print("===\n", extracted_data, "\n===")
    result = extracted_data
    # result = {}
    # for heading, data in extracted_data.items():
        # heading = heading.replace(" ", "_").lower()
        # result[heading] = data
    # print(json.dumps(result, indent=4))
    # print(len(result))

    if not llm_parse:
        return result

    maternity_expense = result["Max liability on maternity exp"]
    room_restrictions = result["Room Restrictions"]


    llm_out = eval(prompt_field_unmatched_policy(unstructured_text, maternity_expense, room_restrictions))

    # llm_out = prompt_field_unmatched_policy_schema(unstructured_text, maternity_expense, room_restrictions)
    # llm_out = {}

    rel_cov_table = table_loader_first(pdf_path)
    result["relations"] = []
    for _, row in rel_cov_table.iterrows():
        result["relations"].append(row["Relation"])
        if row['Relation'] == "EMPLOYEES":
            llm_out["co_pay"]["policy_co_payment_factor"] = row["Percentage"]
            if row['Pre-Existing Diseases'] == "Covered":
                llm_out["pre_existing_disease_and_specified_disease"] = {
                    "pre_existing_disease_and_specified_disease_waiting_period": "Waived Off"}
            else:
                llm_out["pre_existing_disease_and_specified_disease"] = {
                    "pre_existing_disease_and_specified_disease_waiting_period": "Applicable"}
        elif row['Relation'] == "CHILD":
            llm_out["maternity_expenses"]["no_of_deliveries"] = row["Limit on Number of children"]

    # print(llm_out)
    llm_out["maternity_expenses"]["limit_normal_delivery"] = result["Max for normal delivery"]
    llm_out["maternity_expenses"]["limit_C_Section"] = result["Max for LSCS"]
    if "not" in result["9 Months waiting period"].lower():
        llm_out["maternity_expenses"]["waiting_period"] = "No waiting period"
    else:
        llm_out["maternity_expenses"]["waiting_period"] = "9 Months waiting period"
    llm_out["pre_hospitalization"] = {"pre_hospitalization_period": result["Pre Hospitalization Period[Days]"]}
    llm_out["post_hospitalization"] = {"post_hospitalization_period": result["Post Hospitalization Period[Days]"]}

    llm_out = llm_out | {"headings": result}

    rec_modifier(llm_out)
    output(llm_out)

    return llm_out


if __name__ == "__main__":
    pdf_path = "coverage_documents/PDF1.pdf"
    parsing(pdf_path, llm_parse=False)