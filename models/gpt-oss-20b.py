from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="gpt-oss:20b-cloud",
    temperature=0.5,
)

messages = [
    (
        "system",
        "You are a helpful assistant that translates English to French. Translate the user sentence.",
    ),
    ("human", "I love programming."),
]
ai_msg = llm.invoke(messages)
print(ai_msg)

# gpt-oss-20b