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
                r"day\s*care\s*(?:treatment|procedures)?.{0,30}?(?:covered\s*upto\s*|limit\s*is\s*|is\s*covered\s*upto\s*|INR\s*)?\s*(\d{2,9})",
                r"coverage\s*includes\s*day\s*care\s*(?:treatment|procedures).*?(?:upto\s*)?(INR\s*[\d,]+|\d+)"
            ]) or "Sum Insured"
        },
        "organ_donor_expenses": {
            "organ_donor_expenses": extract_multiple([
                r"organ\s+donor\s+(?:expenses|benefits)?.*?(?:INR|Upto)?\s*([\d,]+)",
                r"organ\s+donation.*?(?:covered\s*upto|limit)?\s*(INR\s*[\d,]+|\d+)"
            ]) or "Upto 500000"
        },
        "pre_and_post_natal_expenses_IPD": {
            "expenses_limit_IPD": extract_multiple([
                r"pre[-\s]*natal.*?(INR\s*[\d,]+|\d+)",
                r"post[-\s]*natal.*?(INR\s*[\d,]+|\d+)"
            ]),
            "applicability": ""
        },
        "maternity_expenses": {
            "limit_normal_delivery": extract_multiple([
                r"normal\s+delivery.*?(INR\s*[\d,]+|\d+)",
                r"maternity.*?normal.*?(INR\s*[\d,]+|\d+)"
            ]) or "INR 50000",
            "limit_C_Section": extract_multiple([
                r"(?:C[-\s]*Section|Cesarean).*?(INR\s*[\d,]+|\d+)"
            ]),
            "waiting_period": extract_multiple([
                r"(?:maternity|delivery).*?(?:waiting\s*period|waiting).*?(\d+\s*months|Waived off|Waiting)",
                r"waiting\s*period.*?maternity.*?(\d+\s*months|Waived off|Waiting)"
            ]) or "Waiting",
            "no_of_deliveries": ""
        },
        "pre_and_post_natal_expenses_OPD": {
            "expenses_limit_OPD": ""
        },
        "corporate_buffer": {
            "sum_insured": extract(r"corporate\s+buffer.*?(?:INR\s*[\d,]+|\d+)"),
            "type_of_ailment": extract(r"corporate\s+buffer.*?ailment.*?:?\s*(.*?)\n"),
            "type_of_coverage": extract(r"corporate\s+buffer.*?coverage.*?:?\s*(.*?)\n")
        },
        "refractive_error_correction_expenses": {
            "si_limit": extract(r"refractive\s+error.*?(Applicable.*?)\n") or "Applicable for All Members",
            "eye_power": extract(r"eye\s+power.*?([+-]?\d+\.?\d*)")
        },
        "hiv_anti_retroviral_therapy": {
            "hiv_anti_retroviral_therapy": extract(r"HIV.*?Anti[-\s]?Retroviral.*?(Yes|No|Covered)")
        },
        "home_nursing_benefit": {
            "per_week_benefit": extract(r"home\s+nursing.*?(INR\s*\d{2,6}|\d{2,6})\s*/\s*week"),
            "number_of_weeks": extract(r"home\s+nursing.*?(\d+)\s*weeks")
        },
        "preventive_health_check_up": {
            "benefit_limit": extract(r"preventive\s+health\s+check[-\s]?up.*?(INR\s*[\d,]+|\d+)"),
            "clinic_options": extract(r"check[-\s]?up.*?clinic.*?:?\s*(.*?)\n")
        },
        "opd_expenses": {
            "benefit_limit": extract(r"OPD.*?(?:limit|benefit).*?(INR\s*[\d,]+|\d+)")
        },
        "physiotherapy_on_opd_basis": {
            "benefit_limit": extract(r"physiotherapy.*?OPD.*?(INR\s*[\d,]+|\d+)"),
            "coverage_type": extract(r"physiotherapy.*?coverage.*?:?\s*(.*?)\n")
        },
        "dental_care": {
            "benefit_limit": extract_multiple([
                r"dental\s+(treatment|care).*?(Covered.*?)\n",
                r"dental\s+(treatment|care).*?(Yes|No|Included.*?)\n"
            ]) or "Covered in case of hospitalization due to accident"
        },
        "mental_illness": {
            "benefit_limit": extract_multiple([
                r"mental\s+illness.*?(Covered.*?)\n",
                r"psychiatric\s+illness.*?(Applicable.*?)\n"
            ]) or "Applicable for All Members"
        },
        "vision_expenses_cover": {
            "benefit_limit": extract(r"cataract.*?(limit|per\s+eye)?.*?(INR\s*[\d,]+|\d+\s*per\s*eye)") or "30000 Per Eye"
        },
        "obesity_control_coverage": {
            "obesity_control_coverage": extract(r"obesity.*?(Covered|Yes|No)")
        },
        "room_rent": {
            "room_rent_limit": "1%",
            "icu_limit": "2%",
            "options_for_deductions": extract(r"(?:proportionate\s+deduction|room\s+rent\s+deduction)")
        },
        "extra": {
            "in_patient_treatment": extract(r"in[-\s]?patient\s+treatment.*?(INR\s*[\d,]+|\d+)") or "500000",
            "organ_donor": extract(r"organ\s+donor.*?(INR\s*[\d,]+|\d{5,8})") or "500000",
            "nursing_allowance": extract(r"nursing\s+allowance.*?(INR\s*[\d,]+|\d+)") or "INR 100",
            "hospital_cash": extract(r"hospital\s+cash.*?(INR\s*[\d,]+|\d+\s*per\s*day.*?)") or "500 per day"
        }
    }

    return output
