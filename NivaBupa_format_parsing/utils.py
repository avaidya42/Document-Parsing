import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from io import BytesIO
import re
import torch
import gc

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sec_api_key = os.getenv("SEC_API_KEY")
sec_api_endpoint = os.getenv("SEC_API_ENDPOINT")
serp_api_key = os.getenv("SERP_API_KEY")

def get_completion(messages, model="gpt-4o-mini", temperature=0):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    print("Prompt Tokens:", response.usage.prompt_tokens)
    print("Completion Tokens:", response.usage.completion_tokens)
    return response.choices[0].message.content


def get_completion_json(messages, schema_format, model="gpt-4o-mini", temperature=0):
    response = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format=schema_format
    )
    return response.choices[0].message.parsed.model_dump()

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

def output_template(incl_headings=False):
    heading_outputs = {"Policy No" : {"policy_number":""},
                       "name_of_policy_holder":{"name_of_policy_holder":""},
                       "policy_period":{"policy_period_start_date":"","policy_period_end_date":""},
                       "primary_imsured_members":{"policy_insured_numbers":""},
                       }
    # these are added to the final result without the help of a llm

    output = {"day_care_treatment": {"day_care_treatment": ""},
              "organ_donor_expenses": {"organ_donor_expenses": ""},
              "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "",
                                                  "applicability": ""},
              "maternity_expenses": {"no_of_deliveries": ""},
              "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
              "corporate_buffer": {"sum_insured": "",
                                   "type_of_ailment": ""},
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
    text = re.sub(r'-\n', '', str(text))
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text.replace('\xa0', ' '))
    return text.strip()
