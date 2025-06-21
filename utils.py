from openai import OpenAI
import pandas as pd
from io import BytesIO
import re
import torch
import gc

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='.env')  # 👈 Explicitly load api.env
api_key = os.getenv("OPENAI_API_KEY")

from openai import OpenAI
client = OpenAI(api_key=api_key)


client = OpenAI(
    api_key='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'
)
sec_api_key = "5b19c57b27218997d0e435e48eae7e9f70c40d06c3c8a10fc2567edac632e70c"
sec_api_endpoint = "https://api.sec-api.io/filing-reader"
serp_api_key = "bfedd3505964964bb55e85bba89b8403faf86956ae1e876bbfd413f661704f59"


def get_completion_from_messages(messages, model = 'gpt-4o-mini', temperature=0):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    print("Input Tokens: ", response.usage.prompt_tokens)
    print("Output Tokens: ", response.usage.completion_tokens)
    return response.choices[0].message.content


def get_completion_schema(messages, Format, model = 'gpt-4o-mini', temperature=0):
    response = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format=Format
    )
    print("Input Tokens: ", response.usage.prompt_tokens)
    print("Output Tokens: ", response.usage.completion_tokens)
    return (response.choices[0].message.parsed).model_dump()


def get_completion_qwen(messages, model, tokenizer):
    input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to("cuda")

    outputs = model.generate(
        input_ids,
        max_new_tokens=4096,
        eos_token_id=tokenizer.eos_token_id,
        do_sample=True,
        temperature=0.1,
        top_p=0.9,
    )

    response = outputs[0][input_ids.shape[-1]:]
    summary = tokenizer.decode(response, skip_special_tokens=True)

    del outputs
    del response
    gc.collect()
    torch.cuda.empty_cache()

    return summary


def output_template():
    heading_outputs = {"maternity_expenses": {"limit_normal_delivery": "", "limit_C_Section": "",
                                              "waiting_period": ["9 Months waiting period", "No waiting period"]},
                       "pre_hospitalization": {"pre_hospitalization_period": ""},
                       "post_hospitalization": {"post_hospitalization_period": ""}}
    # these are added to the final result without the help of a llm

    output = {"day_care_treatment": {"day_care_treatment": ""},
              "organ_donor_expenses": {"organ_donor_expenses": ""},
              "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "",
                                                  "applicability": ["Within Maternity", "Over & Above Maternity"]},
              "maternity_expenses": {"no_of_deliveries": ""},
              "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
              "corporate_buffer": {"sum_insured": "",
                                   "type_of_ailment": ["All Accidents & Illness", "For Critical Ailments only",
                                                       "For Accidents Only"],
                                   "type_of_coverage": ["Upto Per Family SI", "Upto Full Corporate Buffer SI"]},
              "refractive_error_correction_expenses": {"si_limit": "", "eye_power": ""},
              "hiv_anti_retroviral_therapy": {"hiv_anti_retroviral_therapy": ""},
              "home_nursing_benefit": {"per_week_benefit": "", "number_of_weeks": ""},
              "preventive_health_check_up": {"benefit_limit": "", "clinic_options": ["All Clinics and Hospitals",
                                                                                     "Network Clinic and Hospitals only"]},
              "opd_expenses": {"benefit_limit": ""},
              "physiotherapy_on_opd_basis": {"benefit_limit": "",
                                             "coverage_type": ["Accidental Body Injury only", "Illness only",
                                                               "Accidental Body Injury and Illness"]},
              "dental_care": {"benefit_limit": ""},
              "mental_illness": {"benefit_limit": ""},
              "vision_expenses_cover": {"benefit_limit": ""},
              "obesity_control_coverage": {"obesity_control_coverage": ""},
              "co_pay": {"co_pay_type": ["All Claims", "Non-Network Hospitals/Clinics", "Not Applicable"],
                         "policy_co_payment_factor": ["5% Copay", "10% Copay", "15% Copay", "20% Copay",
                                                      "25% Copay", "30% Copay"]},
              "room_rent": {
                  "room_rent_limit": ["Not Applicable", "Rent up to Single Private Room", "Rent up to Twin Sharing",
                                      "Rest in General ward", "0.5% of SI max up to 2500", "1% of SI max up to 5000",
                                      "1.5% of SI max up to 7500", "2% of SI max up to 7500", "Others"],
                  "options_for_deductions": ["Proportionate Deduction", "Capping on Room Charges only"]},
              "road_ambulance": {"road_ambulance_limit": ""},
              "ayush_treatment": {"ayush_treatment_limit": ""},
              "pre_existing_disease_and_specified_disease": {
                  "pre_existing_disease_and_specified_disease_waiting_period":
                      ["Applicable", "Waived Off"]},
              "medical_advancement_surgery": {
                  "medical_advancement_surgery_limit": ["Upto 25% SI", "Upto 50% SI", "Upto SI"]}}

    return output


