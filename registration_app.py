import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from supabase import create_client
import config

# --- إعدادات الاتصال بقاعدة البيانات ---
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# دالة استخراج البصمة
def get_normalized_encoding(face_landmarks):
    coords = np.array([[lm.x, lm.y, lm.z] for lm in face_landmarks])
    center = np.mean(coords, axis=0)
    coords -= center
    dist_scale = np.linalg.norm(coords)
    if dist_scale > 0: coords /= dist_scale
    return coords.flatten()

# --- واجهة تطبيق الطالب ---
st.set_page_config(page_title="تسجيل طالب جديد", layout="centered", page_icon="👤")

st.title("🏛️ بوابة التسجيل الجامعي")
st.markdown("مرحباً بك. يرجى إدخال بياناتك الأكاديمية والتقاط صورة واضحة لوجهك لتفعيل بصمتك في النظام.")

with st.form("student_registration_form", clear_on_submit=False):
    st.subheader("📝 البيانات الأكاديمية")
    
    student_name = st.text_input("👤 الأسم الكامل (عربي):")
    university = st.text_input("🏫 الجامعة:")
    department = st.text_input("🔬 القسم الدراسي:")
    academic_year = st.selectbox("📅 المرحلة الدراسية:", ["المرحلة الأولى", "المرحلة الثانية", "المرحلة الثالثة", "المرحلة الرابعة", "أخرى"])

    st.subheader("📷 التقاط بصمة الوجه")
    st.info("نصيحة: قف في مكان جيد الإضاءة وانظر مباشرة للكاميرا.")
    img_file = st.camera_input("التقط صورتك الآن")
    
    submit = st.form_submit_button("إرسال واعتماد البيانات", use_container_width=True)

if submit:
    if not student_name or not university or not department or not img_file:
        st.warning("⚠️ يرجى تعبئة جميع الحقول والتقاط الصورة.")
    else:
        with st.spinner("⏳ جاري تحليل بصمة الوجه وحفظ البيانات..."):
            file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            options = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),
                num_faces=1, min_face_detection_confidence=0.7
            )
            detector = vision.FaceLandmarker.create_from_options(options)
            result = detector.detect(mp_image)

            if result.face_landmarks:
                encoding = get_normalized_encoding(result.face_landmarks[0]).tolist()
                try:
                    supabase.table("students").insert({
                        "name": student_name.strip(),
                        "university": university.strip(),
                        "department": department.strip(),
                        "academic_year": academic_year,
                        "face_encoding": encoding
                    }).execute()
                    st.success(f"🎉 تمت العملية بنجاح! أهلاً بك {student_name}.")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ حدث خطأ، قد يكون الاسم مسجلاً مسبقاً.")
            else:
                st.error("❌ لم يتم التعرف على وجه واضح. يرجى تحسين الإضاءة والمحاولة مجدداً.")