from google import genai
import pathlib
from google.genai import types
from prompts.task_prompts.pdf_content_extraction import PROMPT
from dotenv import load_dotenv
import os
from langchain.tools import tool

load_dotenv()
genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@tool
def summarize_pdf(file_path: str) -> str:
    """
    Extract the content of a PDF document.
    
    Args:
        file_path: Path to the PDF file to parse
        
    Returns:
        Content of the document
    """
    try:
        filepath = pathlib.Path(file_path)
        
        if not filepath.exists():
            return f"Error: File {file_path} not found"
        
        prompt = PROMPT
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=filepath.read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
        return response.text
    except Exception as e:
        return f"Error processing PDF: {str(e)}"