def output_template_unmatched(incl_headings=False):
    heading_outputs = {"maternity_expenses": {"limit_normal_delivery": "", "limit_C_Section": "",
                                              "waiting_period": ""},
                       "pre_hospitalization": {"pre_hospitalization_period": ""},
                       "post_hospitalization": {"post_hospitalization_period": ""},
                       "pre_existing_disease_and_specified_disease": {
                                    "pre_existing_disease_and_specified_disease_waiting_period": ""}}
    # these are added to the final result without the help of a llm

    output = {"day_care_treatment": {"day_care_treatment": ""},
              "organ_donor_expenses": {"organ_donor_expenses": ""},
              "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "",
                                                  "applicability": ""},
              "maternity_expenses": {"no_of_deliveries": ""},
              "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
              "corporate_buffer": {"sum_insured": "",
                                   "type_of_ailment": "",
                                   "type_of_coverage": ""},
              "refractive_error_correction_expenses": {"si_limit": "", "eye_power": ""},
              "hiv_anti_retroviral_therapy": {"hiv_anti_retroviral_therapy": ""},
              "home_nursing_benefit": {"per_week_benefit": "", "number_of_weeks": ""},
              "preventive_health_check_up": {"benefit_limit": "", "clinic_options": ""},
              "opd_expenses": {"benefit_limit": ""},
              "physiotherapy_on_opd_basis": {"benefit_limit": "",
                                             "coverage_type": ""},
              "dental_care": {"benefit_limit": ""},
              "mental_illness": {"benefit_limit": ""},
              "vision_expenses_cover": {"benefit_limit": ""},
              "obesity_control_coverage": {"obesity_control_coverage": ""},
              "co_pay": {"policy_co_payment_factor": "",
                         "co_pay_type": ""},
              "room_rent": {
                  "room_rent_limit": "",
                  "options_for_deductions": ""},
              "road_ambulance": {"road_ambulance_limit": ""},
              "ayush_treatment": {"ayush_treatment_limit": ""},
              "medical_advancement_surgery": {"medical_advancement_surgery_limit": ""}}
    if incl_headings:
        return output | heading_outputs
    return output


