import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from supabase import create_client
import config
from datetime import datetime
import hashlib

# --- 1. إعدادات الاتصال والأمان ---
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# إعداد خوادم Google لضمان عمل البث عبر شبكات الهاتف (STUN Servers)
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# --- 2. معالجة الصور (المنطق البرمجي) ---
def enhance_image(frame):
    yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    yuv[:,:,0] = clahe.apply(yuv[:,:,0])
    return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

# بوابة الدخول (نفس منطق الأمان السابق)
if "password_correct" not in st.session_state:
    st.title("🔐 بوابة المشرفين")
    pwd = st.text_input("كلمة المرور:", type="password")
    if st.button("دخول"):
        if hashlib.sha256(pwd.encode()).hexdigest() == hashlib.sha256(config.ADMIN_PASSWORD.encode()).hexdigest():
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("خطأ!")
    st.stop()

# --- 3. واجهة المشرف بعد الدخول ---
st.title("👨‍🏫 رصد الحضور (وضع تطبيق الهاتف)")

subject = st.text_input("📖 المادة الحالية:", value="البرمجة")

# تهيئة الذاكرة المؤقتة لمنع التكرار
if 'session_attended' not in st.session_state: st.session_state.session_attended = set()

# تحميل بيانات الطلاب
students_raw = supabase.table("students").select("*").execute().data

# وظيفة معالجة الفيديو (هذا الجزء سيعمل داخل المتصفح/APK)
def video_frame_callback(frame):
    img = frame.to_ndarray(format="bgr24")
    
    # 1. تحسين الإضاءة
    img = enhance_image(img)
    
    # 2. تحويل الصورة لـ MediaPipe
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)
    
    # (هنا يتم وضع منطق التعرف على الوجوه كما في الكود السابق)
    # ملاحظة: في WebRTC نكتفي بإرجاع الصورة المحسنة للعرض
    return frame.from_ndarray(img, format="bgr24")

# --- 4. مشغل الكاميرا المتوافق مع الأندرويد ---
webrtc_ctx = webrtc_streamer(
    key="attendance-check",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIGURATION,
    video_frame_callback=video_frame_callback,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

if webrtc_ctx.state.playing:
    st.success("🎥 الكاميرا تعمل الآن. جاري الرصد...")
else:
    st.info("اضغط على Start لبدء استخدام كاميرا الهاتف.")