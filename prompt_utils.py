from utils import get_completion_from_messages, output_template, output_template_unmatched, output_template_unfiltered, \
    output_template_excel, get_completion_qwen, get_completion_schema
import re
import json
from typing import Dict, List
from fastapi import HTTPException
from output_schema import Output, OutputFull

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='.env')
api_key = os.getenv("OPENAI_API_KEY")

from openai import OpenAI
client = OpenAI(api_key=api_key)


def prompt_field(data, maternity_expense, room_restrictions):
    template = output_template()

    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text. The user will provide you with text which is scraped from an insurance \
            policy document by Bajaj. Your \
            task is to extract relevant fields and output them in the form of a JSON. The output should just be the json \
            with no prefix or suffix, and the format of the output should be \n
            --- 
            {template}
            ---
            Your task is to find the appropriate values for the keys in the dictionary, which are left as either empty \
            python strings or python lists. In the instances when the dict value is originally a list, you should set the \
            value to an element of this list, that has the closest match. If the data corresponding to the value of a key \
            is not present in the document, \
            set the value to an empty string or an empty list, depending on if originally the value was an empty string \
            or a list respectively. \

            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.

            Keep the following things in mind, for different fields in the output:

            1. All values related to Corporate Buffer must be taken from the corresponding section, if this section
            is missing from the data, then do not fill in the values for corporate_buffer['sum_insured']. If present, the \
            type_of_ailment and type_of_coverage may also mentioned in this section.

            2. All values related to pre and post_natal_expenses_IPD and pre_and_post_natal_expenses_OPD must be taken \
            from the pre and post natal section or other conditions section of the data. The applicability may also be \
            mentioned here. The max liability on maternity expenses is {maternity_expense}. If OPD is not covered \
            set expense_limit_OPD to an empty string.

            3. Surgery limit for medical_advancement_surgery may be mentioned as Modern Treatment Methods and Advancement \
            in Technologies under Other Conditions

            4. For home nursing benefit, keep in mind to convert allowance amount to per week (times 7) if given as per day and \
            to convert duration to number of weeks (divided by 7, return nearest integer) if given in number of days

            5. refractive_error_correction_expenses are mentioned under Other Conditions (sometimes under pre and post \
            natal) and may sometimes be labeled as lasik

            6. Room Restrictions: {room_restrictions}
            If there are no room restrictions, set options_for_deductions as an empty list.

            7. Do not confuse other sub limits for OPD limit

            8. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa \
            and Homoeopathy

            9. If there is no mention of co_pay or any of its sub keys, set them to empty lists

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template.
            '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {data}'
        }
    ]
    response = get_completion_from_messages(messages)
    return response


def prompt_field_unmatched_policy(data, maternity_expense, room_restrictions):
    template = output_template_unmatched()
    # if "refer claim condition" not in room_restrictions.lower():
    if len(room_restrictions) > 2:
        room_restrictions = f"Use this information to answer: {room_restrictions}"
    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text. The user will provide you with text which is scraped from an insurance \
            policy document by Bajaj. Your \
            task is to extract relevant fields and output them in the form of a JSON. The output should just be the json \
            with no prefix or suffix, and the format of the output should be \n
            --- 
            {template}
            ---
            Your task is to find the appropriate values for the keys in the dictionary, which are left as empty \
            python strings. If the data corresponding to the value of a key \
            is not present in the document, \
            set the value to an empty string. Do not delete any keys, add new keys or change the structure of the output.

            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.

            Keep the following things in mind, for different fields in the output:

            1. All values related to Corporate Buffer must be taken from the corresponding section, if this section
            is missing from the data, then do not fill in the values for corporate_buffer['sum_insured']. If present, the \
            type_of_ailment and type_of_coverage may also mentioned in this section.

            2. All values related to pre and post_natal_expenses_IPD and pre_and_post_natal_expenses_OPD must be taken \
            from the pre and post natal section or other conditions section of the data. The applicability may also be \
            mentioned here. The max liability on maternity expenses is {maternity_expense}. If OPD is not covered \
            set expense_limit_OPD to an empty string.

            3. Surgery limit for medical_advancement_surgery may be mentioned as Modern Treatment Methods and Advancement \
            in Technologies under Other Conditions or for Cyberknife treatment, Stem Cell Transplantation, Cochlear Implant

            4. For home nursing benefit, keep in mind to convert allowance amount to per week (times 7) if given as per day and \
            to convert duration to number of weeks (divided by 7, return nearest integer) if given in number of days

            5. refractive_error_correction_expenses are mentioned under Other Conditions (sometimes under pre and post \
            natal) and may sometimes be labeled as lasik. If present, eye_power may be mentioned in dioptres 

            6. Room Restrictions: {room_restrictions}. If asked to refer to claim condition, they will be under \
            Room Rent Restriction. room_rent_limit may be in the form of a number or a percentage of SI, if it is\
            different for general, and ICU, mention the entire condition under room_rent_limit. 
            While filling options_for_deductions \
            as 'Proportionate Deduction', 'Capping on Room Charges only', only consider the normal case, do not consider \
            the case for ICU hospitalization or cases where there is no \
            differential billing. Do not confuse with Ambulance limit.

            7. Do not confuse other sub limits for OPD limit

            8. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa \
            and Homoeopathy

            9. Under co_pay, policy_co_payment_factor may be mentioned as a percentage, and can include conditions, so output the \
            appropriate value under this key. Whereas co_pay_type \
            refers to types of claims and hospitals

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template.

            '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {data}'
        }
    ]
    # print(data)
    response = get_completion_from_messages(messages)
    json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
    return json_str


def prompt_field_magma(data, template):
    # if "refer claim condition" not in room_restrictions.lower():

    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text. The user will provide you with text which is scraped from an insurance \
            policy document by Magma HDI, in the form of a JSON. Your \
            task is to extract relevant fields and output them in the form of a JSON. The output should just be the json \
            with no prefix or suffix, and the format of the output should be \n
            --- 
            {template}
            ---
            Your task is to find the appropriate values for the keys in the dictionary, which are left as empty \
            python strings. If the data corresponding to the value of a key \
            is not present in the document, \
            set the value to an empty string. Do not delete any keys, add new keys or change the structure of the output.

            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.

            Keep the following things in mind, for different fields in the output:

            1. All values related to Corporate Buffer must be taken from the corresponding section (mostly Corporate \
            Floater), if this section \
            is missing from the data, then do not fill in the values for corporate_buffer['sum_insured']. If present, the \
            type_of_ailment and type_of_coverage may also mentioned in this section.
            
            2. "vision_expenses_cover" for cataract may be present under Disease Wise Sublimits
            
            3. Surgery limit for medical_advancement_surgery may be mentioned as Modern Treatment Methods and Advancement \
            in Technologies under Other Conditions or for Cyberknife treatment, Stem Cell Transplantation, Cochlear Implant
            
            4. "mental_illness" may be present under Special Condition as Psychiatric ailments 
            
            5. refractive_error_correction_expenses are mentioned under Special Condition \
            and may sometimes be labeled as lasik. If present, eye_power may be mentioned 

            6. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa \
            and Homoeopathy, or as non Allopathic medicine

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template.

            '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {data}'
        }
    ]
    # print(data)
    response = get_completion_from_messages(messages)
    json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
    return json_str


def prompt_field_unmatched_policy_new(data, maternity_expense, room_restrictions, insurer="reliance"):
    # from utils import output_template_unmatched
    # import re
    # from openai_helper import get_completion_from_messages
 # change this if needed

    template = output_template_unmatched()

    if len(room_restrictions) > 2:
        room_restrictions = f"Use this information to answer: {room_restrictions}"

    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific 
