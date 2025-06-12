from utils import get_completion_json
from output_schema import OutputFull

def generate_llm_prompt(unstructured_text: str):
    return [
        {"role": "system", "content": "You are an assistant that extracts structured insurance policy details from raw text. "},
        {"role": "user", "content": f"Extract the required information from the following policy text but if some field doesnt \
          have an appropiate text then dont print it and leave it empty. \
          1.If Daycare treatment doesnt have any specified content leave it empty. \
          2. Extract the following fields from the Room Rent section of the policy: \
                sum_insured: List all values under the Sum Insured column (do not extract any values from other columns).\
                maximum_eligibility_for_normal_hospitalization: List all values under the Maximum eligibility for Normal Hospitalization column.\
                maximum_eligibility_for_icu_hospitalization: List all values under the Maximum eligibility for ICU Hospitalization column.\
          Return it as JSON:\n\n{unstructured_text}"}
    ]

def get_llm_output(text: str):
    messages = generate_llm_prompt(text)
    output = get_completion_json(messages, schema_format=OutputFull)
    return output
