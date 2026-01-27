import streamlit as st
import requests
import json
from datetime import datetime

FASTAPI_URL = "http://127.0.0.1:8000/run-ocr"

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="AI Document Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# PROFESSIONAL UI CSS (Subtle, Enterprise)
# ---------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

    html, body, .stApp, p, label, input, textarea, button, h1, h2, h3, h4, h5 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: 0.15px;
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 10%, rgba(120,140,255,0.18), transparent 45%),
            radial-gradient(circle at 85% 20%, rgba(80,200,220,0.14), transparent 50%),
            linear-gradient(180deg, #060814 0%, #0A0F1F 60%, #050814 100%);
        color: #EAEAF0;
    }

    footer {visibility: hidden;}

    .hero {
        padding: 26px;
        border-radius: 24px;
        background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 20px 60px rgba(0,0,0,0.40);
        margin-bottom: 18px;
    }

    .hero h1 {
        font-size: 2.1rem;
        font-weight: 700;
        background: linear-gradient(90deg, #8EA2FF, #6FD3E8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 0.4px;
        margin: 0;
    }

    .hero p {
        margin-top: 8px;
        color: rgba(255,255,255,0.75);
        font-size: 0.98rem;
    }

    .card {
        padding: 18px;
        border-radius: 20px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 16px 45px rgba(0,0,0,0.35);
    }

    .metric-card {
        padding: 14px;
        border-radius: 16px;
        background: linear-gradient(160deg, rgba(110,130,255,0.14), rgba(90,190,210,0.12));
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 12px 40px rgba(0,0,0,0.32);
    }

    .label {
        font-size: 0.8rem;
        opacity: 0.7;
        font-weight: 600;
    }

    .value {
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 4px;
    }

    .stButton > button {
        width: 100%;
        border-radius: 14px !important;
        padding: 0.7rem 1rem !important;
        font-weight: 700 !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        background: linear-gradient(90deg, #6F82FF, #6FD3E8) !important;
        color: #050814 !important;
        box-shadow: 0 14px 45px rgba(0,0,0,0.35) !important;
    }

    .stTextInput input, .stTextArea textarea {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: rgba(255,255,255,0.92) !important;
    }

    details {
        background: rgba(255,255,255,0.04) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# HERO
# ---------------------------
st.markdown(
    """
    <div class="hero">
        <h1>AI Document Extractor</h1>
        <p>
            Upload a document and receive clean, structured insights suitable for
            both business users and technical teams.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    st.markdown("## Extraction Settings")
    max_pages = st.slider("Maximum pages to process", 1, 20, 5)
    show_raw_json = st.toggle("Show raw JSON output", True)
    show_tables = st.toggle("Show tables", True)
    show_form_fields = st.toggle("Show form fields", True)

    st.markdown("---")
    st.markdown("## Backend Status")

    try:
        ping = requests.get("http://127.0.0.1:8000/", timeout=2)
        if ping.status_code == 200:
            st.success("Backend is running")
        else:
            st.warning("Backend responded with an issue")
    except:
        st.error("Backend is not running")

# ---------------------------
# MAIN UI
# ---------------------------
left, right = st.columns([1.25, 0.75], gap="large")

with left:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Upload PDF")
    uploaded = st.file_uploader("Select a PDF file", type=["pdf"], label_visibility="collapsed")

    if uploaded:
        st.success(f"File selected: {uploaded.name}")
        st.caption(datetime.now().strftime("Uploaded on %d %b %Y, %I:%M %p"))
    else:
        st.info("Please upload a PDF to continue.")

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Run Extraction")
    run_btn = st.button("Start Extraction")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# EXTRACTION
# ---------------------------
if "result" not in st.session_state:
    st.session_state.result = None

if run_btn and uploaded:
    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
    with st.spinner("Running extraction..."):
        res = requests.post(FASTAPI_URL, files=files, timeout=600)

    if res.status_code == 200:
        st.session_state.result = res.json()
        st.success("Extraction completed successfully")
    else:
        st.error("Extraction failed")

# ---------------------------
# RESULTS
# ---------------------------
result = st.session_state.result

if result:
    st.markdown("## Extracted Output")

    doc = result.get("document", {})
    pages = result.get("pages", [])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='label'>File Name</div><div class='value'>{doc.get('file_name','—')}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='label'>Document Type</div><div class='value'>{doc.get('document_type','—')}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='label'>Pages Extracted</div><div class='value'>{len(pages)}</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Client View", "Raw JSON", "Export"])

    with tab1:
        for p in pages:
            with st.expander(f"Page {p.get('page','—')}"):
                if show_form_fields:
                    st.json(p.get("form_fields", {}))
                if show_tables:
                    st.json(p.get("tables", {}))

    with tab2:
        if show_raw_json:
            st.json(result)

    with tab3:
        json_text = json.dumps(result, indent=2)
        st.download_button("Download JSON", json_text, "output.json", "application/json")
        st.text_area("JSON Output", json_text, height=250)