def output_template_excel():
    output = {"day_care_treatment": {"day_care_treatment": ""},
              "pre_hospitalization": {"pre_hospitalization_period": ""},
              "post_hospitalization": {"post_hospitalization_period": ""},
              "organ_donor_expenses": {"organ_donor_expenses": ""},
              "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "",
                                                  "applicability": ["Within Maternity", "Over & Above Maternity"]},
              "maternity_expenses": {"no_of_deliveries": "", "limit_normal_delivery": "", "limit_C_Section": "",
                                     "waiting_period": ["9 Months waiting period", "No waiting period"]},
              "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
              "corporate_buffer": {"sum_insured": "",
                                   "type_of_ailment": ["All Accidents & Illness", "For Critical Ailments only",
                                                       "For Accidents Only"],
                                   "type_of_coverage": ["Upto Per Family SI", "Upto Full Corporate Buffer SI"]},
              "refractive_error_correction_expenses": {"si_limit": "", "eye_power": ""},
              "hiv_anti_retroviral_therapy": {"hiv_anti_retroviral_therapy": ""},
              "home_nursing_benefit": {"per_week_benefit": "", "number_of_weeks": ""},
              "preventive_health_check_up": {"benefit_limit": "", "clinic_options": ["All Clinics and Hospitals",
                                                                                     "Network Clinic and Hospitals only"]},
              "opd_expenses": {"benefit_limit": ""},
              "physiotherapy_on_opd_basis": {"benefit_limit": "",
                                             "coverage_type": ["Accidental Body Injury only", "Illness only",
                                                               "Accidental Body Injury and Illness"]},
              "dental_care": {"benefit_limit": ""},
              "mental_illness": {"benefit_limit": ""},
              "vision_expenses_cover": {"benefit_limit": ""},
              "obesity_control_coverage": {"obesity_control_coverage": ""},
              "co_pay": {"co_pay_type": ["All Claims", "Non-Network Hospitals/Clinics", "Not Applicable"],
                         "policy_co_payment_factor": ["5% Copay", "10% Copay", "15% Copay", "20% Copay",
                                                      "25% Copay", "30% Copay"]},
              "room_rent": {
                  "room_rent_limit": ["Not Applicable", "Rent up to Single Private Room", "Rent up to Twin Sharing",
                                      "Rest in General ward", "0.5% of SI max up to 2500", "1% of SI max up to 5000",
                                      "1.5% of SI max up to 7500", "2% of SI max up to 7500", "Others"],
                  "options_for_deductions": ["Proportionate Deduction", "Capping on Room Charges only"]},
              "road_ambulance": {"road_ambulance_limit": ""},
              "ayush_treatment": {"ayush_treatment_limit": ""},
              "pre_existing_disease_and_specified_disease": {
                  "pre_existing_disease_and_specified_disease_waiting_period":
                      ["Applicable", "Waived Off"]},
              "medical_advancement_surgery": {
                  "medical_advancement_surgery_limit": ["Upto 25% SI", "Upto 50% SI", "Upto SI"]}}


# def output_template_unmatched(incl_headings=False):
#     output = {
#         "policy_details": {
#             "policy_number": "",
#             "policy_issue_date": "",
#             "policy_expiry_date": "",
#             "sum_insured": ""
#         },
#         "coverage_details": {
#             "pre_hospitalization_period": "",
#             "post_hospitalization_period": ""
#         },
#         "maternity_benefits": {
#             "limit_normal_delivery": "",
#             "limit_c_section": "",
#             "no_of_deliveries": "",
#             "waiting_period": "",
#             "pre_post_natal_IPD_limit": "",
#             "pre_post_natal_OPD_limit": ""
#         },
#         "room_rent": {
#             "general_limit": "",
#             "icu_limit": "",
#             "deduction_type": ""
#         },
#         "co_pay": {
#             "co_payment_percentage": "",
#             "co_payment_type": ""
#         },
#         "day_care_treatment": {"day_care_treatment": ""},
#         "organ_donor_expenses": {"organ_donor_expenses": ""},
#         "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "", "applicability": ""},
#         "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
#         "corporate_buffer": {
#             "sum_insured": "",
#             "type_of_ailment": "",
#             "type_of_coverage": ""
#         },
#         "refractive_error_correction_expenses": {"si_limit": "", "eye_power": ""},
#         "hiv_anti_retroviral_therapy": {"hiv_anti_retroviral_therapy": ""},
#         "home_nursing_benefit": {"per_week_benefit": "", "number_of_weeks": ""},
#         "preventive_health_check_up": {"benefit_limit": "", "clinic_options": ""},
#         "opd_expenses": {"benefit_limit": ""},
#         "physiotherapy_on_opd_basis": {"benefit_limit": "", "coverage_type": ""},
#         "dental_care": {"benefit_limit": ""},
#         "mental_illness": {"benefit_limit": ""},
#         "vision_expenses_cover": {"benefit_limit": ""},
#         "obesity_control_coverage": {"obesity_control_coverage": ""},
#         "road_ambulance": {"road_ambulance_limit": ""},
#         "ayush_treatment": {"ayush_treatment_limit": ""},
#         "medical_advancement_surgery": {"medical_advancement_surgery_limit": ""}
#     }
#
#     if incl_headings:
#         output["pre_existing_disease_and_specified_disease"] = {
#             "pre_existing_disease_and_specified_disease_waiting_period": ""
#         }
#     return output


