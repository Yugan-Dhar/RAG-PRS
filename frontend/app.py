import streamlit as st
import requests
import time
import pandas as pd

API_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="PRS Compliance Intelligence Platform", layout="wide", page_icon="🛡️")

st.title("🛡️ PRS Compliance Intelligence Platform")
st.markdown("Automated Gap Analysis for Cybersecurity Standards")

# -- 1. Fetch Standards --
@st.cache_data(ttl=60)
def get_standards():
    try:
        r = requests.get(f"{API_URL}/standards")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
    return []

# -- 2. Fetch Frameworks for Standard --
@st.cache_data(ttl=60)
def get_frameworks(standard_id):
    try:
        r = requests.get(f"{API_URL}/standards/{standard_id}/frameworks")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Failed to fetch frameworks: {e}")
    return []

standards = get_standards()

if standards:
    st.subheader("1. Standard & Framework Selection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        standard_names = [s.get("name", s.get("id")) for s in standards]
        selected_standard_name = st.selectbox("Select Cybersecurity Standard", standard_names)
        
        selected_standard = next((s for s in standards if s.get("name", s.get("id")) == selected_standard_name), None)
        standard_id = selected_standard["id"] if selected_standard else None

    with col2:
        if standard_id:
            frameworks = get_frameworks(standard_id)
            if frameworks:
                framework_names = [f.get("name", f.get("id")) for f in frameworks]
                selected_framework_name = st.selectbox("Select Device Framework", framework_names)
                
                selected_framework = next((f for f in frameworks if f.get("name", f.get("id")) == selected_framework_name), None)
                framework_id = selected_framework["id"] if selected_framework else None
            else:
                st.warning("No frameworks found for this standard.")
                framework_id = None
        else:
            framework_id = None
            
    st.divider()

    st.subheader("2. Upload Technical Documentation")
    uploaded_file = st.file_uploader("Upload Product Manual, Security Target, or Architecture Doc", type=["pdf", "txt", "docx"])
    
    if uploaded_file and standard_id and framework_id:
        if st.button("Start AI Gap Analysis", type="primary"):
            with st.spinner("Uploading and running analysis pipeline..."):
                # Stub API Call to /assess
                # In full integration: we upload file, get doc_id, then call assess
                st.info("Initiating analysis jobs...")
                
                # Mock Job for MVP Demonstration
                # We show a progress bar simulating Phase 7 Backend Processing
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i in range(100):
                    time.sleep(0.05)
                    progress_bar.progress(i + 1)
                    if i < 20:
                        status_text.text("Ingesting & Parsing Document...")
                    elif i < 50:
                        status_text.text("Extracting Expected Capabilities...")
                    elif i < 80:
                        status_text.text("Retrieving and Analyzing Evidence with AI...")
                    else:
                        status_text.text("Generating Final Report...")
                
                st.success("Analysis Complete!")
                
                # Show mock results table
                st.subheader("Gap Analysis Report")
                
                data = {
                    "Requirement ID": ["R1", "R2", "R3"],
                    "Status": ["✅ Passed", "❌ Failed (Gap)", "⚠️ Partial"],
                    "Confidence": ["95%", "88%", "62%"],
                    "AI Justification": [
                        "Document explicitly states 'SSHv2 is supported'.",
                        "No evidence found for TLS 1.3 support. Only TLS 1.2 is mentioned.",
                        "Mentions password policies but lacks complexity requirements."
                    ]
                }
                
                df = pd.DataFrame(data)
                
                # Style the dataframe
                def color_status(val):
                    color = 'green' if 'Passed' in val else 'red' if 'Failed' in val else 'orange'
                    return f'color: {color}'
                    
                st.dataframe(df.style.map(color_status, subset=['Status']), use_container_width=True)
                
                st.download_button(
                    label="Download Full PDF Report",
                    data="Mock PDF Content",
                    file_name="compliance_report.pdf",
                    mime="application/pdf"
                )

else:
    st.info("No standards found. Please ensure the backend server is running on http://localhost:8000.")
