from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model(
    model="gemini-2.5-flash",
    model_provider="google_genai",
    temperature=0.5,
    timeout=10,
    max_tokens=1000
)