import streamlit as st

# الطريقة الصحيحة للقراءة من Secrets
# المسميات داخل الأقواس يجب أن تطابق المسميات التي كتبتها في إعدادات Streamlit
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
