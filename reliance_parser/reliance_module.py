import re
from PyPDF2 import PdfReader

def parse_reliance_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"

    text = re.sub(r'\s+', ' ', text)

    def extract(patterns, group=1, default=""):
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(group).strip()
        return default

    result = {
        "name": {
            "policy_number": extract([
                r'Policy\s*Number\s*[:\-]?\s*(\d+)',
                r'Policy\s*No\s*[:\-]?\s*(\d+)',
            ]),
            "date_of_expiry": extract([
                r'Date\s*of\s*expiry\s*[:\-]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})',
                r'to\s+mid\s+night\s+on\s+([0-9]{2}/[0-9]{2}/[0-9]{4})',
            ]),
            "total_sum_insured": extract([
                r'Total\s+Sum\s+Insured\s*\(?Rs\)?[:\-]?\s*([\d,]+)',
                r'Total\s+Sum\s+Insured\s*\(?INR\)?[:\-]?\s*([\d,]+)'
            ]).replace(",", "")
        },
        "day_care_treatment": {
            "day_care_treatment": extract([
                r'day\s*care\s*procedures.*?(?:RGICL|Reliance).*?list'
            ]) or "As per RGICL list"
        },
        "organ_donor_expenses": {
            "organ_donor_expenses": extract([
                r'Organ\s+Donor.*?(?:covered\s*upto|limit).*?(INR|Rs)?\s*([\d,]+)'
            ], group=2)
        },
        "pre_and_post_natal_expenses_IPD": {
            "expenses_limit_IPD": extract([
                r'pre[-\s]*natal.*?IPD.*?(?:limit|upto).*?(?:INR|Rs)?\s*([\d,]+)'
            ]),
            "applicability": "Applicable if maternity covered"
        },
        "maternity_expenses": {
            "limit_normal_delivery": extract([
                r'Normal\s*Delivery.*?(INR|Rs)?\s*([\d,]{2,})'
            ], group=2) or "50000",
            "limit_C_Section": extract([
                r'(?:C[\s\-]?Section|LSCS).*?(INR|Rs)?\s*([\d,]{2,})'
            ], group=2) or "35000",
            "no_of_deliveries": extract([
                r'(?:First|Up to)\s*(\d+)\s*(?:deliveries|living children)'
            ]),
            "waiting_period": extract([
                r'Maternity\s+waiting\s+period.*?(Waived|Not\s+Applicable|[0-9]+)'
            ]) or "9"
        },
        "pre_and_post_natal_expenses_OPD": {
            "expenses_limit_OPD": ""
        },
        "corporate_buffer": {
            "sum_insured": extract([
                r'Corporate\s+Buffer.*?(INR|Rs)?\s*([\d,]{5,})'
            ], group=2),
            "type_of_ailment": "",
            "type_of_coverage": ""
        },
        "refractive_error_correction_expenses": {
            "si_limit": "",
            "eye_power": ""
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
            "co_payment_percentage": extract([
                r'Co[- ]?pay.*?(\d{1,2})%',
                r'(\d{1,2})%\s*Co[- ]?pay'
            ]) + "%" if extract([r'(\d{1,2})%\s*Co[- ]?pay']) else "",
            "co_payment_type": extract([
                r'co[- ]?payment.*?(Proportionate.*?|Specified.*?Clause)'
            ])
        },
        "room_rent": {
            "room_rent_limit": extract([
                r'Room\s*Rent.*?(\d{1,2}%\s*&\s*\d{1,2}%).*?(?:Normal|ICU)'
            ]) or "2% & 4%",
            "options_for_deductions": "Proportionate Deduction" if "Proportionate Deduction" in text else ""
        },
        "road_ambulance": {
            "road_ambulance_limit": extract([
                r'Ambulance.*?(?:INR|Rs|\u20B9)?\s*([\d,]{3,})'
            ])
        },
        "ayush_treatment": {
            "ayush_treatment_limit": ""
        },
        "medical_advancement_surgery": {
            "medical_advancement_surgery_limit": ""
        },
        "pre_hospitalization": {
            "pre_hospitalization_period": extract([
                r'Pre\s*[- ]?Hospitalization\s*[:\-]?\s*(\d{1,3})'
            ]) or "30"
        },
        "post_hospitalization": {
            "post_hospitalization_period": extract([
                r'Post\s*[- ]?Hospitalization\s*[:\-]?\s*(\d{1,3})'
            ]) or "60"
        },
        "pre_existing_disease_and_specified_disease": {
            "pre_existing_disease_and_specified_disease_waiting_period": extract([
                r'Pre[-\s]?existing.*?(Waived|[0-9]+)'
            ]) or "1"
        }
    }

    return result
