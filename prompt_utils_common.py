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
    messages = generate_llm_prompt_amogh(text)
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

            1. All values related to Corporate Buffer must be taken from the corresponding section, if this section
            is missing from the data, then do not fill in the values for corporate_buffer['sum_insured']. If present, the \
            type_of_ailment and type_of_coverage may also mentioned in this section.

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

            16. Unless it says the words "Total sum insured" or "Aggregate sum insured" or something similar , do not print it under "total_sum_insured".


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
