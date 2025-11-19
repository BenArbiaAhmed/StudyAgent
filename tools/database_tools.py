from langchain_community.agent_toolkits import SQLDatabaseToolkit

def create_sql_tools(db, model):
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    return toolkit.get_tools()
