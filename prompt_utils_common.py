from utils_common import get_completion_json, text_space_cleaner,output_template
from output_schema_common import OutputFull

def generate_llm_prompt(unstructured_text: str):
    template = output_template(incl_headings=True)  # use True if you want extra hints
    return [
        {
            "role": "system",
            "content": f"""
            You are an AI assistant that extracts structured insurance policy information from raw text. 
            Only fill values based on actual presence in the document.
            Here is the expected JSON format: {template}
            """
        },
        {"role": "user", "content": unstructured_text}
    ]


def get_llm_output(text: str):
    messages = generate_llm_prompt(text)
    return get_completion_json(messages, schema_format=OutputFull)