def sample_json():
    sample_info = {
        "quoteNumber": "",
        # "demographyFileId": "08dbf624-784f-46cb-83c1-5fa3002ff4d9", #from API
        "channelDetail": {
            "bagic_RM_E_Code": "0",
            "bagic_RM_Name": "",
            "channelName": "DIRECT",
            "imdCode": "0",
            "imdName": "DIRECT",
            "subImdCode": "0",
            "subImdName": ""
        },
        "groupPolicyHolder": {
            "clientIndustryType": "IT and ITES",
            "organizationName": "Testing",
            "pinCode": "751021",
            "state": "Odisha",
            "city": "KHORDA",
            "otherClientIndustryType": ""
        },
        "groupDetail": {
            "groupSize": 18,
            'mandateType': "General",
            "numberOfPrimaryMembers": 10,
            "flaggingSME": "SME"
        },
        "inPatientHospitalizationTreatmentDetail": {
            "corporateBufferTotalSumInsuredLimit": 0,
            "corporateBufferOption": "0",
            "deductiblePerClaim": 0,
            "maternityExpensesWaitingPeriod": "No waiting period",
            "preExistingDiseaseWaitingPeriod": "No Waiting",
            "specifiedDiseaseWaitingPeriod": "No Waiting"
        },
        "coverageDetail": {
            "isOfferDiscount": False,
            "wellnessServices": False,
            "baseCover": "In-patient Hospitalization Treatment",
            "subPlanOption": "Customized",
            "sumInsured": 1000000
        },
        "calculatorAttribute": {
            "commission": 0,
            "premiumPayer": "GroupManager",
            "plan": "Floater",
            "zone": "Zone A",
            "subPlanMaternity": "No",
            "subPlanPED": "No",
            "roomRentLimit": "No Room rent",
            "roomRentDeduction": "Capping on Room Charges only",
            "preHospExpense": 60,
            "postHospExpense": 90,
            "medicalAdvSurgery": "Base Cover (upto 25% SI)",
            "procedureSubLimit": "Option 1",
            "coPayType": "All Claims",
            "coPayFactor": "10% Copay",
            "ambulanceLimit": 0,
            "ayushLimit": 0,
            "noOfDeliveries": 0,
            "normalDeliverySI": 0,
            "cSectionSI": 0,
            # "Commission": 0,
            # "PreHospExpense": 60,
            # "PostHospExpense": 90,
            # "AmbulanceLimit": 0,
            # "AyushLimit": 0,
            # "NoOfDeliveries": 0,
            # "NormalDeliverySI": 0,
            # "CSectionSI": 0
        },
        "isMaternitySelected": False,
        "isRoomRentSelected": False,
        "isCoPaySelected": False,
        "isDeductibleSelected": False,
        "isProcedureSubLimitSelected": False,
        "isCorporateBufferSelected": False,
        "isRoadAmbulanceSelected": False,
        "isAYUSHTreatmentSelected": False,
        "isPreExistingDiseaseSelected": False,
        "isSpecifiedDiseaseSelected": False,
        "isMedicalAdvancementSurgerySelected": False,
        "beneficiary": "Employee",
        "branchCode": "PUN001",
        "branchDescription": "Pune, Maharashtra",
        "groupCategory": "Employer-Employee",
        "policyTenure": "1 Year",
        "raterType": "Per Person ",
        "typeOfProposal": "New Business",
        "city": "Ahmedabad",
        "hasEmployeeList": False
    }
    return sample_info


