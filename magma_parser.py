from parsing_utils import table_loader_multiple
import pandas as pd
import json
from utils import output_template_unmatched, convert_to_dict, key_substring
from collections import Counter
import re
import copy
from prompt_utils import prompt_field_magma

# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# pd.set_option('display.width', None)
# pd.set_option('display.max_colwidth', None)


file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-9906-8604-2025-117161\RAPID ENGINEERING COMPANY PVT LIMITED_ GMC policy Copy 24-25.pdf"
# file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-9906-8604-2025-117114\GMC policy Copy 24-25.pdf"
file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-1501-8604-2025-115649\\08dd8efe-5f8a-4811-894d-bf57fb2c289a.pdf"

# dfs = table_loader_multiple(file_path, "Policy Schedule /TAX INVOICE", "IN WITNESS WHEREOF")



def manual_parsing(file_path):
    dfs = table_loader_multiple(file_path, "Policy Schedule /TAX INVOICE", "IN WITNESS WHEREOF")
    key_counts = Counter()
    result = {}

    next_df = False
    for df in dfs:
        # print(df)
        cols = df.columns.tolist()
        if 'Policy Details' in cols:
            extra_result = df.set_index(df.columns[0])[df.columns[1]].to_dict()
        elif "Cover" in cols and "Coverage Details" in cols:
            # print(df, cols)
            next_df = True
            convert_to_dict(df, result, key_counts)
            # continue
        elif next_df:
            next_df = False
            convert_to_dict(df, result, key_counts, include_headers=True)

    # print(json.dumps(result, indent=4))
    # print(json.dumps(extra_result, indent=4))

    output = output_template_unmatched(True)
    llm_input = copy.deepcopy(output)

    print(len(result), len(output))

    rent = result.pop("Room Rent", None)
    if rent:
        rent_parts = re.split(r'\.(?![^\(]*\))', rent, maxsplit=1)
        if len(rent_parts) >= 2:
            output["room_rent"]["room_rent_limit"] = rent_parts[0]
            output["room_rent"]["options_for_deductions"] = rent_parts[1]
        else:
            output["room_rent"]["room_rent_limit"] = rent
            output["room_rent"]["options_for_deductions"] = ""
        llm_input.pop("room_rent")

    maternity_waiting = key_substring(result, "Maternity waiting") or key_substring(result, "9 Months Waiting")
    if maternity_waiting:
        maternity_waiting_con = result.pop(maternity_waiting[0])
        output["maternity_expenses"]["waiting_period"] = maternity_waiting_con

    maternity = key_substring(result, "Normal & C- Section")
    if maternity:
        maternity_con = result.pop(maternity[0])
        if "not covered" in maternity_con.lower():
            output["maternity_expenses"]["no_of_deliveries"] = 0
            output["maternity_expenses"]["limit_normal_delivery"] = 0
            output["maternity_expenses"]["limit_C_Section"] = 0
        else:
            numbers = [int(x.replace(',', '')) for x in re.findall(r'\d[\d,]*', maternity_con)]
            output["maternity_expenses"]["limit_normal_delivery"] = numbers[0]
            if len(numbers) > 1:
                output["maternity_expenses"]["limit_C_Section"] = numbers[1]
            else:
                output["maternity_expenses"]["limit_C_Section"] = numbers[0]
                # assumption that same value given for both, no supporting data
            if len(numbers) > 2:
                output["maternity_expenses"]["no_of_deliveries"] = numbers[2]
        llm_input.pop("maternity_expenses")

    pre_post = result.pop("Pre - Post Hospitalisation", None)
    if pre_post:
        (output["pre_hospitalization"]["pre_hospitalization_period"],
         output["post_hospitalization"]["post_hospitalization_period"]) = [int(x) for x in re.findall(r'\d+', pre_post)[:2]]
        llm_input.pop("pre_hospitalization")
        llm_input.pop("post_hospitalization")

    pre_disease = result.pop("Pre-existing Disease", None)
    if pre_disease:
        waiver = result.pop("Specific disease waiting period", None)
        output["pre_existing_disease_and_specified_disease"]["pre_existing_disease_and_specified_disease_waiting_period"] = waiver or pre_disease
        llm_input.pop("pre_existing_disease_and_specified_disease")

    ambulance = result.pop("Ambulance Service", None)
    if ambulance:
        ambulance_lim = [int(x) for x in re.findall(r'\d+', pre_post)]
        if len(ambulance_lim) == 1:
            output["road_ambulance"]["road_ambulance_limit"] = ambulance_lim[0]
        else:
            output["road_ambulance"]["road_ambulance_limit"] = ambulance
        llm_input.pop("road_ambulance")

    copay = result.pop("Co-Payment", None)
    if copay:
        if "not applicable" in copay.lower():
            pass
        else:
            output["co_pay"]["policy_co_payment_factor"] = copay
        llm_input.pop("co_pay")

    ayush = key_substring(result, "Ayush")
    if ayush:
        ayush_con = result.pop(ayush[0])
        if "not applicable" in ayush_con.lower():
            pass
        else:
            val = re.findall(r'\d+%|\d+', ayush_con)
            output["ayush_treatment"]["ayush_treatment_limit"] = val[0] if val else ayush_con
        llm_input.pop("ayush_treatment")
    # sometimes ayush is also mentioned in special condition, confirm what to do

    natal = result.pop("Pre/Post Natal Expenses", None)
    if natal:
        if "not covered" in natal.lower():
            output["pre_and_post_natal_expenses_IPD"]["applicability"] = natal
        else:
            val = re.findall(r'\d+%|\d+', natal)
            output["pre_and_post_natal_expenses_IPD"]["expenses_limit_IPD"] = val[0] if val else ""
            output["pre_and_post_natal_expenses_IPD"]["applicability"] = natal
        llm_input.pop("pre_and_post_natal_expenses_IPD")

    day = result.pop("Day care procedures", None)
    if day:
        output["day_care_treatment"]["day_care_treatment"] = day
        llm_input.pop("day_care_treatment")

    organ = result.pop("Organ donor expenses", None)
    if organ:
        output["organ_donor_expenses"]["organ_donor_expenses"] = organ
        llm_input.pop("organ_donor_expenses")

    # print(len(result), len(output), len(llm_input))
    print(json.dumps(output, indent=4))
    print(json.dumps(llm_input, indent=4))

    return output, llm_input, extra_result, result

def llm_parsing(result, llm_input):
    llm_output = eval(prompt_field_magma(result, llm_input))
    print(json.dumps(llm_output, indent=4))


if __name__ == "__main__":
    output, llm_input, extra_result, result = manual_parsing(file_path)
    llm_parsing(result, llm_input)
