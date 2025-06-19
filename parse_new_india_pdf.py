import re
from typing import Dict
import pdfplumber

OUTPUT_TEMPLATE = {
    "day_care_treatment": {"day_care_treatment": ""},
    "organ_donor_expenses": {"organ_donor_expenses": ""},
    "pre_and_post_natal_expenses_IPD": {"expenses_limit_IPD": "", "applicability": ""},
    "maternity_expenses": {
        "limit_normal_delivery": "",
        "limit_C_Section": "",
        "waiting_period": "",
        "no_of_deliveries": ""
    },
    "pre_and_post_natal_expenses_OPD": {"expenses_limit_OPD": ""},
    "corporate_buffer": {"sum_insured": "", "type_of_ailment": "", "type_of_coverage": ""},
    "refractive_error_correction_expenses": {"si_limit": "", "eye_power": ""},
    "hiv_anti_retroviral_therapy": {"hiv_anti_retroviral_therapy": ""},
    "home_nursing_benefit": {"home_nursing_benefit_limit": "", "no_of_days": ""},
    "preventive_health_check_up": {"preventive_healthcheckup_limit": ""},
    "opd_expenses": {"benefit_limit": ""},
    "physiotherapy_on_opd_basis": {"physiotherapy_limit": ""},
    "dental_care": {"benefit_limit": ""},
    "mental_illness": {"benefit_limit": ""},
    "vision_expenses_cover": {"benefit_limit": ""},
    "obesity_control_coverage": {"obesity_control_coverage": ""},
    "co_pay": {"policy_co_payment_factor": "", "co_pay_type": ""},
    "room_rent": {"room_rent_limit": "", "icu_limit": "", "options_for_deductions": ""},
    "road_ambulance": {"road_ambulance_limit": ""},
    "ayush_treatment": {"ayush_treatment_limit": ""},
    "medical_advancement_surgery": {"applicable": "", "limit": ""},
    "pre_hospitalization": {"pre_hospitalization_period": ""},
    "post_hospitalization": {"post_hospitalization_period": ""},
    "pre_existing_disease_and_specified_disease": {"covered": "", "waiting_period": ""},
    "hospital_cash": {"hospital_cash_limit_per_day": "", "hospital_cash_limit_days": ""},
    "emergency_air_ambulance": {"limit": ""},
    "extra": {
        "policy_certificate_no": "",
        "pan_number": "",
        "gstin": "",
        "no_of_persons_covered": ""
    }
}

def extract(pattern, text, group=1, default="", flags=0):
    match = re.search(pattern, text, flags)
    return match.group(group).strip() if match else default

def parse_new_india_pdf_text(text: str) -> Dict:
    result = OUTPUT_TEMPLATE.copy()

    def set_value(path, value):
        parent, key = path.split('.')
        if value:
            result[parent][key] = value

    # --- Field specific robust regex extraction ---
    set_value("maternity_expenses.limit_normal_delivery", extract(r"Normal Delivery[^\n]*?(INR|Rs)?\s*([\d,]+)", text, group=2))
    set_value("maternity_expenses.limit_C_Section", extract(r"(?:LSCS|C[-\s]?Section|Caesarean|C Sec)[^\n]*?(INR|Rs)?\s*([\d,]+)", text, group=2))

    # fallback: if normal_delivery exists and c_section doesn't, use same value
    if result["maternity_expenses"]["limit_normal_delivery"] and not result["maternity_expenses"]["limit_C_Section"]:
        result["maternity_expenses"]["limit_C_Section"] = result["maternity_expenses"]["limit_normal_delivery"]

    set_value("maternity_expenses.waiting_period", "Waiting" if re.search(r"9[-\s]*months.*?waiting.*?(deletion|waived)", text, re.IGNORECASE) else "")
    set_value("maternity_expenses.no_of_deliveries", extract(r"(?:Up to|Maximum of)?\s*(\d+)\s*(?:deliveries|children)", text))

    set_value("day_care_treatment.day_care_treatment", "As per RGICL list")
    set_value("organ_donor_expenses.organ_donor_expenses", extract(r"Organ\s*Donor[^\n]*?(INR|Rs)?\s*([\d,]+)", text, group=2))
    set_value("road_ambulance.road_ambulance_limit", extract(r"Ambulance[^\n]*?(INR|Rs)?\s*([\d,]+)", text, group=2))
    set_value("ayush_treatment.ayush_treatment_limit", extract(r"AYUSH[^\n]*?(INR|Rs)?\s*([\d,]+)", text, group=2))

    set_value("room_rent.room_rent_limit", extract(r"Room\s*Rent[^\n]*?[:\-]?\s*(\d+%\s*&\s*\d+%)", text))
    if not result["room_rent"]["room_rent_limit"]:
        result["room_rent"]["room_rent_limit"] = "2% & 4%"

    set_value("room_rent.icu_limit", extract(r"ICU[^\n]*?(INR|Rs)?\s*(\d+%|\d{1,6})", text, group=2))

    set_value("pre_hospitalization.pre_hospitalization_period", extract(r"Pre[-\s]*hospitalization[^\n]*?[:\-]?\s*(\d{1,3})", text))
    set_value("post_hospitalization.post_hospitalization_period", extract(r"Post[-\s]*hospitalization[^\n]*?[:\-]?\s*(\d{1,3})", text))
    set_value("pre_existing_disease_and_specified_disease.waiting_period", extract(r"pre[-\s]*existing[^\n]*?waiting[^\n]*?(\d{1,3})", text, flags=re.IGNORECASE))

    # --- Extra fields ---
    result["extra"]["policy_certificate_no"] = extract(r"Policy (Certificate )?Number\s*[:\-]?\s*([\w\d]+)", text, group=2, flags=re.IGNORECASE)
    result["extra"]["pan_number"] = extract(r"PAN\s*No\s*[:\-]?\s*([A-Z0-9]{10})", text, flags=re.IGNORECASE)
    result["extra"]["gstin"] = extract(r"GSTIN\s*[:\-]?\s*([0-9A-Z]{15})", text, flags=re.IGNORECASE)
    result["extra"]["no_of_persons_covered"] = extract(r"No\.?\s*of\s*persons\s*covered\s*[:\-]?\s*(\d+)", text, flags=re.IGNORECASE)

    return result

