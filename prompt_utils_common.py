from utils_common import get_completion_json, text_space_cleaner, output_template
from output_schema_common import OutputFull

def generate_llm_prompt_nilay(unstructured_text: str):
    template = output_template(incl_headings=True)

    return [
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
            mentioned here. The max liability on maternity expenses is maternity_expense. If OPD is not covered \
            set expense_limit_OPD to an empty string.Do not mistake Pre and Post Hospitalization for pre and post_natal_expenses_IPD

            3. Surgery limit for medical_advancement_surgery may be mentioned as Modern Treatment Methods and Advancement \
            in Technologies under Other Conditions

            5. refractive_error_correction_expenses are mentioned under Other Conditions or sometimes under Pre and Post \
            Natal. These may be labeled as "Lasik" or "Lasik Surgery". If the document says something like \
            "Covered if correction index is +/- 7.5D", or "Covered for +-- 7. 5", extract `7.5` as the `eye_power`. \
            Normalize formatting errors like "+-- 7. 5", "+/-7.5", "+ / -7.5" and treat them equivalently. \
            If no specific eye power is mentioned or the number is ambiguous, return 0.0.

            6. Room Restrictions: room_restrictions
            If there are no room restrictions, set options_for_deductions as an empty list.

            7. Do not confuse other sub limits for OPD limit

            8. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa \
            and Homoeopathy. If mentioned Like - x% of sum insured , return whole value

            9. If there is no mention of co_pay or any of its sub keys, set them to empty lists

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template.
            10. If the document mentions “Pre-Post Natal Covered up to X”, assume this applies to OPD unless specifically mentioned otherwise. Map it to pre_and_post_natal_expenses_OPD → expenses_limit_OPD.

            11. If the document contains phrases like “Pre and Post Hospitalization Expenses covered up to 30/60 days” or “30/60 days respectively”, \
            interpret them as 30 days of Pre-Hospitalization and 60 days of Post-Hospitalization. \
            Set `"pre_hospitalization_period"` to `"30 days"` and `"post_hospitalization_period"` to `"60 days"`. \
            The number before the slash corresponds to pre-hospitalization, and the number after the slash corresponds to post-hospitalization. \
            This logic applies even if the sentence is phrased differently or includes extra text like “respectively” or “up to”.

            12. If the document says "9 months waiting period: Waive off" or similar (e.g., "9 month waiting period waived off for all insured members"), then map the maternity waiting_period as "Waived off" (instead of "9 Months").

            13. If the policy says "All Day Care Procedures are covered" or "covered as per IRDA list" or ": Day Care Procedures are Covered as per the \
            standard list" or something similar , treat that as day_care_treatment = "Covered".

            14. If the policy says "Donor expenses are not covered", set organ_donor_expenses = "Not Covered".

            15. If "Modern Treatment" or "Advanced Technology" is covered up to a percentage (e.g. 50%), set medical_advancement_surgery_limit accordingly. 

            16. If Day care treatment explicitly not mentioned return as- not covered.

            '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {unstructured_text}'
        }
    ]
def get_llm_output_nilay(text: str):
    messages = generate_llm_prompt_nilay(text)
    return get_completion_json(messages, schema_format=OutputFull)