def output_template_unfiltered():
    output = {"day_care_treatment": {"day_care_treatment": ""},
              "organ_donor_expenses": {"organ_donor_expenses": ""},
              "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "",
                                                  "applicability": ["Within Maternity", "Over & Above Maternity"]},
              "maternity_expenses": {"no_of_deliveries": ""},
              "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
              "corporate_buffer": {"sum_insured": "",
                                   "type_of_ailment": ["All Accidents & Illness", "For Critical Ailments only",
                                                       "For Accidents Only"],
                                   "type_of_coverage": ["Upto Per Family SI", "Upto Full Corporate Buffer SI"]},
              "refractive_error_correction_expenses": {"si_limit": "", "eye_power": ""},
              "hiv_anti_retroviral_therapy": {"hiv_anti_retroviral_therapy": ""},
              "home_nursing_benefit": {"per_week_benefit": "", "number_of_weeks": ""},
              "preventive_health_check_up": {"benefit_limit": "", "clinic_options": ["All Clinics and Hospitals",
                                                                                     "Network Clinic and Hospitals only"]},
              "opd_expenses": {"benefit_limit": ""},
              "physiotherapy_on_opd_basis": {"benefit_limit": "",
                                             "coverage_type": ["Accidental Body Injury only", "Illness only",
                                                               "Accidental Body Injury and Illness"]},
              "dental_care": {"benefit_limit": ""},
              "mental_illness": {"benefit_limit": ""},
              "vision_expenses_cover": {"benefit_limit": ""},
              "obesity_control_coverage": {"obesity_control_coverage": ""},
              "co_pay": {"co_pay_type": ["All Claims", "Non-Network Hospitals/Clinics", "Not Applicable"],
                         "policy_co_payment_factor": ["5% Copay", "10% Copay", "15% Copay", "20% Copay",
                                                      "25% Copay", "30% Copay"]},
              "room_rent": {
                  "room_rent_limit": ["Not Applicable", "Rent up to Single Private Room", "Rent up to Twin Sharing",
                                      "Rest in General ward", "0.5% of SI max up to 2500", "1% of SI max up to 5000",
                                      "1.5% of SI max up to 7500", "2% of SI max up to 7500", "Others"],
                  "options_for_deductions": ["Proportionate Deduction", "Capping on Room Charges only"]},
              "road_ambulance": {"road_ambulance_limit": ""},
              "ayush_treatment": {"ayush_treatment_limit": ""},
              "pre_existing_disease_and_specified_disease": {
                  "pre_existing_disease_and_specified_disease_waiting_period":
                      ["Applicable", "Waived Off"]},
              "medical_advancement_surgery": {
                  "medical_advancement_surgery_limit": ["Upto 25% SI", "Upto 50% SI", "Upto SI"]},
              "initial_waiting_period": {"waiting_period": ["Waived off", "15 Days", "30 Days"]},
              "domiciliary_hospitalization": {"limit_amount": ""},
              "specific_ailment": {"ailment": [], "limit_amount": "", "limit_percentage": ""},
              "infections_cover": {"type_of_infection": ["All Infections", "Vector Borne Diseases",
                                                         "Any Single Pre-Agreed Infection"]},
              "surgery_cover": {"sum_insured": ""},
              "air_ambulance": {"si_limit": ""},
              "critical_illness_multiplier": {"plan": ["Plan A", "Plan B"],
                                              "multiplier": ["One and Half times", "Two times", "Three times"]},
              "accident_multiplier": {"accident_multiplier": ["One and Half times", "Two times", "Three times"]},
              "vaccination_cover": {"age_options": ["New born baby upto 180 days from date of birth",
                                                    "Age up to one Year", "Age up to 5 Year"],
                                    "waiting_period": ["No Waiting", "9 months waiting", "12 months", "24 months",
                                                       "36 months"]},
              "non_medical_expenses_cover": {"non_medical_expenses_cover": ["1% of SI", "2% of SI", "5% of SI",
                                                                            "10% of SI", "15% of SI", "20% of SI",
                                                                            "25% of SI", "50% of SI", "Upto SI"]},
              "external_congenital_anomalies": {"sum_insured": "", "waiting_period": ""},
              "rehabilitation_expense_cover": {"si_limit": ""},
              "gender_reassignment_treatment": {"si_limit": ""},
              "prescribed_external_medical_aid": {"si_limit": ""},
              "compassionate_visit": {"si_limit": ""},
              "sum_insured_reinstatement": {"number_of_reinstatements": ["Once", "Twice", "Unlimited"]},
              "recharge_benefits": {"recharge": ["10% SI not exceeding 50,000", "20% SI not exceeding 1,00,000",
                                                 "25% SI not exceeding 2,00,000", "50% SI not exceeding 5,00,000"]},
              "international_cover": {"internation_cover_emergency_only": ["Applicable", "Not applicable"]},
              "neurodevelopment_disorder_benefit": {"benefit_limit": ""},
              "disability_benefit_cover": {"coverage_type": ["Accidental Body Injury only", "Illness only",
                                                             "Accidental Body Injury and Illness"],
                                           "sum_insured": "", "number_of_weeks": ""},
              "wellness_services": {"health_risk_assessment": [], "electronic_health_records": [],
                                    "kid_vaccination_tracker": [], "tele_consultation": [], "e_second_opinion": [],
                                    "health_services": [], "work_life_balance_programs": [],
                                    "bagic_wellness_offering": [], "bagic_wellness_offering_family_definition": []},
              "wellbeing_benefits": {"wellbeing_benefits": ["Basic Plan", "advanced Plan"]},
              "animal_or_insect_bite_cover": {"animal_or_insect_bite_cover": ""},
              "implant_cover": {"implant_cover": ""},
              "consumable_cover": {"consumable_cover": ""},
              "medicine_cover": {"medicine_cover": ""},
              "continual_treatment": {"continual_treatment": ""},
              "specific_diagnostics_cover": {"specific_diagnostics_cover": ""},
              "ambulatory_care": {"ambulatory_care": ""},
              "catastrophic_events": {"catastrophic_events": ""},
              "isolation_care_type": {"isolation_care_type": ""},
              "palliative_care": {"palliative_care": ""},
              "elderly_care_coverage": {"elderly_care_coverage": ""},
              "funeral_expenses": {"funeral_expenses": ""},
              "lifestyle_modification": {"lifestyle_modification": ""},
              "non_intimation_co_payments": {"non_intimation_co_payments": ""},
              "delayed_submission_of_claim": {"delayed_submission_of_claim": ""},
              "delay_intimation_co_payments": {"delay_intimation_co_payments": ""},
              "waiver_of_documents": {"waiver_of_documents": ""},
              "omission_to_ensure": {"omission_to_ensure": ""},
              "cancer_care": {"benefit_applicability": ["Within SI", "Above SI"],
                              "initial_waiting_period": ["120 days", "180 days"]},
              "procedure_wise_sub_limit": {"procedure_wise_sub_limit": ["Option 1", "Option 2", "Option 3",
                                                                        "Option 4", "Not Applicable"]},
              "assisted_reproduction_expenses": {"waiting_period": ["36 Months", "24 Months",
                                                                    "12 Months", "No Waiting"],
                                                 "sum_insured": ""},
              "waiver_of_cataract_sublimit": {"waiver_of_cataract_sublimit": ["Applicable", "Not Applicable"]},
              "deductible_per_claim": {"deductible_per_claim": [1000, 2000, 3000, 4000, 5000, 10000]}}

    return output


