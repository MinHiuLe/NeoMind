# chain_setup.py
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

GEMINI_MODEL = "gemini-pro"

def create_chain(api_key):
    system_message = """You are NeoMind - a professional AI Assistant. Your tasks:
    - Provide comprehensive, detailed answers
    - Include explanations and analysis
    - Use examples when necessary
    - Maintain technical accuracy"""
    
    prompt_template = ChatPromptTemplate.from_messages([
        HumanMessagePromptTemplate.from_template(system_message + "\n\nQuestion: {question}")
    ])

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=api_key,
        temperature=0.7
    )

    return LLMChain(
        llm=llm,
        prompt=prompt_template,
        verbose=True
    )