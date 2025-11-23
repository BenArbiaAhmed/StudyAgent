from langchain_groq import ChatGroq
from dotenv import load_dotenv


load_dotenv()
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.5,
    max_tokens=1000,
    # reasoning_format="parsed",
    timeout=10,
    max_retries=2,
)

# ### Invoke ###
# messages = [
#     (
#         "system",
#         "You are a helpful assistant that knows everything about animals.",
#     ),
#     ("human", "Why do parrots talk ?"),
# ]
# ai_msg = llm.invoke(messages)
# print(ai_msg)

# ### Stream ###
# for chunk in llm.stream("Why do parrots have colorful feathers?"):
#     print(chunk.text, end="", flush=True)

# full = None  # None | AIMessageChunk
# for chunk in llm.stream("What color is the sky?"):
#     full = chunk if full is None else full + chunk
#     print(full.text)

# print(full.content_blocks)


# ### Batch ###
# responses = llm.batch([
#     "Why do parrots have colorful feathers?",
#     "How do airplanes fly?",
#     "What is quantum computing?"
# ])
# for response in responses:
#     print(response)

### Batch as completed ###
# for response in llm.batch_as_completed([
#     "Why do parrots have colorful feathers?",
#     "How do airplanes fly?",
#     "What is quantum computing?"
# ]):
#     print(response)