import sys
import json
import pdfplumber

from reliance_module import final_parser_reliance 
from parse_tataaig_pdf import final_parser_tata
from parse_new_india_pdf import final_parser_new_india
from parse_carehealth_pdf import final_parser_carehealth
from parse_NivaBupa_format import final_parser_nivabupa
from parse_SBIgeneralinsurance_format import final_parser_SBIgeneral
from aditya_parser import parse_aditya
from digit_parser import parse_digit_pdf
from icici_parser import parse_icici

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def detect_insurer(text: str) -> str:
    upper_text = text.upper()
    if "RELIANCE GENERAL INSURANCE" in upper_text:
        return "reliance"
    elif "TATA AIG" in upper_text or "TATA A.I.G." in upper_text:
        return "tata_aig"
    elif "NEW INDIA ASSURANCE" in upper_text:
        return "new_india"
    elif "CARE HEALTH INSURANCE LIMITED" in upper_text:
        return "carehealth"
    elif "NIVA BUPA" in upper_text:
        return "nivabupa"
    elif "SBI GENERAL" in upper_text:
        return "sbigeneral"
    elif "ADITYA BIRLA" in upper_text:
        return "aditya"
    elif "ICICI LOMBARD" in upper_text:
        return "icici"
    elif "DIGIT INSURANCE" in upper_text or "GO DIGIT" in upper_text or "DIGIT HEALTH" in upper_text:
        return "digit"
    else:
        return "unknown"

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_pdf>")
        return

    pdf_path = sys.argv[1]
    pdf_text = extract_text_from_pdf(pdf_path)
    insurer = detect_insurer(pdf_text)

    if insurer == "reliance":
        result = final_parser_reliance(pdf_path)  
    elif insurer == "tata_aig":
        result = final_parser_tata(pdf_path)
    elif insurer == "new_india":
        result = final_parser_new_india(pdf_path)
    elif insurer == "carehealth":
        result = final_parser_carehealth(pdf_path)
    elif insurer == "nivabupa":
        result = final_parser_nivabupa(pdf_path)
    elif insurer == "sbigeneral":
        result = final_parser_SBIgeneral(pdf_path)
    elif insurer == "aditya":
        result = parse_aditya(pdf_path)
    elif insurer == "icici":
        result = parse_icici(pdf_path)
    elif insurer == "digit":
        result = parse_digit_pdf(pdf_path)
    else:
        print("❌ Insurer not recognized. Please check the document.")
        return

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"✅ {insurer.upper()} output saved to output.json")

if __name__ == "__main__":
    main()

