import os
from typing import List, Dict

import pypdf  # Library to read PDF files
import io

import streamlit as st
import ollama

model = "gemma3:1b"
# CONFIG

st.write("")
st.set_page_config(
    page_title="Personal Trainer",
    page_icon="🧠",
    layout="wide",
)

MODEL = "gemma3:1b"

client = ollama.Client(
    host='https://gangly-leona-adsorptively.ngrok-free.dev',
    headers={'ngrok-skip-browser-warning': 'true'})
# -----------------------------
# STYLES
# -----------------------------

st.markdown(
    """
    <style>
        .main {
            padding-top: 1rem;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        .app-title {
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }
        .app-subtitle {
            color: #666;
            margin-bottom: 1rem;
        }
        .quick-btn-label {
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 0.4rem;
        }
        .small-note {
            font-size: 0.85rem;
            color: #777;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- MOD SELECTOR ---

col_space1, col_space2 = st.columns([0.5, 2,])

with col_space1:
    app_mode = st.radio(
        "Alege focusul tău de azi:",
        ["🏋️ Sport Trainer", "💼 Career Trainer"],
        horizontal=True,
        label_visibility="collapsed" # Ascundem eticheta pentru un look mai clean
    )

with col_space1:
    language = st.selectbox(
        "Select Language",
        ["Romanian",
         "German",
         "English",
         "Spanish", ]
    )

st.divider() # O linie fină de separare

if app_mode == "🏋️ Sport Trainer":
    st.subheader("💪 Let's train!")

    # Împărțim input-urile pe coloane pentru un look profi
    c1, c2, c3 = st.columns(3)
    with col_space1:
        greutate = st.number_input("Greutate (kg)", 40, 150, 75)
    with col_space1:
        inaltime = st.number_input("Înălțime (cm)", 120, 220, 180)
    with col_space1:
        vo2max = st.number_input("VO2 Max", 20, 90, 48)
    with col_space1:
        sport_ales = st.selectbox("Sportul tău:", ["Running", "Cycling", "Triathlon", "Crossfit"])
    with col_space1:
        nivel_antrenament = st.selectbox("Nivelul de antrenament:", ["competition", "stay healthy", "lose weight"])

    # Construim contextul pentru AI
    context_ai = f"Sportiv {sport_ales}, VO2Max: {vo2max}, BMI: {round(greutate / ((inaltime / 100) ** 2), 1)} , Language: {language} , Antrenament: {nivel_antrenament}"

else:
    st.subheader("🚀 Let's train!")

    c1, c2 = st.columns(2)
    with col_space1:
        job_title = st.text_input("Ce job țintești?", placeholder="ex: Python Developer")
    with col_space1:
        experience = st.select_slider("Experiență:", ["Junior", "Mid", "Senior", "Lead"])

    # New: Toggle between Upload and Paste
    with col_space1:
        input_method = st.radio("Provide Job Description via:", ["File Upload (PDF/TXT)", "Manual Paste"],
                                horizontal=False)

    jd_content = ""  # Variable to hold the extracted text
    with col_space1:
        if input_method == "File Upload (PDF/TXT)":
            uploaded_file = st.file_uploader("Upload the Job Description", type=["pdf", "txt"])
            if uploaded_file is not None:
                # Extract text from PDF
                if uploaded_file.type == "application/pdf":
                    try:
                        pdf_reader = pypdf.PdfReader(uploaded_file)
                        for page in pdf_reader.pages:
                            jd_content += page.extract_text()
                        st.success("✅ PDF text extracted successfully!")
                    except Exception as e:
                        st.error(f"Error reading PDF: {e}")
                # Extract text from TXT
                else:
                    jd_content = uploaded_file.read().decode("utf-8")
                    st.success("✅ TXT file loaded!")
        else:
            jd_content = st.text_area("Paste the Job Description here:", height=150)

        # Build context for the AI (summarized JD to avoid token overflow)
        context_ai1 = f"Role: {job_title}, Level: {experience}, Language: {language}, JD Context: {jd_content[:1000]} "


# -----------------------------
# HELPERS
# -----------------------------
def build_system_prompt(mode: str, user_context: str) -> str:
    """
    Takes the mode (Sport/Career) and the raw data (context_ai)
    and turns them into a strict AI personality.
    """
    if mode == "🏋️ Sport Trainer":
        return f"""
        ROLE: You are an Elite Sports Coach.
        MANDATORY CONTEXT : {user_context}

        INSTRUCTIONS:
        1. Analyze the BMI and VO2Max from the CLIENT DATA.
        2. If BMI > 25, prioritize fat-burning and low-impact exercises.
        3. Use the specified 'Language' for all responses.
        4. Provide specific workout advice based on the 'Sport' and 'Nivel Antrenament'.
        """
    else:
        return f"""
        ROLE: You are a Senior Tech Recruiter.
        MANDATORY CONTEXT : {user_context}

        INSTRUCTIONS:
        1. Use the Job Description provided in the context to ask technical questions.
        2. Give feedback based on the seniority level mentioned.
        3. Always maintain a professional tone in the requested 'Language'.
        """

# --- UI CHAT LOGIC ---


with col_space2:
    # --- INITIALIZATION ---
    # Verificăm dacă "messages" există deja în memorie.
    # Dacă NU există (e prima rulare), creăm o listă goală.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if user_query := st.chat_input("Ask your coach..."):

        # 1. PASUL DE INTERPRETARE: Construim promptul de sistem cu datele tale
        # Aici 'context_ai' este string-ul tau cu BMI, VO2Max, etc.

        if app_mode == "🏋️ Sport Trainer":
            system_instructions = build_system_prompt(app_mode, context_ai)
        else:
            system_instructions = build_system_prompt(app_mode, context_ai1)

        # 2. ACTUALIZARE ISTORIC: Adaugam intrebarea utilizatorului
        st.session_state.messages.append({"role": "user", "content": user_query})

        # Afișăm mesajul utilizatorului pe ecran
        with st.chat_message("user"):
            st.markdown(user_query)

        # 3. TRIMITERE REQUEST LA OLLAMA
       # with st.chat_message("assistant"):
            # Pregătim lista de mesaje (System Prompt + Tot istoricul de până acum)
            payload = [
                      {"role": "system", "content": system_instructions}
                  ] + st.session_state.messages

            # Apelăm modelul cu streaming (pentru efectul de "typing")
            try:
                stream = client.chat(
                    model=model,
                    messages=payload,
                    stream=True
                )
                # Modifică bucata de cod unde citești stream-ul:
                with st.chat_message("assistant"):
                    # Chemăm funcția care returnează stream-ul de la Ollama
                    response_stream = client.chat(
                        model=model,
                        messages=payload,
                        stream=True
                    )

                    # Cream un generator care extrage DOAR textul din obiectul JSON pe care l-ai văzut în imagine
                    def stream_parser():
                        for chunk in response_stream:
                            # Mergem pe structura: message -> content
                            yield chunk['message']['content']


                    # Folosim st.write_stream cu generatorul nostru curat
                    full_response = st.write_stream(stream_parser())

                    # Acum salvăm în istoric doar textul final, nu tot JSON-ul
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"Eroare la conectarea cu Ollama: {e}")
