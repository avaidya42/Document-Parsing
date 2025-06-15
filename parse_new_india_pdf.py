import re
from typing import Dict
import pdfplumber

# Schema-compliant template
OUTPUT_TEMPLATE = {
    "day_care_treatment": {"day_care_treatment": ""},
    "organ_donor_expenses": {"organ_donor_expenses": ""},
    "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "", "applicability": ""},
    "maternity_expenses": {"limit_normal_delivery": "", "limit_C_Section": "", "waiting_period": ""},
    "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
    "corporate_buffer": {"sum_insured": "", "type_of_ailment": "", "type_of_coverage": ""},
    "refractive_error_correction_expenses": {"si_limit": "", "eye_power": ""},
    "hiv_anti_retroviral_therapy": {"hiv_anti_retroviral_therapy": ""},
    "home_nursing_benefit": {"per_week_benefit": "", "number_of_weeks": ""},
    "preventive_health_check_up": {"benefit_limit": "", "clinic_options": ""},
    "opd_expenses": {"benefit_limit": ""},
    "physiotherapy_on_opd_basis": {"benefit_limit": "", "coverage_type": ""},
    "dental_care": {"benefit_limit": ""},
    "mental_illness": {"benefit_limit": ""},
    "vision_expenses_cover": {"benefit_limit": ""},
    "obesity_control_coverage": {"obesity_control_coverage": ""},
    "co_pay": {"policy_co_payment_factor": "", "co_pay_type": ""},
    "room_rent": {"room_rent_limit": "", "options_for_deductions": ""},
    "road_ambulance": {"road_ambulance_limit": ""},
    "ayush_treatment": {"ayush_treatment_limit": ""},
    "medical_advancement_surgery": {"medical_advancement_surgery_limit": ""},
    "pre_hospitalization": {"pre_hospitalization_period": ""},
    "post_hospitalization": {"post_hospitalization_period": ""},
    "pre_existing_disease_and_specified_disease": {"pre_existing_disease_and_specified_disease_waiting_period": ""},
    "extra": ""
}

def extract(pattern, text, group=1, default="", flags=0):
    match = re.search(pattern, text, flags)
    return match.group(group).strip() if match else default

def parse_new_india_pdf_text(text: str) -> Dict:
    result = OUTPUT_TEMPLATE.copy()

    # Room Rent/ICU
    result["room_rent"]["room_rent_limit"] = extract(r"room.*?[:\-\s]+(\d+(\.\d+)?%)\s*/", text)
    result["room_rent"]["options_for_deductions"] = extract(r"(proportionate\s+reduction\s+applicable)", text, flags=re.IGNORECASE)

    icu_pct = extract(r"/\s*(\d+(\.\d+)?%)\s*of\s*S\.?I", text)
    if icu_pct:
        result["room_rent"]["room_rent_limit"] += " of Sum Insured"
        result["room_rent"]["options_for_deductions"] = "Proportionate reduction applicable"

    # Maternity
    result["maternity_expenses"]["limit_normal_delivery"] = extract(r"normal delivery[^\d]*(\d{2,6})", text)
    result["maternity_expenses"]["limit_C_Section"] = extract(r"c[-\s]?section[^\d]*(\d{2,6})", text)
    if re.search(r"deletion of 9[\s-]*month", text, re.IGNORECASE):
        result["maternity_expenses"]["waiting_period"] = "Waiting"

    # Ambulance
    result["road_ambulance"]["road_ambulance_limit"] = extract(r"ambulance charges[^\d]*(\d{4,6})", text)

    # Corporate buffer
    result["corporate_buffer"]["sum_insured"] = extract(r"corporate buffer[^\d]*(\d{2,6})", text)

    # Extra fields
    extras = []
    cert = extract(r"Policy Certificate No\.?\s*:?\s*([\w\d]+)", text)
    pan = extract(r"PAN\s*No\.?\s*:?\s*([A-Z0-9]{10})", text)
    gst = extract(r"GSTIN\s*:?\s*([\dA-Z]{15})", text)
    lives = extract(r"No of persons covered\s*:?\s*(\d+)", text)
    if cert: extras.append(f"policy_certificate_no: {cert}")
    if pan: extras.append(f"pan_number: {pan}")
    if gst: extras.append(f"gstin: {gst}")
    if lives: extras.append(f"no_of_persons_covered: {lives}")
    result["extra"] = "; ".join(extras)

    return result