data fields from unstructured text. The user will provide you with text scraped from an insurance policy document by {insurer.title()}.

Your task is to find the appropriate values for the keys in the dictionary, which are left as empty python strings.
If the data corresponding to the value of a key is not present in the document, set the value to an empty string.

! Do not:
- Delete any keys
- Add new keys
- Change the structure of the output

Only return the JSON. No commentary or markdown. Use this schema:
---
{template}
---

Guidelines:

1. **Sum Insured / Limits / Numbers**: Only give the number. Do not confirm or deny coverage. If not mentioned, leave empty.

2. **Pre/Post Hospitalization Periods**: 
   - Should be in number of days.
   - May appear in a paragraph or table.

3. **Maternity Benefits**: 
   - limit_normal_delivery and limit_c_section may appear in tables or sentences.
   - waiting_period might say “9 months waiting period” or “No waiting period”.
   - Use this fallback if needed: {maternity_expense}
   - If OPD is not covered, leave OPD limit as an empty string.

4. **Room Rent**: 
   - {room_restrictions}
   - ICU and general limits might be separate.
   - Deduction type may say "Proportionate Deduction", etc.

5. **Co-Pay**:
   - co_payment_percentage is usually a percentage value like “10%”.
   - co_payment_type might mention claim or hospital type like "non-network hospitals".

Do not guess. Extract only what is present in the document.
'''
        },
        {
            'role': 'user',
            'content': f'Policy Document:\n{data}'
        }
    ]

    response = get_completion_from_messages(messages)
    json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
    return json_str



def prompt_field_unmatched_policy_schema(data, maternity_expense, room_restrictions):
    if len(room_restrictions) > 2:
        room_restrictions = f"Use this information to answer: {room_restrictions}"
    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text. The user will provide you with text which is scraped from an insurance \
            policy document by Bajaj. Your \
            task is to extract relevant fields and output them in the form of a JSON. \
            If the data corresponding to the value of a key \
            is not present in the document, set the value to an empty string. 
            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.

            Keep the following things in mind, for different fields in the output:

            1. The max liability on maternity expenses is {maternity_expense}. If OPD is not covered \
            set expense_limit_OPD to an empty string.

            2. Room Restrictions: {room_restrictions}. 
            Do not confuse with Ambulance limit.

            3. Do not confuse other sub limits for OPD limit

            Do not make guesses, only take data from the document from the \
            relevant sections.
            '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {data}'
        }
    ]
    response = get_completion_schema(messages, Output)
    return response


def prompt_field_unmatched_rfq(rfq_text):
    template = output_template_unmatched(incl_headings=True)
    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text. The user will provide you with text which is scraped from an insurance \
            RFQ document. Your \
            task is to extract relevant fields and output them in the form of a JSON. The output should just be the json \
            with no prefix or suffix, and the format of the output should be \n
            --- 
            {template}
            ---
            Your task is to find the appropriate values for the keys in the dictionary, which are left as empty \
            python strings. If the data corresponding to the value of a key \
            is not present in the document, \
            set the value to an empty string. Do not delete any keys, add new keys or change the structure of the output.

            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.
            
            Include all details present in the document that pertain to the keys in the template. Be descriptive if \
            needed based on the conditions in the document.

            Keep the following things in mind, for different fields in the output:

            1. Do not confuse between overall sum insured and the sub limit for different categories. Do no mix up limits \
            between different categories.

            2. medical_advancement_surgery refers to Cyberknife treatment, Stem Cell Transplantation, Cochlear Implant, \
            and could be given as a percentage. Do not confuse this with co_pay

            3. For home nursing benefit, keep in mind to convert allowance amount to per week (times 7) if given as per day and \
            to convert duration to number of weeks (divided by 7, return nearest integer) if given in number of days

            4. Do not confuse other sub limits for OPD limit

            5. ayush_treatment_limit under ayush_treatment may be present as a number or as a percentage/factor of SI (including up to SI). \
            The value may be present as AYUSH Treatment. AYUSH refers to Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa and Homoeopathy
            Do not convert from percentage SI to a number
            
            6. If room_rent_limit (might be mentioned as value or percentage SI) is present, options_for_deductions might also be present in the same or adjacent sections. \
            If mentioned up to SI, mention that instead of value, and include conditions if any
            
            7. Under co_pay, policy_co_payment_factor may be mentioned as a percentage, and can include conditions, so output the \
            appropriate value under this key. Whereas co_pay_type \
            refers to types of claims and hospitals

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template. Do not delete or add any keys from the template in the output, \
            Keep the structure of the output same as the template, do not modify the keys.
            '''
        },
        {
            'role': 'user',
            'content': f'RFQ Document: \n {rfq_text}'
        }
    ]
    response = get_completion_from_messages(messages)
    json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
    return json_str


def get_extraction_guidance() -> Dict[str, Dict[str, str]]:
    """Returns field-level extraction instructions"""
    return {
        "policy_details": {
            "policy_number": "Look for 'Policy No:' followed by alphanumeric code",
            "dates": "Find dates in DD-MM-YYYY format after labels like 'Issue Date'"
        },
        "premium_details": {
            "total_premium": "Locate amount after 'Total Premium' (₹ symbol optional)",
            "taxes": "Find CGST/SGST values near premium amounts"
        }
    }


def get_validation_rules() -> Dict[str, List[str]]:
    """Returns validation regex patterns for each field"""
    return {
        "policy_number": [r"^[A-Z]{2,3}-\d{6,8}$", "Invalid policy number format"],
        "dates": [r"^\d{2}-\d{2}-\d{4}$", "Date must be DD-MM-YYYY"],
        "currency": [r"^₹?\d{1,3}(,\d{3})*(\.\d{2})?$", "Invalid currency format"]
    }


# [Rest of the functions remain unchanged...]

