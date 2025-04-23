from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Test the API
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # Use the appropriate model
    messages=[
        {"role": "user", "content": "Write a short story about a robot learning to dance."}
    ],
    max_tokens=50
)

print(response.choices[0].message.content)

