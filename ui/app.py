import os
import streamlit as st
import requests
import json
from datetime import datetime

BASE_BACKEND_URL = os.getenv("BASE_BACKEND_URL", "http://13.60.77.224:8000")
FASTAPI_URL = f"{BASE_BACKEND_URL}/run-ocr"

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

    .stTextInput input, .stTextArea textarea, .stNumberInput input {
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

    /* ✅ NEW: Quick preset buttons styling */
    .stButton.preset-btn > button {
        background: rgba(255,255,255,0.08) !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 0.8rem !important;
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
    
    # ✅ NEW: Page range controls
    st.markdown("### Page Range")
    
    page_mode = st.radio(
        "Select mode:",
        ["All Pages", "Custom Range"],
        label_visibility="collapsed"
    )
    
    if page_mode == "Custom Range":
        col1, col2 = st.columns(2)
        with col1:
            start_page = st.number_input(
                "Start Page",
                min_value=1,
                value=1,
                step=1
            )
        with col2:
            end_page = st.number_input(
                "End Page",
                min_value=1,
                value=5,
                step=1,
                help="Leave as-is or adjust"
            )
        
        # ✅ NEW: Quick preset buttons
        st.markdown("**Quick Presets:**")
        preset_cols = st.columns(3)
        with preset_cols[0]:
            if st.button("First 5", key="preset_5"):
                start_page = 1
                end_page = 5
        with preset_cols[1]:
            if st.button("First 10", key="preset_10"):
                start_page = 1
                end_page = 10
        with preset_cols[2]:
            if st.button("Pages 3-7", key="preset_3_7"):
                start_page = 3
                end_page = 7
    else:
        start_page = 1
        end_page = None
    
    st.markdown("---")
    st.markdown("### Display Options")
    show_raw_json = st.toggle("Show raw JSON output", True)
    show_tables = st.toggle("Show tables", True)
    show_form_fields = st.toggle("Show form fields", True)

    st.markdown("---")
    st.markdown("### Backend Status")
    st.caption(f"Backend: {BASE_BACKEND_URL}")

    try:
        ping = requests.get(f"{BASE_BACKEND_URL}/health", timeout=3)
        if ping.status_code == 200:
            st.success("✅ Backend is running")
        else:
            st.warning("⚠️ Backend responded with an issue")
    except:
        st.error("❌ Backend is not running")

# ---------------------------
# MAIN UI
# ---------------------------
left, right = st.columns([1.25, 0.75], gap="large")

with left:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Upload PDF")
    uploaded = st.file_uploader("Select a PDF file", type=["pdf"], label_visibility="collapsed")

    if uploaded:
        st.success(f"✓ File selected: **{uploaded.name}**")
        st.caption(datetime.now().strftime("Uploaded on %d %b %Y, %I:%M %p"))
        
        # ✅ NEW: Show page range info
        if page_mode == "Custom Range":
            st.info(f"📄 Will extract pages **{start_page}** to **{end_page}**")
        else:
            st.info("📄 Will extract **all pages** from the document")
    else:
        st.info("Please upload a PDF to continue.")

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Run Extraction")
    run_btn = st.button("🚀 Start Extraction")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# EXTRACTION
# ---------------------------
if "result" not in st.session_state:
    st.session_state.result = None

if run_btn and uploaded:
    # ✅ NEW: Build URL with page parameters
    params = {"start_page": start_page}
    if end_page is not None:
        params["end_page"] = end_page
    
    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
    
    with st.spinner(f"🔄 Running extraction on pages {start_page}-{end_page or 'end'}..."):
        try:
            # ✅ NEW: Pass params to backend
            res = requests.post(FASTAPI_URL, files=files, params=params, timeout=600)

            if res.status_code == 200:
                st.session_state.result = res.json()
                st.success("✅ Extraction completed successfully")
            else:
                st.error(f"❌ Extraction failed (Status: {res.status_code})")
                st.code(res.text)
        
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. The PDF may be too large or Colab is slow.")
        
        except requests.exceptions.ConnectionError:
            st.error("🔌 Cannot connect to backend. Make sure FastAPI is running on port 8000.")
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

elif run_btn and not uploaded:
    st.warning("⚠️ Please upload a PDF file first")

# ---------------------------
# RESULTS
# ---------------------------
result = st.session_state.result

if result:
    st.markdown("---")
    st.markdown("## 📊 Extracted Output")

    # ✅ IMPROVED: Handle error responses
    if result.get("status") == "error":
        st.error(f"❌ Extraction Error: {result.get('message', 'Unknown error')}")
        with st.expander("View Error Details"):
            st.json(result)
    else:
        doc = result.get("document", {})
        pages = result.get("pages", [])

        # ✅ NEW: Show page range in metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"<div class='metric-card'><div class='label'>File Name</div><div class='value'>{doc.get('file_name','—')}</div></div>",
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f"<div class='metric-card'><div class='label'>Document Type</div><div class='value'>{doc.get('document_type','—')}</div></div>",
                unsafe_allow_html=True
            )
        with c3:
            st.markdown(
                f"<div class='metric-card'><div class='label'>Pages Processed</div><div class='value'>{doc.get('pages_processed', len(pages))}</div></div>",
                unsafe_allow_html=True
            )
        with c4:
            st.markdown(
                f"<div class='metric-card'><div class='label'>Page Range</div><div class='value'>{doc.get('page_range', '—')}</div></div>",
                unsafe_allow_html=True
            )

        st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["📄 Client View", "🔧 Raw JSON", "💾 Export"])

        with tab1:
            if not pages:
                st.info("No pages extracted")
            else:
                for p in pages:
                    page_num = p.get('page', '—')
                    section = p.get('section', 'Unknown Section')
                    
                    with st.expander(f"📄 Page {page_num}: {section}", expanded=(page_num == start_page)):
                        # Show section header
                        st.markdown(f"**Section:** {section}")
                        
                        # ✅ IMPROVED: Better display of different data types
                        if show_form_fields and "form_fields" in p and p["form_fields"]:
                            st.markdown("##### 📝 Form Fields")
                            st.json(p["form_fields"])
                        
                        if show_tables and "tables" in p and p["tables"]:
                            st.markdown("##### 📊 Tables")
                            # Try to display as dataframe if possible
                            for table_name, table_data in p["tables"].items():
                                st.markdown(f"**{table_name}**")
                                if isinstance(table_data, list) and table_data:
                                    try:
                                        import pandas as pd
                                        df = pd.DataFrame(table_data)
                                        st.dataframe(df, use_container_width=True)
                                    except:
                                        st.json(table_data)
                                else:
                                    st.json(table_data)
                        
                        # Show checkboxes if present
                        if "checkboxes" in p and p["checkboxes"]:
                            st.markdown("##### ☑️ Checkboxes")
                            st.json(p["checkboxes"])
                        
                        # Show signatures if present
                        if "signatures" in p and p["signatures"]:
                            st.markdown("##### ✍️ Signatures")
                            st.json(p["signatures"])
                        
                        # Show errors if any
                        if "error_message" in p:
                            st.error(f"⚠️ Error: {p['error_message']}")

        with tab2:
            if show_raw_json:
                st.json(result)

        with tab3:
            json_text = json.dumps(result, indent=2, ensure_ascii=False)
            
            # ✅ IMPROVED: Better filename with page range
            if page_mode == "Custom Range":
                filename = f"extracted_pages_{start_page}-{end_page}.json"
            else:
                filename = f"extracted_all_pages.json"
            
            st.download_button(
                "📥 Download JSON",
                json_text,
                filename,
                "application/json",
                use_container_width=True
            )
            
            st.text_area("JSON Output", json_text, height=300)
            
            # ✅ NEW: Copy to clipboard button helper
            st.caption("💡 Tip: Use the download button above or copy from the text area")

# ---------------------------
# ✅ NEW: Footer with usage tips
# ---------------------------
st.markdown("---")
with st.expander("ℹ️ Usage Tips"):
    st.markdown("""
    ### How to Use:
    1. **Upload PDF**: Select your document using the file uploader
    2. **Choose Range**: Select "All Pages" or "Custom Range" in the sidebar
    3. **Quick Presets**: Use preset buttons for common ranges (First 5, First 10, etc.)
    4. **Extract**: Click "Start Extraction" to begin processing
    5. **Review**: View results in Client View tab or export as JSON
    
    ### Page Range Examples:
    - **All Pages**: Processes entire document
    - **Pages 1-5**: Only extracts first 5 pages
    - **Pages 3-7**: Extracts pages 3 through 7
    - **Pages 10-end**: Set start_page=10, use "All Pages" mode
    
    ### Performance Tips:
    - Processing takes ~4-5 seconds per page
    - For large documents (20+ pages), consider processing in batches
    - Use Custom Range to test on a few pages first
    
    ### Display Options:
    - Toggle tables/form fields visibility in sidebar
    - Tables are displayed as interactive dataframes when possible
    - Download extracted data as JSON for further processing
    """)