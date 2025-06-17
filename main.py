import sys
import json
import ast
# from reliance_module import parse_reliance_pdf  # Make sure this returns a dict, not a string
import pdfplumber 
from parse_tataaig_pdf import parse_tata_aig_pdf_text
from parse_new_india_pdf import parse_new_india_pdf_text
from parse_carehealth_pdf import final_parser


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
    else:
        return "unknown"

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_pdf>")
        return

    pdf_path = sys.argv[1]
    # result = parse_reliance_pdf(pdf_path)

    # # Safety: convert string dict to real dict if needed
    # if isinstance(result, str):
    #     try:
    #         result = ast.literal_eval(result)
    #     except Exception as e:
    #         print("❌ Error converting string to dict:", e)
    #         return

    # # Save output to JSON file
    # with open("output.json", "w") as f:
    #     json.dump(result, f, indent=4)

    # print("✅ Output saved to output.json")

    pdf_text = extract_text_from_pdf(pdf_path)
    insurer = detect_insurer(pdf_text)

    if insurer == "reliance":
        # result = parse_reliance_pdf_text(pdf_text)
        pass
    elif insurer == "tata_aig":
        result = parse_tata_aig_pdf_text(pdf_text)
    elif insurer == "new_india":
        result = parse_new_india_pdf_text(pdf_text)
    elif insurer == "carehealth":
        result = final_parser(pdf_path)
    else:
        print("❌ Insurer not recognized. Please check the document.")
        return

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"✅ {insurer.upper()} output saved to output.json")


if __name__ == "__main__":
    main()
