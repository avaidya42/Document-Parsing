from openai import OpenAI

client = OpenAI()  # make sure your OPENAI_API_KEY is set in environment variables

def get_completion_from_messages(messages, model="gpt-4o-mini", temperature=0):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content
