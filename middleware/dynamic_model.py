from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from dotenv import load_dotenv

load_dotenv()


basic_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.5,
    max_tokens=1000,
    timeout=10,
    max_retries=3,)

advanced_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.5,
    max_tokens=1000,
    timeout=10,
    max_retries=3,)

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """Choose model based on conversation complexity."""
    message_count = len(request.state["messages"])

    if message_count > 10:
        # Use an advanced model for longer conversations
        model = advanced_model
    else:
        model = basic_model

    request.model = model
    return handler(request)