import pdfplumber
import re
from prompt_utils import prompt_field_unmatched_policy

from dotenv import load_dotenv
import os   

load_dotenv(dotenv_path='api.env')  # 👈 Explicitly load api.env
api_key = os.getenv("OPENAI_API_KEY")

from openai import OpenAI
client = OpenAI(api_key=api_key)

def extract_policy_text(pdf_path: str, max_pages: int = 3) -> str:
    relevant_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            text = page.extract_text()
            if not text:
                continue
            if "EMPLOYEE DETAILS" in text.upper() or "MEMBER DETAILS" in text.upper():
                continue

            clean_text = re.sub(r'-\n', '', text)
            clean_text = re.sub(r'\n', ' ', clean_text)
            relevant_text.append(clean_text.strip())

    return "\n".join(relevant_text)


def parse_reliance_pdf(pdf_path: str) -> dict:
    # Step 1: Extract clean policy-level content
    policy_text = extract_policy_text(pdf_path)

    # Step 2: Define known Reliance-specific config
    maternity_expense = "₹60,000"
    room_restrictions = "2% of SI for normal, 4% of SI for ICU"

    # Step 3: Call LLM to extract fields
    json_output = prompt_field_unmatched_policy(
        data=policy_text,
        maternity_expense=maternity_expense,
        room_restrictions=room_restrictions,
        insurer="reliance"
    )

    return json_output
