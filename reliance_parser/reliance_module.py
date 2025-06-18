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
            "day_care_treatment": extract([r'day\s*care\s*procedures\s*covered\s*as\s*per\s*(RGICL.*?)list'])
        },
        "organ_donor_expenses": {
            "organ_donor_expenses": ""
        },
        "pre_and_post_natal_expenses_IPD": {
            "expenses_limit_IPD": "",
            "applicability": ""
        },
        "maternity_expenses": {
            "limit_normal_delivery": extract([
                r'Normal\s*Delivery\s*[:\-]?\s*Rs\.?\s*([\d,]+)',
                r'Normal\s*Limits[:\-]?\s*Rs\.?\s*([\d,]+)',
                r'Normal\s*Delivery\s*[:\-]?\s*INR\s*([\d,]+)'
            ]),
            "limit_C_Section": extract([
                r'(?:C[\s\-]?Section|LSCS).*?[:\-]?\s*Rs\.?\s*([\d,]+)',
                r'C[-\s]?section\s*Delivery\s*[:\-]?\s*Rs\.?\s*([\d,]+)'
            ]),
            "no_of_deliveries": extract([
                r'first\s+(\d+)\s+(?:delivery|deliveries|living children)'
            ]),
            "waiting_period": extract([
                r'Maternity\s+waiting\s+period.*?(Waived|Not\s+Applicable|[0-9]+)'
            ])
        },
        "pre_and_post_natal_expenses_OPD": {
            "expenses_limit_OPD": ""
        },
        "corporate_buffer": {
            "sum_insured": extract([
                r'Corporate\s+Buffer\s+.*?Rs\.?\s*([\d,]+)'
            ]),
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
            ], default="") + "%" if extract([r'(\d{1,2})%\s*Co[- ]?pay']) else "",
            "co_payment_type": extract([
                r'co[- ]?payment.*?(Proportionate.*?|Specified.*?Clause)'
            ])
        },
        "room_rent": {
            "room_rent_limit": extract([
                r'Room\s*Rent.*?(2%.*?4%.*?)\)',
                r'Room\s*Rent.*?inclusive.*?charges.*?([^\n]+?maximum.*?)\)'
            ]),
            "options_for_deductions": "Proportionate Deduction" if "Proportionate Deduction" in text else ""
        },
        "road_ambulance": {
            "road_ambulance_limit": extract([
                r'Ambulance\s+charges\s+.*?Rs\.?\s*([\d,]+)',
                r'Ambulance.*?(?:INR|₹)?\s*([\d,]+)',
                r'Emergency\s+ambulance\s+(?:INR|₹)?\s*([\d,]+)'
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
            ])
        },
        "post_hospitalization": {
            "post_hospitalization_period": extract([
                r'Post\s*[- ]?Hospitalization\s*[:\-]?\s*(\d{1,3})'
            ])
        },
        "pre_existing_disease_and_specified_disease": {
            "pre_existing_disease_and_specified_disease_waiting_period": extract([
                r'Pre[-\s]?existing.*?(Waived|[0-9]+)'
            ])
        }
    }

    return result