def generate_llm_prompt_amogh(unstructured_text: str):
    template = output_template(incl_headings=True)

    return [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific \
            data fields from unstructured text. The user will provide you with text which is scraped from insurance \
            policy documents. Your \
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

            1. Only extract values for the corporate_buffer section if a dedicated Corporate Buffer section or heading is clearly present in the text.\

            Do not assume or infer Corporate Buffer values based on general mentions of sum insured or benefit limits elsewhere.\

            If no such section exists, leave all corporate_buffer fields (sum_insured, type_of_ailment, type_of_coverage) blank.\

            If the Corporate Buffer section is present, extract the relevant fields as stated explicitly under that section.

            2. All values related to pre and post_natal_expenses_IPD and pre_and_post_natal_expenses_OPD must be taken \
            from the pre and post natal section or other conditions section of the data. The applicability may also be \
            mentioned here. The max liability on maternity expenses is maternity_expense. If OPD is not covered \
            set expense_limit_OPD to an empty string.Do not mistake Pre and Post Hospitalization for pre and post_natal_expenses_IPD

            3. Surgery limit for medical_advancement_surgery may be mentioned as Modern Treatment Methods and Advancement \
            in Technologies under Other Conditions

            4. For home nursing benefit, keep in mind to convert allowance amount to per week (times 7) if given as per day and \
            to convert duration to number of weeks (divided by 7, return nearest integer) if given in number of days

            5. refractive_error_correction_expenses are mentioned under Other Conditions or sometimes under Pre and Post \
            Natal. These may be labeled as "Lasik" or "Lasik Surgery". If the document says something like \
            "Covered if correction index is +/- 7.5D", or "Covered for +-- 7. 5", extract `7.5` as the `eye_power`. \
            Normalize formatting errors like "+-- 7. 5", "+/-7.5", "+ / -7.5" and treat them equivalently. \
            If no specific eye power is mentioned or the number is ambiguous, return 0.0.


            6. Room Restrictions: room_restrictions
            If there are no room restrictions, set options_for_deductions as an empty list.

            7. Do not confuse other sub limits for OPD limit

            8. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa \
            and Homoeopathy. If mentioned Like - x% of sum insured , return whole value

            9. If there is no mention of co_pay or any of its sub keys, set them to empty lists

            Do not make guesses, only take data from the document from the \
            relevant sections as present in the template.
            10. If the document mentions “Pre-Post Natal Covered up to X”, assume this applies to OPD unless specifically mentioned otherwise. Map it to pre_and_post_natal_expenses_OPD → expenses_limit_OPD.

            11. If the document contains phrases like “Pre and Post Hospitalization Expenses covered up to 30/60 days” or “30/60 days respectively”, \
            interpret them as 30 days of Pre-Hospitalization and 60 days of Post-Hospitalization. \
            Set `"pre_hospitalization_period"` to `"30 days"` and `"post_hospitalization_period"` to `"60 days"`. \
            The number before the slash corresponds to pre-hospitalization, and the number after the slash corresponds to post-hospitalization. \
            This logic applies even if the sentence is phrased differently or includes extra text like “respectively” or “up to”.

            12. If the document says "9 months waiting period: Waive off" or similar (e.g., "9 month waiting period waived off for all insured members"), then map the maternity waiting_period as "Waived off" (instead of "9 Months").

            13. If the policy says "All Day Care Procedures are covered" or "covered as per IRDA list" or ": Day Care Procedures are Covered as per the \
            standard list" or something similar , treat that as day_care_treatment = "Covered".

            14. If the policy says "Donor expenses are not covered", set organ_donor_expenses = "Not Covered".

            15. If "Modern Treatment" or "Advanced Technology" is covered up to a percentage (e.g. 50%), set medical_advancement_surgery_limit accordingly. 

            16. Only extract a value for total_sum_insured if the text explicitly mentions phrases like "Total Sum Insured", "Aggregate Sum Insured", or clearly equivalent terms.\
            Do not assume or infer the total sum insured based on standalone numbers or contextually unrelated sum insured values (e.g., corporate buffer, room rent, maternity, etc.).\
            If no such explicit mention is found, leave total_sum_insured blank.

            17. If under the heading "Psychiatric In-patient Care" , it says something like "We will cover the Medical Expenses up to Rs. 30000 for In-patient treatment".....\
            then extract the value of 30000 as "psychiatric_ailment_limit": "30000". If there is a diffent value then extract that , not just for 30000.


            '''
        },
        {
            'role': 'user',
            'content': f'Policy Document: \n {unstructured_text}'
        }
    ]
def get_llm_output_amogh(text: str):
    messages = generate_llm_prompt_amogh(text)
    return get_completion_json(messages, schema_format=OutputFull)


def generate_llm_prompt_atreya(unstructured_text: str):
    template = output_template(incl_headings=True)

    return [
        {
            'role': 'system',
            'content': f'''You are an AI data extraction assistant specialized in identifying and extracting specific 
data fields from unstructured text. The user will provide you with text which is scraped from an insurance 
policy document by Bajaj. Your 
task is to extract relevant fields and output them in the form of a JSON. The output should just be the json 
with no prefix or suffix, and the format of the output should be: 

--- 
{template}
---

Your task is to find the appropriate values for the keys in the dictionary, which are left as either empty 
python strings or python lists. In the instances when the dict value is originally a list, you should set the 
value to an element of this list, that has the closest match. If the data corresponding to the value of a key 
is not present in the document, 
set the value to an empty string or an empty list, depending on if originally the value was an empty string 
or a list respectively.

Wherever talking about limits, sum insured, or numbers, only give the number. Do not fill with confirmation 
or negation. Leave the sum insured as an empty string if the policy is not covered.

Keep the following things in mind, for different fields in the output:

1. All values related to Corporate Buffer must be taken from the corresponding section. If this section
is missing from the data, then do not fill in the values for corporate_buffer['sum_insured']. If present, the 
type_of_ailment and type_of_coverage may also be mentioned in this section.

2. All values related to pre and post_natal_expenses_IPD and pre_and_post_natal_expenses_OPD must be taken 
from the pre and post natal section or other conditions section of the data. The applicability may also be 
mentioned here. The max liability on maternity expenses is maternity_expense. If OPD is not covered 
set expense_limit_OPD to an empty string. Do not mistake Pre and Post Hospitalization for pre and post_natal_expenses_IPD

3. Surgery limit for medical_advancement_surgery may be mentioned as Modern Treatment Methods and Advancement 
in Technologies under Other Conditions

4. For home nursing benefit, keep in mind to convert allowance amount to per week (times 7) if given as per day and 
to convert duration to number of weeks (divided by 7, return nearest integer) if given in number of days

5. refractive_error_correction_expenses are mentioned under Other Conditions or General conditions . These may be labeled as "Lasik" or "Lasik Surgery". If the document specifies correction index, extract the number as eye_power. Normalize formatting errors in the number and treat them equivalently. If no specific eye power is mentioned or the number is ambiguous, return 0.0. Also extract si_limit if mentioned. If not mentioned, return "".

6. Room Restrictions: room_restrictions. 
If there are no room restrictions, set options_for_deductions as an empty list.

7. Do not confuse other sub limits for OPD limit

8. ayush_treatment_limit may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, Sowa Rigpa 
and Homoeopathy. If mentioned like "x% of sum insured", return whole value

9. If there is no mention of co_pay or any of its sub keys, set them to empty lists

10. If the document mentions “Pre-Post Natal Covered up to X”, assume this applies to OPD unless specifically mentioned otherwise. Map it to pre_and_post_natal_expenses_OPD → expenses_limit_OPD.

11. If the document contains phrases like “Pre and Post Hospitalization Expenses covered up to 30/60 days” or “30/60 days respectively”, 
interpret them as 30 days of Pre-Hospitalization and 60 days of Post-Hospitalization. 
Set "pre_hospitalization_period" to "30 days" and "post_hospitalization_period" to "60 days". 
The number before the slash corresponds to pre-hospitalization, and the number after the slash corresponds to post-hospitalization. 
This logic applies even if the sentence is phrased differently or includes extra text like “respectively” or “up to”.

12. When extracting the "total sum insured" or "total coverage" from the document, strictly follow these rules:
- Never extract the "Premium" or any payable amount as the sum insured. The sum insured is *always* the insurance coverage, not any payment, GST, or receipt value.
- If both "Premium" and a larger "Total" (for example, "Total Sum Insured", "Total", or a figure in words) are present, always choose the *largest value labeled as sum insured, total coverage, or total*.
- Pay attention to phrases like “₹ X” or “RUPEES [AMOUNT IN WORDS]” next to the total, sum insured, or coverage.
- Ignore values next to "Premium", "GST", "Receipt No.", or any values only referenced for payment or tax.
- Prefer values labeled as "Total Sum Insured", "Total", "Total Coverage", or similar. These are usually in summary tables at the end or bottom of the page.
- *If there is any ambiguity*, select the value that represents the maximum coverage provided by the policy to the insured party, and confirm this is not a premium or a tax.

13. For day_care_treatment, always extract the specific list of procedures or treatments mentioned as "day care" in the policy, even if it is described as "day care procedures", "treatments requiring less than 24 hours hospitalization", or any similar language. If a list is present, include the actual treatments/procedures as a comma-separated string. If the policy says "All day care procedures as per IRDAI list are covered," set value to "All as per IRDAI list." If not mentioned, leave blank.

14. For *AYUSH treatment*, extract any details regarding coverage for Ayurveda, Yoga and Naturopathy, Unani, Siddha, and Homeopathy systems. If the document specifies a percentage or limit of sum insured for AYUSH, provide that value (e.g., "AYUSH: Expenses incurred for Ayurvedic / Homeopathic / Unani Treatment are admissible up to 25% of the sum insured provided the treatment is taken in an AYUSH hospital").

Example:
If the table contains both:
Premium: ₹ 7,411,019  
GST: ₹ 1,333,984  
Total: ₹ 8,745,003  
then the sum insured should be parsed as ₹ 8,745,003 (the total), *not* the premium or GST.

15. For the maternity waiting period: If the document explicitly says that the standard 9 months maternity waiting period is deleted or waived, set the waiting_period to "waived". If there is no such statement, assume the waiting_period is "9 months".

16. Corporate Buffer Sum Insured:

Do not confuse “Corporate Buffer Sum Insured” with “Total Sum Insured.”

“Corporate Buffer Sum Insured” should only be filled if there is an explicit mention of a corporate buffer or buffer fund in the policy document.

If no such section or mention is found, set corporate_buffer["sum_insured"] to an empty string.

Even if both values (corporate buffer and total sum insured) are numerically equal or appear near each other, do not assume they are the same.

These represent separate allocations and must be extracted independently.
'''
        },
        {
            'role': 'user',
            'content': f'Policy Document:\n{unstructured_text}'
        }
    ]

def get_llm_output_atreya(text: str):
    messages = generate_llm_prompt_atreya (text)
    return get_completion_json(messages, schema_format=OutputFull)
