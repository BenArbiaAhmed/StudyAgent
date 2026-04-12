# Study Agent

An intelligent study assistant built with Streamlit and LangGraph. It analyzes uploaded PDFs, performs semantic search (RAG) over document content, and generates helpful outputs such as answers, context summaries, and study flashcards — all orchestrated by a supervisor agent that routes tasks to specialized agents.

The app runs locally in your browser and supports multiple LLM providers via LangChain integrations.

## Features
- Intelligent routing: A `supervisor` coordinates requests across specialized agents.
- PDF ingestion: Extracts and converts PDF content to markdown for downstream processing.
- RAG over documents: Builds a vector store from your uploaded PDF for semantic retrieval.
- Flashcards generation: Produces concise Q/A cards to reinforce learning.
- Conversational UI: Chat interface using Streamlit with message history.
- Pluggable models: Use OpenAI, Gemini, Groq, Ollama, and more via LangChain.

## Architecture
- **Frontend**: Streamlit chat interface in [main.py](main.py).
- **Workflow Orchestration**: LangGraph `StateGraph` compiled from agent nodes.
- **Agents**: Located in [agents/](agents/)
	- `supervisor_agent.py`: decides the next agent (`analyzer`, `rag`, `flashcards`, `end`).
	- `analyzer_agent.py`: analyzes content/questions.
	- `rag_agent.py`: retrieves context from the vector store and answers questions.
	- `supervisor_agent.py` also exposes `flashcards_node` for study card generation.
- **Tools**: In [tools/analyzer_tools/](tools/analyzer_tools/)
	- `pdf_loader.py`: PDF → markdown extraction.
	- `semantic_search.py`: builds vector store from text and retrieval helpers.
- **Prompts & Response Formats**: Under [prompts/](prompts/) and [response_format/](response_format/).
- **Memory & Workflows**: In [memory/](memory/) and [workflows/](workflows/), including flashcards state/workflow.

## Requirements
- Python 3.11+ recommended.
- Windows, macOS, or Linux. Tested on Windows.
- Optional external dependencies for OCR/PDF (e.g., Tesseract) depending on your PDFs.

## Setup
1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies from `requirements.txt`.
4. Create a `.env` with your API keys as needed.

### Example commands (Windows PowerShell)
```powershell
# From the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# (Optional) Verify Streamlit installed
streamlit --version
```

### Environment variables
Create a `.env` file in the project root to configure model providers. Common variables include:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `GROQ_API_KEY`
- `OLLAMA_BASE_URL` (if using local Ollama)
- `FIRECRAWL_API_KEY` (optional, enables full webpage scraping in the analyzer agent)

Only set the providers you plan to use. The app loads `.env` via `python-dotenv`.

## Running the App
Start the Streamlit app and open it in your browser.

```powershell
streamlit run main.py
```

Then:
- Use the sidebar to upload a PDF.
- Wait for "PDF Processed and RAG Context Ready!".
- Ask questions or request flashcards in the chat box.

## Usage Notes
- When a PDF is uploaded, the app extracts text to markdown and initializes a vector store for RAG.
- The supervisor agent chooses whether your prompt should be handled by `analyzer`, `rag`, or `flashcards`.
- If no PDF is loaded, RAG/flashcards may be limited; you’ll see a sidebar warning.

## Project Structure
Key files and folders:
- [main.py](main.py): Streamlit UI, graph compilation, chat loop.
- [agents/](agents/): Agent nodes and routing logic.
- [tools/analyzer_tools/](tools/analyzer_tools/): PDF extraction and semantic search utilities.
- [prompts/](prompts/), [response_format/](response_format/): Prompt templates and structured outputs.
- [memory/](memory/), [workflows/](workflows/): State and workflows (e.g., flashcards).
- [data/chroma_langchain_db/](data/chroma_langchain_db/): Vector store artifacts (managed by the app).

## Configuration & Models
Model selection and prompts are modularized in [models/](models/) and [prompts/](prompts/). You can:
- Add or adjust model wrappers (OpenAI, Gemini, Groq, Ollama) under [models/](models/).
- Tune system prompts in [prompts/system_prompts/](prompts/system_prompts/).

## Troubleshooting
- PDF not processing:
	- Ensure the file is a valid PDF.
	- Some PDFs may need OCR; install `pytesseract` and Tesseract if required.
- No responses or API errors:
	- Check your `.env` credentials and provider rate limits.
- Vector store issues:
	- Clear the `data/chroma_langchain_db/` directory if corrupted; re-upload the PDF.
- Streamlit cache quirks:
	- Use the sidebar "Clear Conversation" to reset the session.

## Development
- Run Streamlit in debug mode with `--logger.level=debug` to see more logs.
- Modify agents or prompts, then refresh the Streamlit app.
- Keep changes focused and consistent with existing abstractions.

## License
This project is for educational purposes. Add a license file if you intend to distribute.
