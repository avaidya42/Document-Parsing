import re
from PyPDF2 import PdfReader

def parse_reliance_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    text = re.sub(r'\s+', ' ', text)

    # --- Improved regex patterns ---
    co_pay_match = re.search(r'\b(\d{1,2})%\b.*?Co-?pay', text, re.IGNORECASE)
    ambulance_match = re.search(r'Ambulance[^.]*?(?:INR|₹)?\s*[, ]?(\d{3,6})', text, re.IGNORECASE)
    normal_delivery = re.search(r'Normal\s+Delivery\s*[:-]?\s*(?:INR|₹)?\s*[, ]?(\d{2,6})', text, re.IGNORECASE)
    c_section = re.search(r'(?:LSCS|C[\s-]?Section)\s*[:-]?\s*(?:INR|₹)?\s*[, ]?(\d{2,6})', text, re.IGNORECASE)
    no_of_deliveries = re.search(r'(?:No(?:\.|umber)?\s*of\s*Deliver(?:y|ies))\s*[:-]?\s*(\d{1,2})', text, re.IGNORECASE)
    waiting = re.search(r'Waiting\s*Period\s*[:-]?\s*(\d{1,4})', text, re.IGNORECASE)
    pre_hosp = re.search(r'Pre[- ]?Hospitalization.*?(\d+)', text, re.IGNORECASE)
    post_hosp = re.search(r'Post[- ]?Hospitalization.*?(\d+)', text, re.IGNORECASE)
    room_rent_match = re.search(r'Room Rent.*?(2%.*?4%.*?\))', text, re.IGNORECASE)

    return {
        "day_care_treatment": {"day_care_treatment": ""},
        "organ_donor_expenses": {"organ_donor_expenses": ""},
        "pre_and_post_natal_expenses_IPD": {
            "expenses_limit_IPD": "",
            "applicability": ""
        },
        "maternity_expenses": {
            "no_of_deliveries": no_of_deliveries.group(1) if no_of_deliveries else "",
            "limit_normal_delivery": normal_delivery.group(1) if normal_delivery else "",
            "limit_C_Section": c_section.group(1) if c_section else "",
            "waiting_period": waiting.group(1) if waiting else ""
        },
        "pre_and_post_natal_expenses_OPD": {
            "expenses_limit_OPD": ""
        },
        "corporate_buffer": {
            "sum_insured": "",
            "type_of_ailment": "",
            "type_of_coverage": ""
        },
        "refractive_error_correction_expenses": {
            "si_limit": "",
            "eye_power": 0.0
        },
        "hiv_anti_retroviral_therapy": {
            "hiv_anti_retroviral_therapy": ""
        },
        "home_nursing_benefit": {
            "per_week_benefit": "",
            "number_of_weeks": ""
        },
        "preventive_health_check_up": {
            "benefit_limit": "",
            "clinic_options": ""
        },
        "opd_expenses": {
            "benefit_limit": ""
        },
        "physiotherapy_on_opd_basis": {
            "benefit_limit": "",
            "coverage_type": ""
        },
        "dental_care": {
            "benefit_limit": ""
        },
        "mental_illness": {
            "benefit_limit": ""
        },
        "vision_expenses_cover": {
            "benefit_limit": ""
        },
        "obesity_control_coverage": {
            "obesity_control_coverage": ""
        },
        "co_pay": {
            "policy_co_payment_factor": co_pay_match.group(1) + "%" if co_pay_match else "",
            "co_pay_type": "Specified illness" if "Specified illness" in text else ""
        },
        "room_rent": {
            "room_rent_limit": room_rent_match.group(1) if room_rent_match else "",
            "options_for_deductions": "Proportionate Deduction" if "Proportionate Deduction" in text else ""
        },
        "road_ambulance": {
            "road_ambulance_limit": ambulance_match.group(1) if ambulance_match else ""
        },
        "ayush_treatment": {
            "ayush_treatment_limit": ""
        },
        "medical_advancement_surgery": {
            "medical_advancement_surgery_limit": ""
        },
        "pre_hospitalization": {
            "pre_hospitalization_period": pre_hosp.group(1) if pre_hosp else ""
        },
        "post_hospitalization": {
            "post_hospitalization_period": post_hosp.group(1) if post_hosp else ""
        },
        "pre_existing_disease_and_specified_disease": {
            "pre_existing_disease_and_specified_disease_waiting_period": waiting.group(1) if waiting else ""
        }
    }
