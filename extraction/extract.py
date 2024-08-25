import instructor
from openai import OpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"

client = instructor.from_openai(OpenAI())

def get_messages(data):
    messages_investor_info = [
        {"role": "user", "content": data},
    ]
    return messages_investor_info

def extract_tags(content: str , extr_model: BaseModel):
    messages = get_messages(content)
    # Add a system prompt to guide the model's behavior
    system_prompt = {"role": "system", "content": 
                     "You are a tagging algorithm designed to analyze product descriptions and generate meaningful, categorized tags that improve search navigation and filtering. Each tag should represent a key feature, attribute, or characteristic of the product. Input: "
                     }
    
    # Add the system prompt at the beginning of the messages list
    messages.insert(0, system_prompt)

    # Extract structured data from natural language
    tags, completion = client.chat.completions.create_with_completion(
        temperature=0.0,
        model=MODEL,
        response_model=extr_model, #InvestorInfo,
        messages=messages,
        max_retries=2
    )

    print(f'costs prompt: {completion.usage.prompt_tokens}, completion: {completion.usage.completion_tokens}')
    return tags, completion.usage