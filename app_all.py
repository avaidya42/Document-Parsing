from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import aiofiles
import json
import pdfplumber
import uuid
import os

# Import all the parser modules from main.py
from reliance_module import parse_reliance_pdf
from parse_tataaig_pdf import parse_tata_aig_pdf_text
from parse_new_india_pdf import parse_new_india_pdf_text
from parse_carehealth_pdf import final_parser_carehealth
from parse_NivaBupa_format import final_parser_nivabupa
from parse_SBIgeneralinsurance_format import final_parser_SBIgeneral
from aditya_parser import parse_aditya
from digit_parser import parse_digit_pdf
from icici_parser import parse_icici

# Import Bajaj-specific modules from app_cpu.py
from parsing_utils import extract_text_with_coordinates, find_heading_coordinates, \
    extract_text_near_heading, get_headings, output, table_loader_first
from prompt_utils import prompt_field_unmatched_policy
from utils import rec_modifier

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def detect_insurer(text: str) -> str:
    """Detect insurer from PDF text content"""
    upper_text = text.upper()
    if "RELIANCE GENERAL INSURANCE" in upper_text:
        return "reliance"
    elif "POLICYACTIVEWITHBAJAJALLIANZ" in upper_text or "POLICY ACTIVE WITH BAJAJ ALLIANZ" in upper_text:
        return "bajaj"
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


async def parse_bajaj_pdf(pdf_path: str):
    """Parse Bajaj PDF using the existing logic from app_cpu.py"""
    actual_headings = get_headings()

    text_with_coords = extract_text_with_coordinates(pdf_path)
    unstructured_text = ""
    con = False
    con2 = False

    for i in range(max(text_with_coords.keys()) + 1):
        for item in text_with_coords[i]:
            if not con:
                if "claim conditions" == item['text'].lower():
                    con = True
                    unstructured_text += item['text'] + "\n"
            else:
                if "quote disclaim" in item['text'].lower():
                    pass
                unstructured_text += item['text'] + "\n"
        if con2:
            break

    heading_coords = find_heading_coordinates(text_with_coords, actual_headings)
    actual_headings = get_headings()
    extracted_data = extract_text_near_heading(text_with_coords, actual_headings, heading_coords)

    result = extracted_data  # redundancy from legacy result modification TODO remove
    print(result)
    maternity_expense = result["Max liability on maternity exp"]
    room_restrictions = result["Room Restrictions"]
    llm_out = eval(prompt_field_unmatched_policy(unstructured_text, maternity_expense, room_restrictions))
    print(llm_out)
    rel_cov_table = table_loader_first(pdf_path)
    result["relations"] = []
    for _, row in rel_cov_table.iterrows():
        result["relations"].append(row["Relation"])
        if row['Relation'] == "EMPLOYEES":
            llm_out["co_pay"]["policy_co_payment_factor"] = row["Percentage"]
            if row['Pre-Existing Diseases'] == "Covered":
                llm_out["pre_existing_disease_and_specified_disease"] = {
                    "pre_existing_disease_and_specified_disease_waiting_period": "Waived Off"}
            else:
                llm_out["pre_existing_disease_and_specified_disease"] = {
                    "pre_existing_disease_and_specified_disease_waiting_period": "Applicable"}
        elif row['Relation'] == "CHILD":
            llm_out["maternity_expenses"]["no_of_deliveries"] = row["Limit on Number of children"]

    llm_out["maternity_expenses"]["limit_normal_delivery"] = result["Max for normal delivery"]
    llm_out["maternity_expenses"]["limit_C_Section"] = result["Max for LSCS"]
    if "not" in result["9 Months waiting period"].lower():
        llm_out["maternity_expenses"]["waiting_period"] = "No waiting period"
    else:
        llm_out["maternity_expenses"]["waiting_period"] = "9 Months waiting period"
    llm_out["pre_hospitalization"] = {"pre_hospitalization_period": result["Pre Hospitalization Period[Days]"]}
    llm_out["post_hospitalization"] = {"post_hospitalization_period": result["Post Hospitalization Period[Days]"]}

    llm_out = llm_out | {"headings": result}
    rec_modifier(llm_out)
    output(llm_out)

    return llm_out


@app.post("/v2/pdf_parsing_all")
async def pdf_parser_all(user_id: str, agent_name: str, file: UploadFile = File(...)):
    """Parse PDF for all supported insurers"""
    try:
        # Generate unique filename to avoid conflicts
        file_id = str(uuid.uuid4())
        pdf_path = f"temp_file_{file_id}.pdf"

        # Save uploaded file
        async with aiofiles.open(pdf_path, "wb") as output_file:
            content = await file.read()
            await output_file.write(content)

        # Extract text and detect insurer
        pdf_text = extract_text_from_pdf(pdf_path)
        insurer = detect_insurer(pdf_text)

        if insurer == "unknown":
            raise HTTPException(status_code=500, detail="Insurer not recognized. Please check the document.")

        # Parse based on detected insurer
        if insurer == "reliance":
            result = parse_reliance_pdf(pdf_path)
        elif insurer == "bajaj":
            result = await parse_bajaj_pdf(pdf_path)
        elif insurer == "tata_aig":
            result = parse_tata_aig_pdf_text(pdf_text)
        elif insurer == "new_india":
            result = parse_new_india_pdf_text(pdf_text)
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
            raise HTTPException(status_code=500, detail=f"{insurer} - Insurer not recognized. Please check the document.")

        # Save result to JSON file
        output_filename = f"output_{file_id}.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

        # Clean up temporary PDF file
        try:
            os.remove(pdf_path)
        except:
            pass

        # Add metadata to result
        metadata = {
            "insurer": insurer,
            "user_id": user_id,
            "agent_name": agent_name,
            "file_id": file_id
        }

        return result | metadata

    except Exception as e:
        # Clean up temporary files in case of error
        try:
            if 'pdf_path' in locals():
                os.remove(pdf_path)
        except:
            pass

        return {"error": f"Encountered exception: {str(e)}"}


@app.get("/v2/download_result/{file_id}")
async def download_result(file_id: str):
    """Download the parsed result as JSON file"""
    try:
        filename = f"output_{file_id}.json"
        if os.path.exists(filename):
            return FileResponse(
                path=filename,
                filename=filename,
                media_type='application/json'
            )
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


@app.get("/v2/supported_insurers")
async def get_supported_insurers():
    """Get list of supported insurers"""
    return {
        "supported_insurers": [
            "reliance",
            "bajaj",
            "tata_aig",
            "new_india",
            "carehealth",
            "nivabupa",
            "sbigeneral",
            "aditya",
            "icici",
            "digit"
        ],
        "total_count": 10
    }