def excel_merge(file_bytes_list, output_file):
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for file_bytes in file_bytes_list:
            data = pd.read_excel(BytesIO(file_bytes), sheet_name=None)
            for sheet_name, sheet_df in data.items():
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)


def replace_string(value):
    if isinstance(value, str):  # Ensure value is a string
        if 'employee' in value.lower():
            return 'Self'
    return value


def json_checker(json_obj):
    int_keys = ['normal_delivery_sum_insured', 'c_section_sum_insured', 'ambulance_limit', 'ayush_limit']
    for key in int_keys:
        value = json_obj.get(key)
        if value is not None and not isinstance(value, int):
            try:
                json_obj[key] = int(value)
            except (ValueError, TypeError):
                json_obj[key] = 0
    return json_obj


def match_check(json_obj):
    status = True
    prompt_str = ""
    type_list = ['IT and ITES', 'Manufacturing', 'Aviation', 'Media and Entertainment', 'Pharmaceuticals',
                 'Real Estate', 'Hospitality', 'Healthcare and hospitals', 'Education and Training', 'Insurance',
                 'Bank', 'NBFC', 'Other Financial Institution', 'NGO / Trust', 'Association', 'Society', 'SHG',
                 'Club', 'Military / Para Military force', 'Police Force', 'Law Enforcement agencies',
                 'Political Party / Firms', 'Grocery /Kirana Stores', 'Gymkhanas', 'Religious Group',
                 'Any kind of Shops', 'Event Management Companies / Teams', 'Mining industry',
                 'Sea-voyage Carriers', 'Film Industry', 'Adventure sport organizations', 'Tourism Industry',
                 'Agriculture Industry', 'Logistics and Transportation', 'Others']
    if json_obj['type_of_industry'] not in type_list:
        prompt_str += f"""{{"type_of_industry": {json_obj['type_of_industry']}}}\n"""
        prompt_str += f"{type_list}\n---\n"
        status = False

    proposal_list = ['Fresh', 'Renewal', 'Roll-over']
    if json_obj['proposal_type'] not in proposal_list:
        prompt_str += f"""{{"proposal_type": {json_obj['proposal_type']}}}\n"""
        prompt_str += f"{proposal_list}\n---\n"
        status = False

    maternity_list = ['No period', '9 month', 'No info provided']
    if json_obj['maternity_waiting_period'] not in maternity_list:
        prompt_str += f"""{{"maternity_waiting_period": {json_obj['maternity_waiting_period']}}}\n"""
        prompt_str += f"{maternity_list}\n---\n"
        status = False

    pre_existing_list = ['No period', 'Applicable period', 'No info provided']
    if json_obj['pre_existing_disease_waiting_period'] not in pre_existing_list:
        prompt_str += f"""{{"pre_existing_disease_waiting_period": {json_obj['pre_existing_disease_waiting_period']}}}\n"""
        prompt_str += f"{pre_existing_list}\n---\n"
        status = False

    specific_list = ['No period', 'Applicable period', 'No info provided']
    if json_obj['specific_disease_waiting_period'] not in specific_list:
        prompt_str += f"""{{"specific_disease_waiting_period": {json_obj['specific_disease_waiting_period']}}}\n"""
        prompt_str += f"{specific_list}\n---\n"
        status = False

    rent_list = ['Actual Rent', 'Rent up to a single private room', 'Rent up to twin sharing', 'Rest in general ward',
                 '0.5% of SI max up to 2500', '1% of SI max up to 5000', '1.5% of SI max up to 7500', '2% of SI max up to 7500', 'No info provided']
    if json_obj['room_rent_limit'] not in rent_list:
        prompt_str += f"""{{"room_rent_limit": {json_obj['room_rent_limit']}}}\n"""
        prompt_str += f"{rent_list}\n---\n"
        status = False

    deduction_list = ['Capping on Room Charges only', 'Proportionate Deduction', 'No info provided']
    if json_obj['room_rent_deduction'] not in deduction_list:
        prompt_str += f"""{{"room_rent_deduction": {json_obj['room_rent_deduction']}}}\n"""
        prompt_str += f"{deduction_list}\n---\n"
        status = False

    prehosp_list = [0, 15, 30, 60, 90, 120, 'No info provided']
    if json_obj['prehosp_period'] not in prehosp_list:
        prompt_str += f"""{{"prehosp_period": {json_obj['prehosp_period']}}}\n"""
        prompt_str += f"{prehosp_list}\n---\n"
        status = False

    posthosp_list = [0, 30, 60, 90, 120, 180, 'No info provided']
    if json_obj['posthosp_period'] not in posthosp_list:
        prompt_str += f"""{{"posthosp_period": {json_obj['posthosp_period']}}}\n"""
        prompt_str += f"{posthosp_list}\n---\n"
        status = False

    med_adv_list = ['Upto 25% SI', 'Upto 50% SI', 'Upto SI', 'No info provided']
    if json_obj['med_advancement_surgery_limit'] not in med_adv_list:
        prompt_str += f"""{{"med_advancement_surgery_limit": {json_obj['med_advancement_surgery_limit']}}}\n"""
        prompt_str += f"{med_adv_list}\n---\n"
        status = False

    co_pay_type_list = ['All Claims', 'Non-Network Hospitals/ Clinics', 'Pre-agreed disease/ procedure', 'No info provided']
    if json_obj['copay_type'] not in co_pay_type_list:
        prompt_str += f"""{{"copay_type": {json_obj['copay_type']}}}\n"""
        prompt_str += f"{co_pay_type_list}\n---\n"
        status = False

    co_pay_factor_list = ['5% Copay', '10% Copay', '15% Copay', '20% Copay', '25% Copay', '30% Copay', 'No info provided']
    if json_obj['copay_factor'] not in co_pay_factor_list:
        prompt_str += f"""{{"copay_factor": {json_obj['copay_factor']}}}\n"""
        prompt_str += f"{co_pay_factor_list}\n---\n"
        status = False

    deliveries_list = [1, 2, 3, 'No info provided']
    if json_obj['number_of_deliveries'] not in deliveries_list:
        prompt_str += f"""{{"number_of_deliveries": {json_obj['number_of_deliveries']}}}\n"""
        prompt_str += f"{deliveries_list}\n---\n"
        status = False

    plan_list = ['Floater', 'Individual or Non-Floater']
    if json_obj['plan_type'] not in plan_list:
        prompt_str += f"""{{"plan_type": {json_obj['plan_type']}}}\n"""
        prompt_str += f"{plan_list}\n---\n"
        status = False

    return status, prompt_str