def prompt_field_unmatched_rfq_schema(rfq_text):
    # template = output_template_unmatched(incl_headings=True)
    # output = OutputFull()
    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text. The user will provide you with text which is scraped from an insurance \
            RFQ document. Your \
            task is to extract relevant fields and output them in the form of a JSON. \
            If the data corresponding to the value of a key is not present in the document, \
            set the value to an empty string. Do not delete any keys, add new keys or change the structure of the output.

            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.

            Include all details present in the document that pertain to the keys in the template. Be descriptive if \
            needed based on the conditions in the document.

            Keep the following things in mind, for different fields in the output:

            1. Do not confuse between overall sum insured and the sub limit for different categories. Do no mix up limits \
            between different categories.

            2. medical_advancement_surgery refers to Cyberknife treatment, Stem Cell Transplantation, Cochlear Implant, \
            and could be given as a percentage. Do not confuse this with co_pay

            3. For home nursing benefit, keep in mind to convert allowance amount to per week (times 7) if given as per day and \
            to convert duration to number of weeks (divided by 7, return nearest integer) if given in number of days

            4. Do not confuse other sub limits for OPD limit

            5. ayush_treatment_limit under ayush_treatment may be present as a number or as a percentage/factor of SI (including up to SI). \
            The value may be present as AYUSH Treatment. AYUSH refers to Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa and Homoeopathy
            Do not convert from percentage SI to a number

            6. If room_rent_limit (might be mentioned as value or percentage SI) is present, options_for_deductions might also be present in the same or adjacent sections. \
            If mentioned up to SI, mention that instead of value, and include conditions if any

            7. Under co_pay, policy_co_payment_factor may be mentioned as a percentage, and can include conditions, so output the \
            appropriate value under this key. Whereas co_pay_type \
            refers to types of claims and hospitals

            Do not make guesses, only take data from the document from the \
            relevant sections.
            '''
        },
        {
            'role': 'user',
            'content': f'RFQ Document: \n {rfq_text}'
        }
    ]
    response = get_completion_schema(messages, OutputFull)
    return response


def prompt_field_matched_rfq(df):
    # print(mail)
    # print(len(df))
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

    messages = [
        {
            'role': 'system',
            'content': '''
    You are an AI json generator. You will be provided with data from a table, for creating the said \
    json. Your responses should \
    only contain information in the json format. \
    No need to print the json wrapper, only print the content of the json file, i.e. do not include \
    the '```json' tag in your replies. 
    '''
        },
        {
            'role': 'user',
            'content': f'''Given the information transcribed from a Group Mediclaim policy (or GMC) schedule, \
    your task is to identify relevant information. The information is provided in the form of an email and a table. \


    Use the \
    information provided in the following table, delimited by triple backticks to perform the upcoming task:
    ```{df}```

    You must identify the following information from the above data. If you cannot find relevant information, \
    just reply 'null': 
    1. Name of the company/institution to be insured
    2. City of the company/institution to be insured
    3. State of the company/institution to be insured
    4. PIN Code of the company/institution to be insured
    5. Normal Delivery Sum Insured (this should be a number)
    6. C-Section Delivery Sum Insured (this should be a number)
    7. Ambulance limit (this should be a number)
    8. AYUSH treatment limit (this should be a number)

    Then, identify the following information from the above data. You will be provided a list of possible responses for each field, \
    from which you should pick the closest fitting response, or 'null' if the information is not present. Please ensure that \
    your response for each field is always from the list provided to you:
    1. Type of industry/company: ['IT and ITES', 'Manufacturing', 'Aviation', 'Media and Entertainment', 'Pharmaceuticals', 'Real Estate', 'Hospitality', 'Healthcare and hospitals', 'Education and Training', 'Insurance', 'Bank', 'NBFC', 'Other Financial Institution', 'NGO / Trust', 'Association', 'Society', 'SHG', 'Club', 'Military / Para Military force', 'Police Force', 'Law Enforcement agencies', 'Political Party / Firms', 'Grocery /Kirana Stores', 'Gymkhanas', 'Religious Group', 'Any kind of Shops', 'Event Management Companies / Teams', 'Mining industry', 'Sea-voyage Carriers', 'Film Industry', 'Adventure sport organizations', 'Tourism Industry', 'Agriculture Industry', 'Logistics and Transportation', 'Others', 'No info provided']
    2. Type of proposal: ['Fresh', 'Renewal', 'Roll-over']
    3. Maternity waiting period: ['No period', '9 month', 'No info provided']
    4. Pre-existing disease (PED) waiting period: ['No period', 'Applicable period', 'No info provided']
    5. Specific disease waiting period: ['No period', 'Applicable period', 'No info provided']
    6. Room Rent limit: ['Actual Rent', 'Rent up to a single private room', 'Rent up to twin sharing', 'Rest in general ward', '0.5% of SI max up to 2500', '1% of SI max up to 5000', '1.5% of SI max up to 7500', '2% of SI max up to 7500', 'No info provided']
    7. Room Rent deduction: ['Capping on Room Charges only', 'Proportionate Deduction', 'No info provided']
    8. Pre-hospitalization period: [0, 15, 30, 60, 90, 120, 'No info provided']
    9. Post-hospitalization period: [0, 30, 60, 90, 120, 180, 'No info provided']
    10. Medical advancement surgery limit: ['Upto 25% SI', 'Upto 50% SI', 'Upto SI', 'No info provided']
    11. Co-pay type: ['All Claims', 'Non-Network Hospitals/ Clinics', 'Pre-agreed disease/ procedure', 'No info provided']
    12. Co-pay factor: ['5% Copay', '10% Copay', '15% Copay', '20% Copay', '25% Copay', '30% Copay', 'No info provided']
    13. Number of Deliveries: [1, 2, 3, 'No info provided']
    14. Plan type: ['Floater', 'Individual or Non-Floater']

    Also identify any other information about additional coverages which isn't already encompassed by the \
    above parameters.

    Format your reply as a python dict which has keys 'name', 'city', 'state', 'pin', \
    'normal delivery sum insured', 'c-section sum insured', 'ambulance limit', 'ayush limit', 'type of industry', 'proposal type', \
    'maternity waiting period', 'pre-existing disease waiting period', 'specific disease waiting period', 'room rent limit', 
    'room rent deduction', 'prehosp period', 'posthosp period', 'med advancement surgery limit', \
    'copay type', 'copay factor', 'number of deliveries' ,'plan type' and 'additional coverages'.
    '''
        },
    ]

    response = get_completion_from_messages(messages)
    d = json.loads(response)
    with open("results/llm_response.json", 'w') as f:
        json.dump(d, f, indent=4)

    other = None
    if 'additional coverages' in list(d.keys()) and d['additional coverages']:
        other = d['additional coverages']
    type_list = ['IT and ITES', 'Manufacturing', 'Aviation', 'Media and Entertainment', 'Pharmaceuticals',
                 'Real Estate', 'Hospitality', 'Healthcare and hospitals', 'Education and Training', 'Insurance',
                 'Bank', 'NBFC', 'Other Financial Institution', 'NGO / Trust', 'Association', 'Society', 'SHG',
                 'Club', 'Military / Para Military force', 'Police Force', 'Law Enforcement agencies',
                 'Political Party / Firms', 'Grocery /Kirana Stores', 'Gymkhanas', 'Religious Group',
                 'Any kind of Shops', 'Event Management Companies / Teams', 'Mining industry',
                 'Sea-voyage Carriers', 'Film Industry', 'Adventure sport organizations', 'Tourism Industry',
                 'Agriculture Industry', 'Logistics and Transportation', 'Others']
    proposal_dict = {'Fresh': 'New Business', 'Renewal': 'Own Renewal', 'Roll-over': 'Roll Over'}

    # FOR THE FOLLOWING ASSIGNMENTS, THE else CLAUSE HAS TO BE CHANGED BACK TO NONE.

    sample_info['groupPolicyHolder']['clientIndustryType'] = d['type of industry'] if \
        d['type of industry'] in type_list else 'Others'
    if d['name'] is not None and d['name'] != 'null':
        sample_info['groupPolicyHolder']['organizationName'] = d['name']
    else:
        print('Mandatory field, Organization name, not found in given information.')
    if d['pin'] is not None and d['pin'] != 'null':
        sample_info['groupPolicyHolder']['pinCode'] = d['pin']
    else:
        print('Mandatory field, PIN Code, not found in given information.')
    sample_info['groupPolicyHolder']['state'] = d['state'] if d['state'] is not None and d[
        'state'] != 'null' else 'No State'
    sample_info['groupPolicyHolder']['city'] = d['city'] if d['city'] is not None and d[
        'city'] != 'null' else 'No City'

    # sample_info['groupDetail']['groupSize'] = d['group size'] if d['group size'] is not None and d[
    #     'group size'] != 'null' \
    #     else 0
    # sample_info["groupDetail"]["numberOfPrimaryMembers"] = d['number of primary members'] \
    #     if d['number of primary members'] is not None and d['number of primary members'] != 'null' else 0
    sample_info["inPatientHospitalizationTreatmentDetail"]["maternityExpensesWaitingPeriod"] = d[
        'maternity waiting period'] if d['maternity waiting period'] in ['No period',
                                                                         '9 month'] else "No waiting period"
    sample_info["inPatientHospitalizationTreatmentDetail"]["preExistingDiseaseWaitingPeriod"] = d[
        'pre-existing disease waiting period'] if d['pre-existing disease waiting period'] in \
                                                  ['No period', 'Applicable period'] else "No Waiting"
    sample_info["inPatientHospitalizationTreatmentDetail"]["specifiedDiseaseWaitingPeriod"] = d[
        'specific disease waiting period'] if d['specific disease waiting period'] in ['No period',
                                                                                       'Applicable period'] \
        else "No Waiting"

    sample_info["calculatorAttribute"]["roomRentLimit"] = d['room rent limit'] if d['room rent limit'] in [
        'Actual Rent', 'Rent up to a single private room', 'Rent up to twin sharing', 'Rest in general ward',
        '0.5% of SI max up to 2500', '1% of SI max up to 5000', '1.5% of SI max up to 7500',
        '2% of SI max up to 7500'] else 'No Room rent'
    sample_info["calculatorAttribute"]["roomRentDeduction"] = d['room rent deduction'] if d['room rent deduction'] \
                                                                                          in [
                                                                                              'Capping on Room Charges only',
                                                                                              'Proportionate Deduction'] else 'Capping on Room Charges only'
    sample_info["calculatorAttribute"]["preHospExpense"] = d['prehosp period'] if d['prehosp period'] in [0, 15, 30,
                                                                                                          60, 90,
                                                                                                          120] else 60
    sample_info["calculatorAttribute"]["postHospExpense"] = d['posthosp period'] if d['posthosp period'] in [0, 30,
                                                                                                             60, 90,
                                                                                                             120,
                                                                                                             180] else 90
    sample_info["calculatorAttribute"]["medicalAdvSurgery"] = d['med advancement surgery limit'] if d[
                                                                                                        'med advancement surgery limit'] in [
                                                                                                        'Upto 25% SI',
                                                                                                        'Upto 50% SI',
                                                                                                        'Upto SI'] else "No MedicalAdvSurgery"
    sample_info["calculatorAttribute"]["procedureSubLimit"] = "No Procedure Sub Limit"
    sample_info["calculatorAttribute"]["coPayType"] = d['copay type'] if d['copay type'] in ['All Claims',
                                                                                             'Non-Network Hospitals/ Clinics',
                                                                                             'Pre-agreed disease/ procedure'] else "No CoPay"
    sample_info["calculatorAttribute"]["coPayFactor"] = d['copay factor'] if d['copay factor'] in ['5% Copay',
                                                                                                   '10% Copay',
                                                                                                   '15% Copay',
                                                                                                   '20% Copay',
                                                                                                   '25% Copay',
                                                                                                   '30% Copay'] else "No CoPay"
    sample_info["calculatorAttribute"]["ambulanceLimit"] = d['ambulance limit'] if d['ambulance limit'] is not None \
                                                                                   and d[
                                                                                       'ambulance limit'] != 'null' else 0
    sample_info["calculatorAttribute"]["ayushLimit"] = d['ayush limit'] if d['ayush limit'] is not None and d[
        'ayush limit'] != 'null' else 0
    sample_info["calculatorAttribute"]["normalDeliverySI"] = d['normal delivery sum insured'] \
        if d['normal delivery sum insured'] is not None and d['normal delivery sum insured'] != 'null' else 0
    sample_info["calculatorAttribute"]["cSectionSI"] = d['c-section sum insured'] if d[
                                                                                         'c-section sum insured'] is not None and \
                                                                                     d[
                                                                                         'c-section sum insured'] != 'null' else 0
    sample_info["calculatorAttribute"]["noOfDeliveries"] = d['number of deliveries'] if (d['number of deliveries']
                                                                                         in [1, 2, 3]) else 0

    # sample_info["isMaternitySelected"] = False if d['number of deliveries'] is None and d['normal delivery sum insured'] is None and d['c-section sum insured'] is None and d[
    #     'maternity waiting period'] is None else True
    sample_info["isMaternitySelected"] = False if sample_info["calculatorAttribute"]["normalDeliverySI"] == 0 and \
                                                  sample_info["calculatorAttribute"]["cSectionSI"] == 0 else True
    sample_info["isRoomRentSelected"] = False if sample_info["calculatorAttribute"][
                                                     "roomRentLimit"] == "No Room rent" and \
                                                 sample_info["calculatorAttribute"][
                                                     "roomRentDeduction"] == "Capping on Room Charges only" else True
    sample_info["isCoPaySelected"] = False if sample_info["calculatorAttribute"]["coPayType"] == "No CoPay" or \
                                              sample_info["calculatorAttribute"][
                                                  "coPayFactor"] == "No CoPay" else True
    sample_info["isProcedureSubLimitSelected"] = False if sample_info["calculatorAttribute"][
                                                              "procedureSubLimit"] == "No Procedure Sub Limit" else True
    sample_info["isRoadAmbulanceSelected"] = False if sample_info["calculatorAttribute"][
                                                          "ambulanceLimit"] == 0 else True
    sample_info["isAYUSHTreatmentSelected"] = False if sample_info["calculatorAttribute"][
                                                           "ayushLimit"] == 0 else True
    sample_info["isPreExistingDiseaseSelected"] = False if sample_info["inPatientHospitalizationTreatmentDetail"][
                                                               "preExistingDiseaseWaitingPeriod"] == "No Waiting" else True
    sample_info["isSpecifiedDiseaseSelected"] = False if sample_info["inPatientHospitalizationTreatmentDetail"][
                                                             "specifiedDiseaseWaitingPeriod"] == "No Waiting" else True
    sample_info["isMedicalAdvancementSurgerySelected"] = False if sample_info["calculatorAttribute"][
                                                                      "medicalAdvSurgery"] == "No MedicalAdvSurgery" else True
    sample_info["typeOfProposal"] = proposal_dict[d['proposal type']] if d['proposal type'] in list(
        proposal_dict.keys()) else 'New Business'
    sample_info["city"] = d['city'] if d['city'] is not None and d['city'] != 'null' else 'No city'
    if d['plan type'] == 'Floater':
        sample_info['calculatorAttribute']['plan'] = 'Floater'
    elif d['plan type'] == 'Individual or Non-Floater':
        sample_info['calculatorAttribute']['plan'] = 'Individual'
    else:
        print('Proposal plan not found')
        sample_info['calculatorAttribute']['plan'] = 'Floater'
    print(json.dumps(sample_info, indent=4))
    return sample_info, other


def compare_pdf_prompt(policy_text, rfq_text):
    template = output_template_unmatched(incl_headings=True)

    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text in the field of health insurance. The user will provide you with input, \
            consisting of text scraped from a Bajaj policy document, and a insurance RFQ. These are respectively labelled \
            as "policy_document" and "rfq_document", in the JSON input. 
            
            Your task is to extract relevant fields and output them in the form of a JSON, separately for both the \
            documents. Do not mix up the documents as the data in them will be distinct. The relevant fields for \
            the output are given in the template below.
            --- 
            {template}
            ---
            The output should be a JSON with the same structure as the user input but the unstructured text replaced by \
            structured JSON given in the template above. 
            
            For the individual documents, your task is to find the appropriate values for the keys in the dictionary. \
            If the data corresponding to the value of a key \
            is not present in the respective document, set the value to an empty string.

            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.

            Keep the following things in mind, for different fields in the output:

            1. All values related to Corporate Buffer must be taken from the corresponding section, if this section
            is missing from the data, then do not fill in the values for corporate_buffer['sum_insured']. If present, the \
            type_of_ailment and type_of_coverage may also mentioned in this section.

            2. All values related to pre and post_natal_expenses_IPD and pre_and_post_natal_expenses_OPD must be taken \
            from the pre and post natal section or other conditions section of the data. If OPD is not covered \
            set expense_limit_OPD to an empty string.

            3. Surgery limit for medical_advancement_surgery may be mentioned as Modern Treatment Methods and Advancement \
            in Technologies under Other Conditions

            4. refractive_error_correction_expenses are mentioned under Other Conditions (sometimes under pre and post \
            natal) and may sometimes be labeled as lasik

            5. Do not confuse other sub limits for OPD limit

            6. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa \
            and Homoeopathy

            7. If there is no mention of co_pay or any of its sub keys, set them to empty lists
            
            8. Road ambulance should be present near road ambulance, do not confuse with total sum insured, or other \
            sub limits

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template. Do not remove any keys from the template, set teh value to an \
            empty string if it is not present in the document.
            Keep in mind that the data is distinct for policy_document and \
            rfq_document, be careful not to mix information from one for the output of the other. For policy_document use \
            user data present in the policy_document value and for rfq_document, use user data present in the rfq_document \
            value. Do NOT mix these two.
            
            Do not include any prefixes or \
            suffixes in the output, it should be a proper JSON. 
            '''
        },
        {
            'role': 'user',
            'content': f'{{"policy_document": {policy_text}, "rfq_document": {rfq_text}}}'
        }
    ]
    # print(data)
    response = get_completion_from_messages(messages)
    print(response)
    json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
    return json_str


