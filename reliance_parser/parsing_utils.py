import pdfplumber
import re
from prompt_utils import prompt_field_unmatched_policy
from openai import OpenAI



def extract_policy_text(pdf_path: str, max_pages: int = 3) -> str:
    """
    Extracts and cleans the first few pages of an insurance policy PDF.
    Filters out employee/member data, fixes line breaks, and merges the content.
    """
    relevant_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            text = page.extract_text()
            if not text:
                continue

            # Skip employee/member sections
            if "EMPLOYEE DETAILS" in text.upper() or "MEMBER DETAILS" in text.upper():
                continue

            # Clean formatting
            clean_text = re.sub(r'-\n', '', text)  # fix hyphenated line breaks
            clean_text = re.sub(r'\n', ' ', clean_text)  # flatten newlines
            relevant_text.append(clean_text.strip())

    return "\n".join(relevant_text)


def parse_reliance_pdf(pdf_path: str) -> dict:
    """
    Parses an insurance policy PDF (Reliance format) and returns structured JSON output.
    """
    # Step 1: Extract the policy text
    policy_text = extract_policy_text(pdf_path)

    # Step 2: Known config for Reliance
    maternity_expense = "₹60,000"
    room_restrictions = "2% of SI for normal, 4% of SI for ICU"

    # Step 3: Use LLM to extract structured fields
    json_output = prompt_field_unmatched_policy(
        data=policy_text,
        maternity_expense=maternity_expense,
        room_restrictions=room_restrictions,
        insurer="reliance"
    )

    return json_output
