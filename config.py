import streamlit as st

# الطريقة الصحيحة للقراءة من Secrets في Streamlit Cloud
# المسميات داخل الأقواس هي "مفاتيح" تشير إلى البيانات المخفية
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