def compare_pdf_second(policy_out, rfq_out):
    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data analyst assistant specialized in the filed of insurance policy. \
            The user will provide you with a structured JSON input, with two key value pairs, 
            
            1. "policy_document": Data extracted from a Bajaj insurance policy document.
            2. "rfq_document": Data extracted from an insurance RFQ document.
            
            Your task is to compare the policy terms, conditions and insured limits present between these two and find \
            only the differences.

            - Both of these JSONs have identical structure (keys are the same) but may differ \
            in their values. The output must also be of the same structure, do not modify or add new keys. \
            - Include only the keys where the values differ between "policy_document" and "rfq_document".
            - For each key with a difference, include a descriptive string that clearly points out the difference in the \
             values from "policy_document" and "rfq_document".
            - Exclude keys where the values are the same or similar, or equivalent based on context. 
            
            Keep the following things in mind while making the comparisons, to find differences:
            
            1. For a key, if the corresponding value is an empty string, that implies that the either the scheme is not \
            covered or the limit for the same is 0.

            2. Identify only differences that are meaningful and significant. Check if things are equivalent based on \
            their context. For example:
            - "60" and "60 days" should be treated as equivalent. 
            - 50 and 50% should be treated as equal
            - "60%" and "50%" should be treated as different.
            - "waived off", "waived for all", and "covered from day 1" are equivalent
            
            3. Only point out actual differences. Differences in grammar, writing style and phrasing should not be \
            counted.

            Do not make guesses, only compare data from corresponding sections of the documents. 
            
            The final output should be JSON, with a similar structure as both the documents. The output should contain \
            only the keys which have different values between the policy and rfq document, and this difference should \
            be the corresponding value. Other than deleting the keys, where \
            there is no difference, do not make any other modifications to the structure.
            
            Ensure that the output is of proper JSON structure and does not contain any prefixes or suffixes \
            (such as ```json).
            '''
        },
        {
            'role': 'user',
            'content': f'{{"policy_document": {policy_out}, "rfq_document": {rfq_out}}}'
        }
    ]
    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data analyst assistant specialized in the filed of insurance policy. \
                The user will provide you with a structured JSON input, with two key value pairs, 

                1. "policy_document": Data extracted from a Bajaj insurance policy document.
                2. "rfq_document": Data extracted from an insurance RFQ document.

                Your task is to compare the policy terms, conditions and insured limits present between these two and find \
                only the differences. 
                
                Structure the output with the following points in mind:
                - Both of these JSONs have identical structure (keys are the same) but may differ \
                in their values. The output must also be of the same structure, do not modify or add new keys. \
                - Include only the keys where the values differ between "policy_document" and "rfq_document".
                - For each key with a difference, include a descriptive string that clearly points out the difference in the \
                 values from "policy_document" and "rfq_document" (without needing to quote directly).
                - Exclude keys where the values are the same or similar, or equivalent based on context. 

                Keep the following things in mind while making the comparisons, to find differences:

                1. If a value is an empty string (""), it indicates that the scheme is either not covered or its limit is 0.

                2. Use contextual understanding to verify if differences are significant and meaningful.
                - For post_hospitalization_period (and related), 60 and 60 days refer to the same thing
                - For co_pay (and related), 50 and 50% mean the same thing
                - Coverage from day 1 and no waiting period are equivalent
                The above show that values can mean the same thing even if phrased differently, do not consider these \
                as differences.
                
                Below is a sample input with output
                ---
                Input :
                {{
                  "policy_document": {{
                    "co_pay": {{
                      "policy_co_payment_factor": "50%",
                      "co_pay_type": ""
                    }},
                    "waiting_period": "30 days",
                    "day_care_treatment": {{
                      "day_care_treatment": ""
                    }}
                  }},
                  "rfq_document": {{
                    "co_pay": {{
                      "policy_co_payment_factor": "40",
                      "co_pay_type": ""
                    }},
                    "waiting_period": "30",
                     "day_care_treatment": {{
                      "day_care_treatment": "Covered"
                    }},
                  }}
                }}
                Output:
                {{
                  "co_pay": "Policy document specifies 50% while RFQ document specifies 40%",
                  "day_care_treatment": "Not covered under policy document but covered under RFQ"
                }}
                ---
                
                Do not make guesses, only compare data from corresponding sections of the documents. Use contextual \
                understanding to point out the differences. Provide a precise output with the differences, no need to \
                quote the documents.  

                Ensure that the output is of proper JSON structure and does not contain any prefixes or suffixes \
                (such as ```json).
                '''
        },
        {
            'role': 'user',
            'content': f'{{"policy_document": {policy_out}, "rfq_document": {rfq_out}}}'
        }
    ]
    # print(data)
    response = get_completion_from_messages(messages)
    json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
    return json_str


def prompt_field_unfiltered(data):
    template = output_template_unfiltered()

    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
                data fields from unstructured text. The user will provide you with text which is scraped from an insurance \
                policy document by Bajaj. Your \
                task is to extract relevant fields and output them in the form of a JSON. The output should just be the json \
                with no prefix or suffix, and the format of the output should be \n
                --- 
                {template}
                ---
                Your task is to find the appropriate values for the keys in the dictionary, which are left as either empty \
                python strings or python lists. In the instances when the dict value is originally a list, you should set the \
                value to an element of this list, that has the closest match. If the data corresponding to the value of a key \
                is not present in the document, \
                set the value to an empty string or an empty list, depending on if originally the value was an empty string \
                or a list respectively. 
                Try to find as many entries as possible by parsing the document. Feel free to make reasonable guesses \
                and extrapolate based on given on given information. Try to fill in as many values as possible \
                Next to the value please provide your reasoning and source in parenthesis, for example for \
                "road_ambulance_limit": "2000 (Ambulance charges covered upto Rs. 2000/- per incident)"
                Please follow the template and instructions.
                '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {data}'
        }
    ]
    response = get_completion_from_messages(messages)
    print(response)
    return response


def prompt_excel(data):
    template = output_template_excel()

    messages = [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from structured data. The user will provide you with a JSON which is scraped from an insurance \
            policy document. Your \
            task is to extract relevant fields and output them in the form of a JSON. The output should just be the json \
            with no prefix or suffix, and the format of the output should be \n
            --- 
            {template}
            ---
            Your task is to find the appropriate values for the keys in the dictionary, which are left as either empty \
            python strings or python lists. In the instances when the dict value is originally a list, you should set the \
            value to an element of this list, that has the closest match. If the data corresponding to the value of a key \
            is not present in the document, \
            set the value to an empty string or an empty list, depending on if originally the value was an empty string \
            or a list respectively. \

            Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation \
            or negation. Leave the sum insured as an empty string if the policy is not covered.

            Keep the following things in mind, for different fields in the output:

            1. All values related to Corporate Buffer must be taken from the corresponding section, if this section
            is missing from the data, then do not fill in the values for corporate_buffer['sum_insured']. If present, the \
            type_of_ailment and type_of_coverage may also mentioned in this section.

            2. All values related to pre and post_natal_expenses_IPD and pre_and_post_natal_expenses_OPD must be taken \
            from the pre and post natal section or other conditions section of the data. The applicability may also be \
            mentioned here. If OPD is not covered \
            set expense_limit_OPD to an empty string.

            3. For home nursing benefit, keep in mind to convert allowance amount to per week (times 7) if given as per day and \
            to convert duration to number of weeks (divided by 7, return nearest integer) if given in number of days

            4. refractive_error_correction_expenses are mentioned under Other Conditions (sometimes under pre and post \
            natal) and may sometimes be labeled as lasik

            5. Do not confuse other sub limits for OPD limit

            6. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa \
            and Homoeopathy

            7. For maternity_expenses["waiting_period"] please check whether 9 months waiting period is Applicable or \
            Waived off

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template.

            '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {data}'
        }
    ]
    # print(data)
    response = get_completion_from_messages(messages)
    return response


def llm_first(df, model, tokenizer):
    messages = [
        {
            'role': 'system',
            'content': '''
        You are an AI json generator. You will be provided with data from a table, for creating the said \
        json. Your responses should \
        only contain information in the json format. \
        No need to print the json wrapper, only print the content of the json file, i.e. do not include \
        the '```json' tag in your replies. 
        '''
        },
        {
            'role': 'user',
            'content': f'''Given the information transcribed from a Group Mediclaim policy (or GMC) schedule, \
        your task is to identify relevant information. The information is provided in the form of a table, \
        delimited by triple backticks, use it to perform the upcoming task:
        ```{df}```

        You must identify the following information from the above data. If you cannot find relevant information, \
        just reply 'null': 
        1. Name of the company/institution to be insured
        2. City of the company/institution to be insured
        3. State of the company/institution to be insured
        4. PIN Code of the company/institution to be insured
        5. Normal Delivery Sum Insured (this should be a number)
        6. C-Section Delivery Sum Insured (this should be a number)
        7. Ambulance limit (this should be a number) (consider road/emergency ambulance limit, not air ambulance, if both are present) 
        8. AYUSH treatment limit (this should be a number)
        9. Type of industry/company
        10. Type of proposal (Fresh, Renewal, or Roll Over)
        11. Maternity waiting period (check if waiting period applicable or waived off, mention period if applicable, do not confuse with other waiting period)
        12. Pre-existing disease (PED) waiting period (check if waiting period applicable or waived off, mention period if applicable, do not confuse with other waiting period)
        13. Specific disease waiting period (check if waiting period applicable or waived off, mention period if applicable, do not confuse with other waiting period)
        14. Room Rent limit (mention as a number or percentage of SI)
        15. Room Rent deduction (capping on room charges or proportionate deduction)
        16. Pre-hospitalization period
        17. Post-hospitalization period
        18. Medical advancement surgery limit (as a percentage of SI)
        19. Co-pay type (all claims, non network hospitals, pre-agreed diseases, or no information)
        20. Co-pay factor (percentage of SI)
        21. Number of Deliveries (this should be a number)
        22. Plan type (Floater or Non-floater)

        In case of separate limits or deductions for general and ICU hospitalization, consider the general valuse.

        If the information is not present in the data, respond with 'null'. If limit says covered up to SI, mention that.
        All the values of the in the dict must be either str or int, do not include or sub-dicts.
        Format your reply as a python dict which has keys 'name', 'city', 'state', 'pin', \
        'normal_delivery_sum_insured', 'c_section_sum_insured', 'ambulance_limit', 'ayush_limit', 'type_of_industry', 'proposal_type', \
        'maternity_waiting_period', 'pre_existing_disease_waiting_period', 'specific_disease_waiting_period', 'room_rent_limit', 
        'room_rent_deduction', 'prehosp_period', 'posthosp_period', 'med_advancement_surgery_limit', \
        'copay_type', 'copay_factor', 'number_of_deliveries', and 'plan_type'.
        '''
        },
    ]
    summary = get_completion_qwen(messages, model, tokenizer)
    json_str = re.search(r'\{.*\}', summary, re.DOTALL).group(0)  # Extract the JSON part as a string
    return json_str


def llm_second(json_str, pdf_all, model, tokenizer):
    messages = [
        {
            'role': 'system',
            'content': '''
    You are an AI json generator. You will be provided with a json file, some of whose values \
    are 'null'. You will also be provided with data from a document, for creating the said \
    json. Do not change the values that already exist, only input values in place of null. \
    Your responses should only contain information in the json format. \
    Strictly adhere to the json format given to you, do not change it. \
    No need to print the json wrapper, only print the content of the json file, i.e. do not include \
    the '```json' tag in your replies. 
    '''
        },
        {
            'role': 'user',
            'content': f'''Given the information transcribed from a Group Mediclaim policy (or GMC) schedule, \
    your task is to identify relevant information. The information is \
    delimited by triple backticks, use it to perform the upcoming task:
    ```{pdf_all}```

    Your task is to fill the null valuse in the following json, delimitted by triple backticks. Restrict your \
    output to this format.
    ```{json_str}```

    In case of separate limits or deductions for general and ICU hospitalization, consider the general valuse.
    If the information is not present in the data, respond with 'null'. If limit says covered up to SI, mention that.
    All the values of the in the dict must be either str or int, do not include or sub-dicts.
    Do not change the keys of the dict, or add any new keys, do not change the pre-filled values.
    '''
        },
    ]

    summary = get_completion_qwen(messages, model, tokenizer)
    json_str = re.search(r'\{.*\}', summary, re.DOTALL).group(0)  # Extract the JSON part as a string
    return json_str


def gmc_mail_update_local(data, mail, model, tokenizer):
    messages = [
        {
            'role': 'system',
            'content': '''
    You are an AI agent, responsible for updating a json file. Your responses should only contain information in the json format. \
    You will be provided with a pre-filled json, whose values you may need to update based on new information. You are \
    only allowed to update the values of the json, do not change the keys. \
    No need to print the json wrapper, only print the content of the json file, i.e. do not include \
    the '```json' tag in your replies.
    '''
        },
        {
            'role': 'user',
            'content': f'''Information transcribed from a Group Mediclaim Policy (GMC) is provided below in the form of\
            a json, delimited by triple brackets. \
            ```{data}```

    Update the previous json, using the information provided in the json below:
    ```{mail}```

    For any discrepancy, between email and json, always consider the data in the email to be updated and final, and \
    consider that in your output.

    Do not change the format of the json. Do not rename, add new, or delete any keys. \
    Only update the values if needed.
    '''
        },
    ]
    summary = get_completion_qwen(messages, model, tokenizer)
    json_str = re.search(r'\{.*\}', summary, re.DOTALL).group(0)  # Extract the JSON part as a string
    return json_str


def llm_final_gpt(json_str):
    messages = [
        {
            'role': 'system',
            'content': '''
    You are an AI agent tasked with find the nearest match from a corresponding list. \
    You will be provided with a json file, your task is to match the values \
    of the corresponding keys to the nearest match from their corresponding python lists. Do \
    not use random values, make sure that the values are a member of the corresponding \
    python list.

    Do not rename, add new, or delete any keys. \
    No need to print the json wrapper, only print the content of the json file, i.e. do not include \
    the '```json' tag in your replies. 
    '''
        },
        {
            'role': 'user',
            'content': f'''Information transcribed from a Group Mediclaim policy (or GMC) schedule, \
    is provided to you in the form of a json, \
    delimited by triple backticks, use it to perform the upcoming task:
    ```{json_str}```

    Given below is an ordered list, containing the keys of the above json, and a corresponding \
    python list containing possible accetable valuse for that key 

    1. type_of_industry: ['IT and ITES', 'Manufacturing', 'Aviation', 'Media and Entertainment', 'Pharmaceuticals', 'Real Estate', 'Hospitality', 'Healthcare and hospitals', 'Education and Training', 'Insurance', 'Bank', 'NBFC', 'Other Financial Institution', 'NGO / Trust', 'Association', 'Society', 'SHG', 'Club', 'Military / Para Military force', 'Police Force', 'Law Enforcement agencies', 'Political Party / Firms', 'Grocery /Kirana Stores', 'Gymkhanas', 'Religious Group', 'Any kind of Shops', 'Event Management Companies / Teams', 'Mining industry', 'Sea-voyage Carriers', 'Film Industry', 'Adventure sport organizations', 'Tourism Industry', 'Agriculture Industry', 'Logistics and Transportation', 'Others', 'No info provided']
    2. proposal_type: ['Fresh', 'Renewal', 'Roll-over']
    3. maternity_waiting_period: ['No period', '9 month', 'No info provided']
    4. pre_existing_disease_waiting_period: ['No period', 'Applicable period', 'No info provided']
    5. specific_disease_waiting_period: ['No period', 'Applicable period', 'No info provided']
    6. room_rent_limit: ['Actual Rent', 'Rent up to a single private room', 'Rent up to twin sharing', 'Rest in general ward', '0.5% of SI max up to 2500', '1% of SI max up to 5000', '1.5% of SI max up to 7500', '2% of SI max up to 7500', 'No info provided']
    7. room_rent_deduction: ['Capping on Room Charges only', 'Proportionate Deduction', 'No info provided']
    8. prehosp_period: [0, 15, 30, 60, 90, 120, 'No info provided']
    9. posthosp_period: [0, 30, 60, 90, 120, 180, 'No info provided']
    10. med_advancement_surgery_limit: ['Upto 25% SI', 'Upto 50% SI', 'Upto SI', 'No info provided']
    11. copay_type: ['All Claims', 'Non-Network Hospitals/ Clinics', 'Pre-agreed disease/ procedure', 'No info provided']
    12. copay_factor: ['5% Copay', '10% Copay', '15% Copay', '20% Copay', '25% Copay', '30% Copay', 'No info provided']
    13. number_of_deliveries: [1, 2, 3, 'No info provided']
    14. plan_type: ['Floater', 'Individual or Non-Floater'] 


    Follow the instructions below to choose the best possible match:
    1. prehosp_period and posthosp_period must only be a number
    2. copay_factor must be mentioned as a percentage (sometime original value may be missing % symbol)
    3. In case of no deduction, capping or 100% coverage, room_rent_limit must be set to 'Actual Rent'

    Try to find the nearest match, which may or may not be exact to the pre-existing value. \
    Ensure that the value is an element of the corresponding python list.
    All the values of the in the dict must be either str or int, do not include or sub-dicts.
    '''
        },
    ]
    response = get_completion_from_messages(messages)
    json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)  # Extract the JSON part as a string
    return json_str


def llm_final_match(json_str, model, tokenizer) -> Dict:
    try:
        json_obj = json.loads(json_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding the JSON.")
    messages = [
        {
            'role': 'system',
            'content': '''
    You are an AI agent tasked with find the nearest match from a corresponding list. \
    You will be provided with a key avlue pair (json) followed by a list of possible values. \
    Your task is to replace the value in the json, with the closest matching value from the \
    corresponding list.
    Do not use random values, make sure that the values are a member of the corresponding \
    python list.
    You must respond with a dict which contains all of these key value pairs as a json.
    Do not rename, add new, or delete any keys. \
    No need to print the json wrapper, only print the content of the json file, i.e. do not include \
    the '```json' tag in your replies. 
    '''
        },
        {
            'role': 'user',
            'content': f'''Information transcribed from a Group Mediclaim policy (or GMC) schedule, \
    and corresponding lists of possible values are given below. Each pair of such is separed by a \
    dashed line '---'

    {{"type_of_industry": {json_obj['type_of_industry']}}}
    ['IT and ITES', 'Manufacturing', 'Aviation', 'Media and Entertainment', 'Pharmaceuticals', 'Real Estate', 'Hospitality', 'Healthcare and hospitals', 'Education and Training', 'Insurance', 'Bank', 'NBFC', 'Other Financial Institution', 'NGO / Trust', 'Association', 'Society', 'SHG', 'Club', 'Military / Para Military force', 'Police Force', 'Law Enforcement agencies', 'Political Party / Firms', 'Grocery /Kirana Stores', 'Gymkhanas', 'Religious Group', 'Any kind of Shops', 'Event Management Companies / Teams', 'Mining industry', 'Sea-voyage Carriers', 'Film Industry', 'Adventure sport organizations', 'Tourism Industry', 'Agriculture Industry', 'Logistics and Transportation', 'Others', 'No info provided']
    ---
    {{"proposal_type": {json_obj['proposal_type']}}}
    ['Fresh', 'Renewal', 'Roll-over']
    ---
    {{"maternity_waiting_period": {json_obj['maternity_waiting_period']}}}
    ['No period', '9 month', 'No info provided']
    ---
    {{"pre_existing_disease_waiting_period": {json_obj['pre_existing_disease_waiting_period']}}}
    ['No period', 'Applicable period', 'No info provided']
    ---
    {{"specific_disease_waiting_period": {json_obj['specific_disease_waiting_period']}}}
    ['No period', 'Applicable period', 'No info provided']
    ---
    {{"room_rent_limit": {json_obj['room_rent_limit']}}}
    ['Actual Rent', 'Rent up to a single private room', 'Rent up to twin sharing', 'Rest in general ward', '0.5% of SI max up to 2500', '1% of SI max up to 5000', '1.5% of SI max up to 7500', '2% of SI max up to 7500', 'No info provided']
    ---
    {{"room_rent_deduction": {json_obj['room_rent_deduction']}}}
    ['Capping on Room Charges only', 'Proportionate Deduction', 'No info provided']
    ---
    {{"prehosp_period": {json_obj['prehosp_period']}}}
    [0, 15, 30, 60, 90, 120, 'No info provided']
    ---
    {{"posthosp_period": {json_obj['posthosp_period']}}}
    [0, 30, 60, 90, 120, 180, 'No info provided']
    ---
    {{"med_advancement_surgery_limit": {json_obj['med_advancement_surgery_limit']}}}
    ['Upto 25% SI', 'Upto 50% SI', 'Upto SI', 'No info provided']
    ---
    {{"copay_type": {json_obj['copay_type']}}}
    ['All Claims', 'Non-Network Hospitals/ Clinics', 'Pre-agreed disease/ procedure', 'No info provided']
    ---
    {{"copay_factor": {json_obj['copay_factor']}}}
    ['5% Copay', '10% Copay', '15% Copay', '20% Copay', '25% Copay', '30% Copay', 'No info provided']
    ---
    {{"number_of_deliveries": {json_obj['number_of_deliveries']}}}
    [1, 2, 3, 'No info provided']
    ---
    {{"plan_type": {json_obj['plan_type']}}}
    ['Floater', 'Individual or Non-Floater'] 

    Follow the instructions below to choose the best possible match:
    1. prehosp_period and posthosp_period must only be a number
    2. copay_factor must be mentioned as a percentage (sometime original value may be missing % symbol)
    3. In case of no deduction, capping or 100% coverage, room_rent_limit must be set to 'Actual Rent'
    4. room_rent_limit may be missing a % symbol in the original value

    Replace the value with values only from the corresponding python list. \
    Try to find the closest match, which may or may not be exact to the pre-existing value. \
    Ensure that the value is an element of the corresponding python list.
    All the values of the in the dict must be either str or int, do not include or sub-dicts.
    Your output must be a json with the key and the replaced value pairs.
    '''
        },
    ]

    summary = get_completion_qwen(messages, model, tokenizer)
    json_str = re.search(r'\{.*\}', summary, re.DOTALL).group(0)  # Extract the JSON part as a string
    try:
        json_obj_updated = json.loads(json_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding the JSON.")
    json_obj.update({key: json_obj_updated[key] for key in json_obj if key in json_obj_updated})
    return json_obj


def llm_rec_match(prompt_str, model, tokenizer) -> Dict:
    messages = [
        {
            'role': 'system',
            'content': '''
    You are an AI agent tasked with find the nearest match from a corresponding list. \
    You will be provided with a key avlue pair (json) followed by a list of possible values. \
    Your task is to replace the value in the json, with the closest matching value from the \
    corresponding list.
    Do not use random values, make sure that the values are a member of the corresponding \
    python list.
    You must respond with a dict which contains all of these key value pairs as a json.
    Do not rename, add new, or delete any keys. \
    No need to print the json wrapper, only print the content of the json file, i.e. do not include \
    the '```json' tag in your replies. 
    '''
        },
        {
            'role': 'user',
            'content': f'''Information transcribed from a Group Mediclaim policy (or GMC) schedule, \
    and corresponding lists of possible values are given below. Each pair of such is separed by a \
    dashed line '---'

    {prompt_str}

    Follow the instructions below to choose the best possible match:
    1. prehosp_period and posthosp_period must only be a number
    2. copay_factor must be mentioned as a percentage (sometime original value may be missing % symbol)
    3. In case of no deduction, capping or 100% coverage, room_rent_limit must be set to 'Actual Rent'
    4. room_rent_limit may be missing a % symbol in the original value

    Replace the value with values only from the corresponding python list. \
    Try to find the closest match, which may or may not be exact to the pre-existing value. \
    Ensure that the value is an element of the corresponding python list.
    All the values of the in the dict must be either str or int, do not include or sub-dicts.
    Your output must be a json with the key and the replaced value pairs.
    '''
        },
    ]

    summary = get_completion_qwen(messages, model, tokenizer)
    json_str = re.search(r'\{.*\}', summary, re.DOTALL).group(0)  # Extract the JSON part as a string
    try:
        json_obj_updated = json.loads(json_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding the JSON.")
    return json_obj_updated


def demo_detection(df, model, tokenizer):
    messages = [
        {
            'role': 'system',
            'content': '''You are an AI helper who can only answer with  only 'True' or 'False'.'''
        },
        {
            'role': 'user',
            'content': f'''Given the following information formatted as a table, please check whether or not \
        it contains employees' demography information, i.e. a list containing names of employees (possibly also their \
        relations), along with age, sum insured and other data. This should contain names of all insured, and not a summary.

        The transcribed information is provided here, delimited by triple backticks.
        ```{df.to_string(index=False, na_rep='')}```

        Please only reply 'True' if it contains employees' demography information, 'False' if not or \
        if you are not sure. Do not provide any explanation for your answer. Restrict the output to either \
        'True' or 'False'. '''
        },
    ]
    summary = get_completion_qwen(messages, model, tokenizer)
    return summary


