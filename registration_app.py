import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from supabase import create_client
import config

# --- 1. إعدادات الاتصال وقاعدة البيانات ---
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# إعدادات الـ WebRTC لضمان عمل الكاميرا في السحابة والـ APK
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# --- 2. دالة استخراج البصمة ---
def get_normalized_encoding(face_landmarks):
    coords = np.array([[lm.x, lm.y, lm.z] for lm in face_landmarks])
    center = np.mean(coords, axis=0)
    coords -= center
    dist_scale = np.linalg.norm(coords)
    if dist_scale > 0:
        coords /= dist_scale
    return coords.flatten()

# --- 3. واجهة تطبيق الطالب ---
st.set_page_config(page_title="تسجيل طالب جديد", layout="centered", page_icon="👤")
st.title("🏛️ بوابة التسجيل الجامعي")
st.markdown("مرحباً بك. يرجى إدخال بياناتك الأكاديمية والتقاط صورة واضحة لوجهك لتفعيل بصمتك في النظام.")

# استخدام Session State لتخزين حالة التقاط الصورة
if "captured_frame" not in st.session_state:
    st.session_state.captured_frame = None

with st.form("student_registration_form", clear_on_submit=False):
    st.subheader("📝 البيانات الأكاديمية")
    student_name = st.text_input("👤 الأسم الكامل (عربي):")
    university = st.text_input("🏫 الجامعة:")
    department = st.text_input("🔬 القسم الدراسي:")
    academic_year = st.selectbox("📅 المرحلة الدراسية:", [
        "المرحلة الأولى",
        "المرحلة الثانية",
        "المرحلة الثالثة",
        "المرحلة الرابعة",
        "أخرى"
    ])

    st.subheader("📷 التقاط بصمة الوجه")
    st.info("نصيحة: قف في مكان جيد الإضاءة وانظر مباشرة للكاميرا.")
    
    # مشغل الكاميرا المدمج (WebRTC) بدلاً من st.camera_input
    webrtc_ctx = webrtc_streamer(
        key="student-registration",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    submit = st.form_submit_button("إرسال واعتماد البيانات", use_container_width=True)

# --- 4. منطق المعالجة عند الضغط على الزر ---
if submit:
    if not student_name or not university or not department:
        st.warning("⚠️ يرجى تعبئة جميع الحقول النصية.")
    elif not webrtc_ctx.video_receiver:
        st.warning("⚠️ يرجى تشغيل الكاميرا (Start) أولاً.")
    else:
        with st.spinner("⏳ جاري تحليل بصمة الوجه وحفظ البيانات..."):
            try:
                # التقاط الإطار الحالي من البث المباشر
                img_frame = webrtc_ctx.video_receiver.get_frame()
                
                if img_frame:
                    frame = img_frame.to_ndarray(format="bgr24")
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                    # إعداد مستخرج المعالم (Mediapipe)
                    options = vision.FaceLandmarkerOptions(
                        base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),
                        num_faces=1,
                        min_face_detection_confidence=0.7
                    )
                    detector = vision.FaceLandmarker.create_from_options(options)
                    result = detector.detect(mp_image)

                    if result.face_landmarks:
                        # تحويل البصمة إلى قائمة (List) لحفظها في سوبابيس
                        encoding = get_normalized_encoding(result.face_landmarks[0]).tolist()
                        
                        # إدخال البيانات في الجدول
                        supabase.table("students").insert({
                            "name": student_name.strip(),
                            "university": university.strip(),
                            "department": department.strip(),
                            "academic_year": academic_year,
                            "face_encoding": encoding
                        }).execute()
                        
                        st.success(f"🎉 تمت العملية بنجاح! أهلاً بك {student_name}.")
                        st.balloons()
                    else:
                        st.error("❌ لم يتم التعرف على وجه واضح. يرجى النظر مباشرة للكاميرا.")
                else:
                    st.error("❌ فشل التقاط صورة من البث. تأكد من أن الكاميرا تعمل.")
                
            except Exception as e:
                st.error(f"❌ حدث خطأ تقني: {str(e)}")
