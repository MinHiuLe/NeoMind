import streamlit as st
import pymongo
import datetime
import bcrypt
import smtplib
from config import configure_api
from chain_setup import create_chain, GEMINI_MODEL
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="NeoMind",
    page_icon="🐈",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Hàm load file CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("styles.css")

# Kết nối MongoDB (sử dụng st.secrets để quản lý thông tin nhạy cảm)
MONGODB_URI = st.secrets["MONGODB_URI"]
try:
    client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=30000)
    db = client["NeoMind"]
    chat_collection = db["Chat_Session"]
    users_collection = db["Users"]
    client.admin.command('ping')
    logging.info("Connected to MongoDB!")
except Exception as e:
    st.error(f"MongoDB connection failed: {e}")
    st.stop()

# Tạo unique index cho email và username nếu chưa tồn tại
users_collection.create_index("email", unique=True)
users_collection.create_index("username", unique=True)
# Hàm gửi email cảm ơn sau khi đăng ký
def send_thank_you_email(to_email, username):
    # Lấy cấu hình SMTP từ st.secrets
    smtp_server = st.secrets.get("SMTP_SERVER")
    smtp_port = st.secrets.get("SMTP_PORT")
    email_user = st.secrets.get("EMAIL_USER")
    email_password = st.secrets.get("EMAIL_PASSWORD")
    
    if not all([smtp_server, smtp_port, email_user, email_password]):
        logging.error("SMTP configuration is missing in secrets!")
        return
    
    subject = "Thank You for Registering with NeoMind"
    body = f"""Dear {username},

    Thank you for choosing to join NeoMind. We sincerely appreciate your trust and are delighted to welcome you to our community. At NeoMind, we are committed to providing you with an exceptional experience and innovative solutions that enhance your journey.

    Should you have any questions or require assistance, please do not hesitate to reach out. We are here to support you every step of the way.

    Warm regards,
    HiuLe
    """
    msg = MIMEMultipart()
    msg["From"] = "email_user"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    try:
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(email_user, email_password)
        server.sendmail(email_user, to_email, msg.as_string())
        server.quit()
        logging.info(f"Thank you email sent to {to_email}")
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")

#Function to register user
def register_user(email, username, password):
    if users_collection.find_one({"$or": [{"email": email}, {"username": username}]}):
        return False, "Username or Email has already been taken!"
    # Hashed password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_doc = {
        "email": email,
        "username": username,
        "password": hashed_password,
        "created_at": datetime.datetime.utcnow()
    }
    result = users_collection.insert_one(user_doc)
    if result.inserted_id:
        return True, "Register successfully!"
    return False, "Register failed!"

# Hàm đăng nhập người dùng
def login_user(username_or_email, password):
    user = users_collection.find_one({"$or": [{"email": username_or_email}, {"username": username_or_email}]})
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        return True, user
    return False, "Invalid login information!"

# Các hàm xử lý phiên chat (đã cập nhật để lưu theo user)
def save_chat_session(title, messages):
    session_doc = {
        "user_id": st.session_state.user["_id"],
        "title": title,
        "messages": messages,
        "created_at": datetime.datetime.utcnow()
    }
    try:
        result = chat_collection.insert_one(session_doc)
        return result.inserted_id
    except Exception as e:
        st.error(f"Failed to save chat session: {str(e)}")
        logging.error(f"Failed to save chat session: {str(e)}")
        return None

def update_chat_session(session_id, messages):
    try:
        chat_collection.update_one({"_id": session_id}, {"$set": {"messages": messages}})
    except Exception as e:
        st.error(f"Failed to update chat session: {str(e)}")
        logging.error(f"Failed to update chat session: {str(e)}")

def load_chat_sessions():
    try:
        return list(chat_collection.find({"user_id": st.session_state.user["_id"]}).sort("created_at", -1))
    except Exception as e:
        st.error(f"Failed to load chat sessions: {str(e)}")
        logging.error(f"Failed to load chat sessions: {str(e)}")
        return []

