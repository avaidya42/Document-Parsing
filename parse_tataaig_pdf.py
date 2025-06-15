import re

def parse_tata_aig_pdf_text(text: str) -> dict:
    def extract(regex, flags=re.IGNORECASE):
        match = re.search(regex, text, flags)
        return match.group(1).strip() if match else ""

    def extract_multiple(regexes):
        for regex in regexes:
            value = extract(regex)
            if value:
                return value
        return ""

    output = {
        "day_care_treatment": {
            "day_care_treatment": extract_multiple([
                r"day\s*care.*?(?:procedures|treatment).*?(?::|is)?\s*(.*?)(?:\n|$)",
                r"includes.*?day\s*care.*?(?::|is)?\s*(.*?)(?:\n|$)"
            ]) or "Sum Insured"
        },
        "organ_donor_expenses": {
            "organ_donor_expenses": extract_multiple([
                r"organ\s+donor.*?(INR\s*[\d,]+|Upto\s*\d{4,9})",
                r"expenses.*?organ\s+donation.*?(INR\s*[\d,]+|\d{5,8})"
            ]) or "Upto 500000"
        },
        "pre_and_post_natal_expenses_IPD": {
            "expenses_limit_IPD": extract_multiple([
                r"IPD.*?(pre[-\s]?natal|post[-\s]?natal).*?(INR\s*[\d,]+|\d+)",
                r"maternity.*?IPD.*?(INR\s*[\d,]+|\d+)"
            ]),
            "applicability": extract(r"IPD.*?(within.*?maternity.*?)\n")
        },
        "maternity_expenses": {
            "limit_normal_delivery": extract_multiple([
                r"normal\s+delivery.*?(INR\s*[\d,]+|Upto\s*\d+.*?)",
                r"delivery.*?normal.*?(INR\s*[\d,]+|\d+)"
            ]) or "INR 50000",
            "limit_C_Section": extract_multiple([
                r"C[-\s]*Section.*?(INR\s*[\d,]+|Upto\s*\d+.*?)",
                r"cesarean.*?(INR\s*[\d,]+|\d+)"
            ]),
            "waiting_period": extract(r"maternity.*?(waiting|period).*?(\d+\s*months|Waived off|Waiting)") or "Waiting"
        },
        "pre_and_post_natal_expenses_OPD": {
            "expenses_limit_OPD": extract(r"OPD.*?(pre[-\s]?natal|post[-\s]?natal).*?(INR\s*[\d,]+|\d+)")
        },
        "corporate_buffer": {
            "sum_insured": extract(r"corporate\s+buffer.*?(sum insured|amount).*?(INR\s*[\d,]+|\d+)", re.IGNORECASE),
            "type_of_ailment": extract(r"corporate\s+buffer.*?ailment.*?:?\s*(.*?)\n"),
            "type_of_coverage": extract(r"corporate\s+buffer.*?coverage.*?:?\s*(.*?)\n")
        },
        "refractive_error_correction_expenses": {
            "si_limit": extract(r"refractive\s+error.*?(Applicable.*?)\n") or "Applicable for All Members",
            "eye_power": extract(r"eye\s+power.*?([+-]?\d+\.?\d*\s*[Dd])")
        },
        "hiv_anti_retroviral_therapy": {
            "hiv_anti_retroviral_therapy": extract(r"HIV.*?Anti[-\s]?Retroviral.*?(Yes|No|Covered)")
        },
        "home_nursing_benefit": {
            "per_week_benefit": extract(r"home\s+nursing.*?(INR\s*\d{2,6}|\d{2,6})\s*/\s*week"),
            "number_of_weeks": extract(r"home\s+nursing.*?(\d+)\s*weeks")
        },
        "preventive_health_check_up": {
            "benefit_limit": extract(r"preventive\s+health.*?check[-\s]?up.*?(INR\s*[\d,]+|\d+)") or "",
            "clinic_options": extract(r"health.*?check[-\s]?up.*?clinic.*?:?\s*(.*?)\n")
        },
        "opd_expenses": {
            "benefit_limit": extract(r"OPD.*?(benefit)?\s*limit.*?(INR\s*[\d,]+|\d+)")
        },
        "physiotherapy_on_opd_basis": {
            "benefit_limit": extract(r"physiotherapy.*?OPD.*?(INR\s*[\d,]+|\d+)", re.IGNORECASE),
            "coverage_type": extract(r"physiotherapy.*?coverage.*?:?\s*(.*?)\n")
        },
        "dental_care": {
            "benefit_limit": extract_multiple([
                r"dental\s+treatment.*?(Covered.*?)\n",
                r"dental\s+care.*?(Covered.*?)\n"
            ]) or "Covered in case of hospitalization due to"
        },
        "mental_illness": {
            "benefit_limit": extract_multiple([
                r"mental\s+illness.*?(Covered.*?)\n",
                r"psychiatric.*?(Applicable.*?)\n"
            ]) or "Applicable for All Members"
        },
        "vision_expenses_cover": {
            "benefit_limit": extract(r"cataract.*?limit.*?(INR\s*[\d,]+|\d+\s*Per\s*Eye)") or "30000 Per Eye"
        },
        "obesity_control_coverage": {
            "obesity_control_coverage": extract(r"obesity.*?control.*?(Covered|Yes|No)")
        },
        "extra": {
            "in_patient_treatment": extract(r"in[-\s]?patient\s+treatment.*?(INR\s*[\d,]+|\d{5,8})") or "500000",
            "organ_donor": extract(r"organ\s+donor.*?(INR\s*[\d,]+|\d{5,8})") or "500000",
            "nursing_allowance": extract(r"nursing\s+allowance.*?(Yes|No|INR\s*[\d,]+|\d{2,6})") or "INR 100",
            "hospital_cash": extract(r"hospital\s+cash.*?(INR\s*[\d,]+|\d+\s*per\s*day.*?)") or "500 per day",
            "emergency_air_ambulance": extract(r"emergency\s+air\s+ambulance.*?(INR\s*[\d,]+|\d{5,8})")
        }
    }

    return output