def prompt_sum_insured(data):
    messages = [
        {
            'role': 'system',
            'content': '''You are an AI data extraction assistant specialized in identifying and extracting specific \
                data fields from from table data. Your \
                task is to extract relevant fields and output them in the form of a JSON. The output should just be the json \
                with no prefix or suffix, and the format of the output should be \n

                {"sumInsured": ""}

                Your task is to find the total sum insured, if it is present in the data document (not the sum insured \
                for sub-categories)
                '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {data}'
        }
    ]
    response = get_completion_from_messages(messages)
    print(response)
    return response


def gmc_mail_update(data, mail):
    messages = [
        {
            'role': 'system',
            'content': '''
    You are an AI agent, responsible for updating a json file. Your responses should only contain information in the json format. \
    You will be provided with a pre-filled json, whose values you may need to update based on new information. You are \
    only allowed to update the values of the json, do not change the keys. \
    No need to print the json wrapper, only print the content of the json file, i.e. do not include \
    the '```json' tag in your replies.
    '''
        },
        {
            'role': 'user',
            'content': f'''Information transcribed from a Group Mediclaim Policy (GMC) is provided below in the form of\
            a json, delimited by triple brackets. \
            ```{data}```

    Update the previous json, using the information provided in the json below:
    ```{mail}```

    For any discrepancy, between email and json, always consider the data in the email to be updated and final, and \
    consider that in your output.

    Do not change the format of the json, only update the values if and when needed.
    '''
        },
    ]

    response = get_completion_from_messages(messages)
    return response
def get_validation_rules() -> Dict[str, List[str]]:
    """Returns validation regex patterns for each field"""
    return {
        "policy_number": [r"^[A-Z]{2,3}-\d{6,8}$", "Invalid policy number format"],
        "dates": [r"^\d{2}-\d{2}-\d{4}$", "Date must be DD-MM-YYYY"],
        "currency": [r"^₹?\d{1,3}(,\d{3})*(\.\d{2})?$", "Invalid currency format"]
    }
SCHEMA_FIELDS = {
    "day_care_treatment": ["day_care_treatment"],
    "organ_donor_expenses": ["organ_donor_expenses"],
    "pre_and_post_natal_expenses_IPD": ["expenses_limit_IPD", "applicability"],
    "maternity_expenses": ["limit_normal_delivery", "limit_C_Section", "waiting_period", "no_of_deliveries"],
    "pre_and_post_natal_expenses_OPD": ["expenses_limit_OPD"],
    "corporate_buffer": ["sum_insured", "type_of_ailment", "type_of_coverage"],
    "refractive_error_correction_expenses": ["si_limit", "eye_power"],
    "hiv_anti_retroviral_therapy": ["hiv_anti_retroviral_therapy"],
    "home_nursing_benefit": ["home_nursing_benefit_limit", "no_of_days"],
    "preventive_health_check_up": ["preventive_healthcheckup_limit"],
    "opd_expenses": ["benefit_limit"],
    "physiotherapy_on_opd_basis": ["physiotherapy_limit"],
    "dental_care": ["benefit_limit"],
    "mental_illness": ["benefit_limit"],
    "vision_expenses_cover": ["benefit_limit"],
    "obesity_control_coverage": ["obesity_control_coverage"],
    "co_pay": ["policy_co_payment_factor", "co_pay_type"],
    "room_rent": ["room_rent_limit", "icu_limit", "options_for_deductions"],
    "road_ambulance": ["road_ambulance_limit"],
    "ayush_treatment": ["ayush_treatment_limit"],
    "medical_advancement_surgery": ["applicable", "limit"],
    "pre_hospitalization": ["pre_hospitalization_period"],
    "post_hospitalization": ["post_hospitalization_period"],
    "pre_existing_disease_and_specified_disease": ["covered", "waiting_period"],
    "hospital_cash": ["hospital_cash_limit_per_day", "hospital_cash_limit_days"],
    "emergency_air_ambulance": ["limit"],
    "extra": ["policy_certificate_no", "pan_number", "gstin", "no_of_persons_covered"]
}
