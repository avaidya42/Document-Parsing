from utils import get_completion_json,output_template
from output_schema import OutputFull

def generate_llm_prompt(unstructured_text: str):
    return [
        {"role": "system", "content": "You are an assistant that extracts structured insurance policy details from raw text. "},
        {"role": "user", "content": f"Extract the required information from the following policy text but if some field doesnt \
          have an appropiate text then dont print it and leave it empty. \
          1.If Daycare treatment has a value like-Covered upto Sum Insured and this sum isured is the value of- Inpatient Care - Sum Insured , \
          display the value of that field or if it doesnt have any specified content leave it empty. \
          2. For home_nursing_benefit it is mentioned under the heading-Standard Definitions-Any one illness.For the number of weeks field if days \
          are mentioned - divide days by 7 to acquire number of weeks and if it is in decimal make it nearest whole number.Leave eampty if nothing mentioned. \
          3. From the Benefits Opted table - extract relevant fields for room_rent_limit,icu,pre_hospitalization_period,post_hospitalization_period,under maternity-  no_of_deliveries  \
          limit_normal_delivery,limit_C_Section,waiting_period. \
          carefully interpret the table layout: \
                1.For any kind of nested values such as : Room rent, ICU, Normal, C-section \
                2.If any section contains textual notes for room rent or maternity .. or any field go through them and include them as needed. \
                3.f a field is - Not Covered or - NA, set it accordingly.\
          Return it as JSON in this format-:\n\n{unstructured_text}"}
    ]

def get_llm_output(text: str):
    messages = generate_llm_prompt(text)
    output = get_completion_json(messages, schema_format=OutputFull)
    return output
