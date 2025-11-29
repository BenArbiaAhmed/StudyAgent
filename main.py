import streamlit as st
import os
import tempfile
from dotenv import load_dotenv
from agents.supervisor_agent import *
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from tools.analyzer_tools.pdf_loader import extract_pdf_content
from tools.analyzer_tools.semantic_search import setup_rag_from_text, create_retrieve_context_tool

load_dotenv()

st.set_page_config(page_title="Study Agent", layout="wide")
st.title("Intelligent Study Agent")


@st.cache_resource
def get_graph():
    workflow = StateGraph(SupervisorState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("analyzer", analyzer_node)    
    workflow.add_node("rag", rag_node)
    workflow.add_node("flashcards", flashcards_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        decide_next_agent,
        {
            "analyzer": "analyzer",
            "rag": "rag",
            "flashcards": "flashcards",
            "end": END
        }
    )

    workflow.add_edge("analyzer", END)
    workflow.add_edge("rag", END)
    workflow.add_edge("flashcards", END)

    return workflow.compile()

supervisor_app = get_graph()


with st.sidebar:
    st.header("Document Source")
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    
    if uploaded_file:
        if "current_file" not in st.session_state or st.session_state["current_file"] != uploaded_file.name:
            with st.spinner("Processing PDF..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    markdown_text = extract_pdf_content(tmp_path)
                    
                    # --- RAG Setup using Text Content ---
                    st.session_state["pdf_content"] = markdown_text
                    st.session_state["current_file"] = uploaded_file.name
                    
                    # Use the new function to create the vector store from the extracted text
                    current_vector_store = setup_rag_from_text(
                        document_text=markdown_text,
                        document_source=uploaded_file.name,
                        collection_name=uploaded_file.name.replace(".", "_")
                    )
                    
                    st.session_state["vector_store"] = current_vector_store 
                    
                    st.success("PDF Processed and RAG Context Ready! 🎉")
                    
                except Exception as e:
                    st.error(f"Error processing PDF: {e}")
                finally:
                    os.remove(tmp_path)
    
    if "pdf_content" in st.session_state:
        st.info(f"Loaded: {len(st.session_state['pdf_content'])} characters")
    else:
        st.warning("No PDF loaded. RAG and Flashcards may not work correctly.")

    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question or request flashcards..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = []
    for m in st.session_state.messages:
        if m["role"] == "user":
            history.append(HumanMessage(content=m["content"]))
        else:
            history.append(AIMessage(content=m["content"]))

    initial_state = {
        "messages": history,
        "pdf_markdown": st.session_state.get("pdf_content", ""),
        "vector_store": st.session_state.get("vector_store"),
        "next": "supervisor"
    }

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        status_placeholder = st.status("Routing request...", expanded=True)
        
        final_response = ""
        last_agent = ""
        
        try:
            for chunk in supervisor_app.stream(initial_state, stream_mode="values"):
                if "next" in chunk:
                    current_step = chunk["next"]
                    if current_step != "end":
                        status_placeholder.write(f"Agent working: **{current_step}**...")
                        last_agent = current_step
                
                if "messages" in chunk:
                    last_msg = chunk["messages"][-1]
                    
                    if isinstance(last_msg, AIMessage):
                        final_response = last_msg.content
                        
            status_placeholder.update(label="Complete", state="complete", expanded=False)

            response_placeholder.markdown(final_response) 
        
            st.session_state.messages.append({"role": "assistant", "content": final_response})

        except Exception as e:
            status_placeholder.update(label="Error", state="error")
            st.error(f"An error occurred: {e}")