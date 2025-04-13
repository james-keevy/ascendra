import streamlit as st
import csv
import pandas as pd
from collections import defaultdict
from openai import OpenAI
from datetime import datetime
import re
from fpdf import FPDF
import textwrap
import streamlit_authenticator as stauth

st.set_page_config(page_title="Learning Outcomes Levelling", layout="centered")

# To create a login screen for your public app (simulating private access)

# Hashed password generated earlier
hashed_passwords = ['$2b$12$2Myv8E.J5lIbWN5aThrBDOeGthVRDw4e7j38g.fDTOmiy.VvKRCZa']  

# ✅ New structure for credentials
credentials = {
    "usernames": {
        "ascendra": {
            "name": "Ascendra User",
            "password": hashed_passwords[0],
        }
    }
}

# ✅ New Authenticate() signature
authenticator = stauth.Authenticate(
    credentials,
    "ascendra_cookie",  # cookie_name
    "abcdef",           # key
    cookie_expiry_days=1
)

# 🔐 Show login widget
login_result = authenticator.login(form_name='Login', location='main')

if login_result is not None:
    name, auth_status, username = login_result
    if auth_status:
            name, auth_status, username = login_result

            if auth_status:
                authenticator.logout('Logout', location='sidebar')
                st.success(f"Welcome {name}")
                # 👉 Your app goes here

                # --- Streamlit UI ---
                # st.set_page_config(page_title="Ascendra", layout="centered")
                st.image("ascendra_v5.png", width=300)
                st.title("Comparing learning outcomes")
                st.caption("Ascendra v1.1 is limited to CSV files")
                st.caption("Ascendra provides AI-assisted comparisons of learning outcomes within different artefacts (e.g. qualifications, curricula, microcredentials, job descriptions and many others), but results should be interpreted as advisory, not definitive. The model relies on language patterns and may not capture nuanced policy or contextual differences across frameworks. It is not a substitute for expert judgement, formal benchmarking, or regulatory endorsement. Users should validate results through human review and consult official frameworks for authoritative decisions.")

                # Input: OpenAI API key
                api_key = st.secrets["OPENAI_API_KEY"]
               
                # File upload widgets
                Primary_file = st.file_uploader("Upload a primary artefact in CSV format", type="csv")
                Secondary_file = st.file_uploader("Upload a secondary artefact in CSV format", type="csv")

                # Match threshold slider
                high_match_threshold = st.slider("Set threshold for High Match (%)", min_value=50, max_value=100, value=80)

                # Session state for results
                if "results" not in st.session_state:
                    st.session_state.results = []

                # If all inputs are available
                if api_key and Primary_file and Secondary_file:
                    client = OpenAI(api_key=api_key)

                    # Load Primary levels
                    Primary_levels = defaultdict(list)
                    Primary_reader = csv.DictReader(Primary_file.read().decode("utf-8").splitlines())
                    Primary_reader.fieldnames = [h.strip().lstrip('\ufeff') for h in Primary_reader.fieldnames]
                    for row in Primary_reader:
                        if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
                            Primary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

                    # Load Secondary levels
                    Secondary_levels = defaultdict(list)
                    Secondary_reader = csv.DictReader(Secondary_file.read().decode("utf-8").splitlines())
                    Secondary_reader.fieldnames = [h.strip().lstrip('\ufeff') for h in Secondary_reader.fieldnames]
                    for row in Secondary_reader:
                        if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
                            Secondary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

                    # Set similarity slider in place
                    similarity_score = st.slider(
                        "Set Similarity Score", 
                        min_value=0, 
                        max_value=100, 
                        value=70, 
                        step=1, 
                        key="similarity_score_slider"
                    )
                    
                    # Level selection dropdowns
                    selected_Primary_level = st.selectbox("Select Primary Level", sorted(Primary_levels.keys()))
                    selected_Secondary_level = st.selectbox("Select Secondary Level", sorted(Secondary_levels.keys()))

                    # Compare levels
                    if st.button("Compare Levels"):
                        Primary_text = "\n".join(Primary_levels[selected_Primary_level])
                        Secondary_text = "\n".join(Secondary_levels[selected_Secondary_level])

                        prompt = f"""
                    Compare the following qualification level descriptors and assess their equivalence.

                    Primary Level {selected_Primary_level}:
                    {Primary_text}

                    Secondary Level {selected_Secondary_level}:
                    {Secondary_text}

                    Compare the descriptors. Are these levels equivalent? Highlight similarities and differences. 
                    Suggest the most appropriate Secondary level match and provide a similarity score out of 100.
                    """
                        
                        with st.spinner("Asking GPT-4o..."):
                                    try:
                                        response = client.chat.completions.create(
                                            model="gpt-4o",
                                            messages=[
                                                {
                                                    "role": "system",
                                                    "content": """You are an expert in qualifications frameworks and international education systems. You understand learning outcomes and domain-based comparisons. You are able to compare the learning outcomes in different artefacts (such as level descriptors, qualifications, curricula, and job descriptions). You are well versed in the application of taxonomies, such as the revised Bloom taxonomy for knowledge, the structure of the Observed Learning Outcome (SOLO) taxonomy, and the Dreyfus model of skill acquisition."""
                                                },
                                                {
                                                    "role": "user",
                                                    "content": prompt
                                                }
                                            ]
                                        )

                                        result_text = response.choices[0].message.content

                                        if st.button("🔄 New Query"):
                                            st.session_state.results = []
                                            st.rerun()

                                        if result_text:
                                            match = re.search(r"similarity score[^\d]*(\d{1,3})", result_text, re.IGNORECASE)
                                            similarity_score = int(match.group(1)) if match else None

                                            st.subheader(f"Comparison Result: Primary Level {selected_Primary_level} - Secondary Level {selected_Secondary_level}")

                                            if similarity_score is not None and 0 <= similarity_score <= 100:
                                                st.write(f"**Similarity Score:** {similarity_score}/100")
                                                st.progress(similarity_score / 100.0)

                                                if similarity_score >= high_match_threshold:
                                                    st.success("High Match")
                                                elif similarity_score >= 50:
                                                    st.warning("Moderate Match")
                                            else:
                                                    st.error("Low Match")

                                            with st.expander("View compared descriptors"):
                                                col1, col2 = st.columns(2)
                                                with col1:
                                                    st.markdown(f"**Primary Level {selected_Primary_level}**")
                                                    for item in Primary_levels[selected_Primary_level]:
                                                        st.markdown(f"- {item}")
                                                with col2:
                                                    st.markdown(f"**Secondary Level {selected_Secondary_level}**")
                                                    for item in Secondary_levels[selected_Secondary_level]:
                                                        st.markdown(f"- {item}")

                                            st.write(result_text)

                                            # Save to results state
                                            st.session_state.results.append({
                                                "Primary Level": selected_Primary_level,
                                                "Secondary Level": selected_Secondary_level,
                                                "Similarity Score": similarity_score if similarity_score else "N/A",
                                                "Response": result_text,
                                                "Timestamp": datetime.utcnow().isoformat()
                                            })
                                            
                                            from fpdf import FPDF
                                            import io
                                            from datetime import datetime
                                            from fpdf.enums import XPos, YPos

                                            class PDFWithFooter(FPDF):
                                                def footer(self):
                                                    self.set_y(-15)
                                                    self.set_font("DejaVu", "I", 8)
                                                    self.set_text_color(128)
                                                    self.cell(0, 10, "Powered by Ascendra | Version 1.0 – April 2025", 0, 0, "C")

                                            def safe_multicell(pdf_obj, width, height, text):
                                                import re
                                                if not text:
                                                    return
                                                words = re.split(r'(\s+)', str(text))
                                                current_line = ''
                                                for word in words:
                                                    chunk = current_line + word
                                                    if pdf_obj.get_string_width(chunk) > pdf_obj.w - 2 * pdf_obj.l_margin:
                                                        pdf_obj.multi_cell(width, height, current_line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                                                        current_line = word
                                                    else:
                                                        current_line += word
                                                if current_line.strip():
                                                    pdf_obj.multi_cell(width, height, current_line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                                            # --- Create PDF ---
                                            pdf = PDFWithFooter()
                                            pdf.add_page()

                                            # Fonts
                                            pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
                                            pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
                                            pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)
                                            pdf.set_font("DejaVu", size=8)

                                            # Header
                                            pdf.image("ascendra_v5.png", x=10, y=8, w=40)
                                            pdf.ln(25)
                                            pdf.set_font("DejaVu", "B", 14)
                                            safe_multicell(pdf, 0, 8, "Primary - Secondary Comparison Report")
                                            pdf.set_font("DejaVu", "", 8)
                                            safe_multicell(pdf, 0, 8, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
                                            pdf.ln(10)

                                            # Primary Level
                                            pdf.set_font("DejaVu", "B", 12)
                                            safe_multicell(pdf, 0, 8, f"Primary Level {selected_Primary_level}")
                                            pdf.set_font("DejaVu", "", 8)
                                            for item in Primary_levels[selected_Primary_level]:
                                                safe_multicell(pdf, 0, 8, f"• {item}")
                                            pdf.ln(5)

                                            # Secondary Level
                                            pdf.set_font("DejaVu", "B", 12)
                                            safe_multicell(pdf, 0, 8, f"Secondary Level {selected_Secondary_level}")
                                            pdf.set_font("DejaVu", "", 8)
                                            for item in Secondary_levels[selected_Secondary_level]:
                                                safe_multicell(pdf, 0, 8, f"• {item}")
                                            pdf.ln(5)

                                            # Similarity Score
                                            if similarity_score is not None:
                                                pdf.set_font("DejaVu", "B", 12)
                                                safe_multicell(pdf, 0, 8, f"Similarity Score: {similarity_score}/100")
                                                pdf.ln(5)

                                            # GPT Result
                                            pdf.set_font("DejaVu", "B", 12)
                                            safe_multicell(pdf, 0, 8, "GPT Comparison Result:")
                                            pdf.set_font("DejaVu", "", 8)
                                            safe_multicell(pdf, 0, 8, result_text)

                                            # Convert to BytesIO
                                            pdf_bytes = io.BytesIO(pdf.output(dest='S'))

                                            # PDF Download Button
                                            st.download_button(
                                                label="📄 Download this comparison as PDF",
                                                data=pdf_bytes,
                                                file_name=f"Primary_Secondary_comparison_{selected_Primary_level}_{selected_Secondary_level}.pdf",
                                                mime="application/pdf")
                                            
                                            # CSV Export Button
                                            if st.session_state.get("results"):
                                                df = pd.DataFrame(st.session_state.results)
                                                st.download_button(
                                                    label="📥 Download comparison as CSV",
                                                    data=df.to_csv(index=False).encode("utf-8"),
                                                    file_name="Primary_Secondary_comparisons.csv",
                                                    mime="text/csv"
                                                )

                                            # Reset Button
                                            if st.button("🔄 Run new query"):
                                                st.session_state.results = []
                                                st.rerun()
                                        else:
                                            st.info("No results yet — run a comparison to enable downloading.")
                                                                            
                                    except Exception as e:
                                        st.error(f"❌ API Error: {e}")
                    
                        # --- Pinned footer ---
                        st.markdown("""
                        <style>
                        footer { visibility: hidden; }
                        footer:after {
                            content: 'Powered by Ascendra | Built with Streamlit & OpenAI • Version 1.0 – April 2025';
                            visibility: visible;
                            display: block;
                            position: fixed;
                            bottom: 0;
                            width: 100%;
                            background-color: #f0f2f6;
                            color: #6c757d;
                            text-align: center;
                            padding: 0.5rem;
                            font-size: 0.8rem;
                            font-family: 'sans-serif';
                            z-index: 9999;
                        }
                        </style>
                        """, unsafe_allow_html=True)

    elif auth_status is False:
        st.error("Incorrect username or password")
    elif auth_status is None:
        st.warning("Please enter your credentials")
else:
    st.error("Login form could not be rendered.")