def rec_modifier(output: dict):
    for key, value in output.items():
        if isinstance(value, dict):
            rec_modifier(value)
        elif isinstance(value, list):
            # if value:
            output[key] = " ".join(map(str, value))


def remove_days(period):
    return period.lower().replace("days", "").strip() if isinstance(period, str) else period


def remove_plusminus(period):
    return period.lower().replace("+/-", "").strip() if isinstance(period, str) else period


def text_space_cleaner(text):
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n', ' ', text)
    return text

def reliance_output_template():
    """Template for Reliance insurance policy output"""
    return {
        "policy_details": {
            "policy_number": "",
            "policy_issue_date": "",
            "date_of_proposal": "",
            "date_of_expiry": ""
        },
        "premium_details": {
            "cgst": "",
            "sgst": "",
            "total_premium": ""
        },
        "coverage_details": {
            "pre_hospitalization": "",
            "post_hospitalization": "",
            "maternity_cover": "",
            "room_rent": ""
        }
    }
def output_template_excel():
    return {
        "policy_details": {
            "policy_number": "",
            "policy_issue_date": "",
            "date_of_proposal": "",
            "date_of_expiry": ""
        },
        "coverage_details": {
            "pre_hospitalization": "",
            "post_hospitalization": ""
        },
        "maternity_benefits": {
            "no_of_deliveries": "",
            "limit_normal_delivery": "",
            "limit_C_Section": "",
            "waiting_period": ""
        },
        "room_rent": {
            "room_rent_limit": "",
            "options_for_deductions": ""
        },
        "co_pay": {
            "co_pay_type": "",
            "policy_co_payment_factor": ""
        }
    }
