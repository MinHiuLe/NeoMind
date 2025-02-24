import streamlit as st
import pymongo
import datetime
from config import configure_api
from chain_setup import create_chain, GEMINI_MODEL
import os

# Set page configuration with theme
st.set_page_config(
    page_title="NeoMind",
    page_icon="🐈",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Hàm để load file CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load file styles.css
local_css("styles.css")

#---------------------------------MONGODB---------------------------------
MONGODB_URI = os.getenv("MONGODB_URI")
client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=30000)
db = client["NeoMind"]
chat_collection = db["Chat_Session"]

try:
    client.admin.command('ping')
    #st.success("Connected to MongoDB!")
except Exception as e:
    st.error(f"MongoDB connection failed: {e}")
    raise e

def save_chat_session(title, messages):
    session_doc = {
        "title": title,
        "messages": messages,
        "created_at": datetime.datetime.utcnow()
    }
    result = chat_collection.insert_one(session_doc)
    return result.inserted_id

def update_chat_session(session_id, messages):
    chat_collection.update_one({"_id": session_id}, {"$set": {"messages": messages}})

def load_chat_sessions():
    return list(chat_collection.find().sort("created_at", -1))

st.title("🐈 NeoMind: AI Research")

if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")

if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How can I help you today?"}]
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None

with st.sidebar:
    st.header("🐈 NeoMind")
    
    if st.button("💬 New Chat", key="new_chat"):
        default_msg = [{"role": "assistant", "content": "How can I help you today?"}]
        if st.session_state.messages != default_msg:
            first_user_msg = next((msg["content"] for msg in st.session_state.messages if msg["role"] == "user"), None)
            title = first_user_msg if first_user_msg else "Untitled Chat"
            if st.session_state.current_session_id is not None:
                update_chat_session(st.session_state.current_session_id, st.session_state.messages)
            else:
                new_id = save_chat_session(title, st.session_state.messages)
                st.session_state.current_session_id = new_id
        st.session_state.messages = [{"role": "assistant", "content": "How can I help you today?"}]
        st.session_state.current_session_id = None
    
    st.subheader("Saved Sessions")
    sessions = load_chat_sessions()
    max_title_length = 25
    for session in sessions:
        title = session.get("title", "Untitled Chat")
        if len(title) > max_title_length:
            title = title[:max_title_length] + "..."
        if st.button(title, key=str(session["_id"])):
            st.session_state.messages = session["messages"]
            st.session_state.current_session_id = session["_id"]

if st.session_state.api_key:
    try:
        configure_api(st.session_state.api_key)
        if "chain" not in st.session_state:
            st.session_state.chain = create_chain(st.session_state.api_key)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(f'<div class="custom-card new-message">{msg["content"]}</div>', unsafe_allow_html=True)

        if prompt := st.chat_input("💬 Ask me anything..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            
            with st.spinner("🐈 NeoMind Processing..."):
                try:
                    response = st.session_state.chain.run(question=prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.chat_message("assistant").write(response)
                except Exception as e:
                    st.error(f"⚠️ Error: {str(e)}")
                    st.session_state.messages.pop()  

    except Exception as e:
        st.error(f"❌ Configuration Error: {str(e)}")
else:
    st.warning("🔑 Please enter your Gemini API Key in the sidebar to start")
