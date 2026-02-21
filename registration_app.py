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
# التأكد من جلب البيانات من ملف config المرتبط بـ Secrets
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# --- 2. إعدادات WebRTC المحسنة للعراق (تجاوز NAT/Firewall) ---
RTC_CONFIGURATION = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun2.l.google.com:19302"]},
            {"urls": ["stun:stun.services.mozilla.com"]},
        ]
    }
)

# --- 3. دالة استخراج بصمة الوجه الرياضية ---
def get_normalized_encoding(face_landmarks):
    coords = np.array([[lm.x, lm.y, lm.z] for lm in face_landmarks])
    center = np.mean(coords, axis=0)
    coords -= center
    dist_scale = np.linalg.norm(coords)
    if dist_scale > 0:
        coords /= dist_scale
    return coords.flatten().tolist()

# --- 4. تصميم واجهة التطبيق ---
st.set_page_config(page_title="تسجيل طالب جديد", layout="centered", page_icon="👤")
st.title("🏛️ بوابة التسجيل الجامعي")
st.markdown("مرحباً بك. يرجى إدخال بياناتك والتقاط صورة واضحة لوجهك.")

# تنسيق استمارة التسجيل
with st.form("registration_form"):
    st.subheader("📝 البيانات الأكاديمية")
    name = st.text_input("👤 الاسم الكامل (كما في الهوية):")
    uni = st.text_input("🏫 الجامعة:")
    dept = st.text_input("🔬 القسم الدراسي:")
    year = st.selectbox("📅 المرحلة:", ["الأولى", "الثانية", "الثالثة", "الرابعة", "أخرى"])

    st.subheader("📷 التقاط بصمة الوجه")
    st.info("قم بتشغيل الكاميرا وانتظر ظهور صورتك، ثم اضغط 'إرسال'")
    
    # مشغل الكاميرا المباشر
    webrtc_ctx = webrtc_streamer(
        key="student-camera",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    submit_btn = st.form_submit_button("إرسال واعتماد البيانات", use_container_width=True)

# --- 5. منطق المعالجة والحفظ ---
if submit_btn:
    if not name or not uni or not dept:
        st.warning("⚠️ يرجى إكمال جميع الحقول.")
    elif not webrtc_ctx.video_receiver:
        st.error("⚠️ يرجى الضغط على Start لتشغيل الكاميرا أولاً.")
    else:
        with st.spinner("⏳ جاري تحليل ملامح الوجه وحفظها في قاعدة البيانات..."):
            try:
                # التقاط الصورة من البث
                img_frame = webrtc_ctx.video_receiver.get_frame()
                if img_frame:
                    frame = img_frame.to_ndarray(format="bgr24")
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                    # معالجة الوجه باستخدام Mediapipe
                    options = vision.FaceLandmarkerOptions(
                        base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),
                        num_faces=1,
                        min_face_detection_confidence=0.7
                    )
                    with vision.FaceLandmarker.create_from_options(options) as detector:
                        result = detector.detect(mp_image)

                        if result.face_landmarks:
                            face_enc = get_normalized_encoding(result.face_landmarks[0])
                            
                            # رفع البيانات إلى Supabase
                            supabase.table("students").insert({
                                "name": name.strip(),
                                "university": uni.strip(),
                                "department": dept.strip(),
                                "academic_year": year,
                                "face_encoding": face_enc
                            }).execute()
                            
                            st.success(f"🎉 تمت العملية بنجاح! تم تسجيلك يا {name}.")
                            st.balloons()
                        else:
                            st.error("❌ لم يتم اكتشاف وجه. تأكد من الإضاءة وانظر للكاميرا.")
                else:
                    st.error("❌ فشل التقاط الصورة. يرجى إعادة محاولة تشغيل الكاميرا.")
            except Exception as e:
                st.error(f"❌ خطأ: {str(e)}")