def delete_chat_session(session_id):
    try:
        chat_collection.delete_one({"_id": session_id})
    except Exception as e:
        st.error(f"Failed to delete chat session: {str(e)}")
        logging.error(f"Failed to delete chat session: {str(e)}")

## Nếu chưa có biến auth_page, mặc định hiển thị trang đăng ký
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

# Nếu người dùng chưa đăng nhập
if "user" not in st.session_state:
    if st.session_state.auth_page == "register":
        st.subheader("Register")
        with st.form("register_form"):
            reg_email = st.text_input("Email")
            reg_username = st.text_input("Username")
            reg_password = st.text_input("Password", type="password")
            reg_password_confirm = st.text_input("Confirm Password", type="password")
            reg_submit = st.form_submit_button("Register")
        if reg_submit:
            # Kiểm tra cấu trúc email
            if not reg_email.endswith("@gmail.com"):
                st.error("The email must be in the format ...@gmail.com")
            elif reg_password != reg_password_confirm:
                st.error("Password and Password Confirmation do not match!")
            else:
                # Gọi hàm đăng ký (register_user) đã được định nghĩa ở phần khác
                success, message = register_user(reg_email, reg_username, reg_password)
                if success:
                    st.success(message)
                    # Gửi email cảm ơn sau khi đăng ký thành công
                    send_thank_you_email(reg_email, reg_username)
                else:
                    st.error(message)
        # Nút chuyển sang trang đăng nhập
        if st.button("Already have an account? Login"):
            st.session_state.auth_page = "login"
            st.rerun()  # Cập nhật lại trang

    elif st.session_state.auth_page == "login":
        st.subheader("Login")
        with st.form("login_form"):
            login_input = st.text_input("Email or Username")
            login_password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Login")
        if login_submit:
            # Gọi hàm đăng nhập (login_user) đã được định nghĩa ở phần khác
            success, user_or_message = login_user(login_input, login_password)
            if success:
                st.session_state.user = user_or_message
                st.success("Register successfully!")
                st.rerun()
            else:
                st.error(user_or_message)
        # Nút chuyển sang trang đăng ký
        if st.button("Don't have an account yet? Register"):
            st.session_state.auth_page = "register"
            st.rerun()
    st.stop()

# Sau khi đăng nhập, hiển thị thông tin người dùng
st.sidebar.write(f"Hello, {st.session_state.user['username']}")

# Phần chat của ứng dụng
st.title("🐈 NeoMind: AI Research")

if "api_key" not in st.session_state:
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How can I help you today?"}]

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

with st.sidebar:
    st.header("🐈 NeoMind")
    if st.button("💬 New Chat", key="new_chat"):
        default_msg = [{"role": "assistant", "content": "How can I help you today?"}]
        if st.session_state.messages != default_msg:
            first_user_msg = next((msg["content"] for msg in st.session_state.messages if msg["role"] == "user"), None)
            title = first_user_msg if first_user_msg else "New Chat"
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
        title = session.get("title", "New Chat")
        if len(title) > max_title_length:
            title = title[:max_title_length] + "..."
        col1, col2 = st.columns([3, 1])
        if col1.button(title, key=str(session["_id"])):
            st.session_state.messages = session["messages"]
            st.session_state.current_session_id = session["_id"]
        if col2.button("❌", key="delete_" + str(session["_id"])):
            delete_chat_session(session["_id"])
            st.rerun()

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
                    logging.error(f"Error when connecting to API: {str(e)}")
                    st.session_state.messages.pop()
            
            # Sau mỗi lượt chat, tự động lưu phiên chat
            if st.session_state.current_session_id is not None:
                update_chat_session(st.session_state.current_session_id, st.session_state.messages)
            else:
                first_user_msg = next((msg["content"] for msg in st.session_state.messages if msg["role"] == "user"), None)
                title = first_user_msg if first_user_msg else "New Chat"
                new_id = save_chat_session(title, st.session_state.messages)
                st.session_state.current_session_id = new_id

    except Exception as e:
        st.error(f"❌ Configuration Error: {str(e)}")
        logging.error(f"Configuration Error: {str(e)}")
else:
    st.warning("🔑 Please enter your Gemini API Key in the sidebar to start")
