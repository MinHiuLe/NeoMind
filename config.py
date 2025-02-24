# config.py
import google.generativeai as genai
import streamlit as st

def configure_api(api_key):
    try:
        genai.configure(api_key=api_key)
        genai.list_models()  # Verify API connection
    except Exception as e:
        st.error(f"❌ Invalid API Key: {str(e)}. Please enter a valid API Key.")
        st.session_state.api_key = ""  # Reset key để yêu cầu nhập lại
        return False
    return True

