import streamlit as st
from datetime import datetime, timedelta
import time
import re
import requests


BACKEND_URL = "http://127.0.0.1:5000"
SEARCH_ENDPOINT = f"{BACKEND_URL}/api/search"


def detect_question_language(question, preferred_language="English"):
    """Use Devanagari input to select Nepali for the current response."""

    if isinstance(question, str):
        devanagari_count = len(re.findall(r"[\u0900-\u097F]", question))
        latin_count = len(re.findall(r"[A-Za-z]", question))

        if devanagari_count > latin_count:
            return "नेपाली"

        if latin_count > devanagari_count:
            return "English"

    return preferred_language


def search_legal_documents(question, language="English"):
    """Send one question to the Flask legal search API."""

    nepali = language == "नेपाली"

    if not isinstance(question, str) or not question.strip():
        if nepali:
            return None, "कृपया खोज्नुअघि प्रश्न लेख्नुहोस्।", None

        return None, "Please enter a question before searching.", None

    try:
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"question": question.strip()},
            timeout=15,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        if nepali:
            return None, (
                "कानुनी खोज ब्याकएन्ड चलिरहेको छैन। "
                "कृपया Flask ब्याकएन्ड सुरु गरेर फेरि प्रयास गर्नुहोस्।"
            ), None

        return None, (
            "The legal search backend is not running. "
            "Please start the Flask backend and try again."
        ), None
    except requests.exceptions.Timeout:
        if nepali:
            return None, (
                "कानुनी खोज ब्याकएन्डबाट उत्तर आउन धेरै समय लाग्यो। "
                "कृपया फेरि प्रयास गर्नुहोस्।"
            ), None

        return None, (
            "The legal search backend took too long to respond. "
            "Please try again."
        ), None
    except requests.exceptions.RequestException as error:
        if nepali:
            return None, f"कानुनी खोज ब्याकएन्डमा समस्या भयो: {error}", None

        return None, f"Could not contact the legal search backend: {error}", None

    try:
        payload = response.json()
    except ValueError:
        if nepali:
            return None, "कानुनी खोज ब्याकएन्डले अमान्य उत्तर दियो।", None

        return None, "The legal search backend returned an invalid response.", None

    if not isinstance(payload, dict) or not isinstance(
        payload.get("results"), list
    ):
        if nepali:
            return None, "कानुनी खोज ब्याकएन्डले अमान्य उत्तर दियो।", None

        return None, "The legal search backend returned an invalid response.", None

    return payload["results"], None, payload.get("answer")


def summarize_legal_text(text, question, max_chars=520):
    """Return the most question-relevant sentences from a retrieved chunk."""

    if not isinstance(text, str) or not text.strip():
        return ""

    question_terms = {
        term.lower()
        for term in re.findall(r"[A-Za-z0-9\u0900-\u097F]+", question or "")
        if len(term) > 2
    }
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?।])\s+", text)
        if sentence.strip()
    ]

    if not sentences:
        return text[:max_chars].strip()

    ranked_sentences = sorted(
        enumerate(sentences),
        key=lambda item: (
            len(
                question_terms.intersection(
                    {
                        term.lower()
                        for term in re.findall(
                            r"[A-Za-z0-9\u0900-\u097F]+",
                            item[1],
                        )
                    }
                )
            ),
            -item[0],
        ),
        reverse=True,
    )

    selected = sorted(
        [sentence for _, sentence in ranked_sentences[:2]],
        key=sentences.index,
    )
    summary = " ".join(selected)

    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."

    return summary


def format_search_results(results, language="English", question=""):
    """Format concise, question-focused excerpts from retrieved legal results."""

    nepali = language == "नेपाली"

    if not results:
        if nepali:
            return "मिल्दो कानुनी कागजात भेटिएन।"

        return "No matching legal documents were found."

    if nepali:
        formatted_results = [
            "तपाईंको प्रश्नसँग सम्बन्धित कानुनी व्याख्या "
            "(मूल कानुनी अंशसहित):\n"
        ]
        section_label = "दफा"
        page_label = "पृष्ठ"
        unavailable_section = "दफा उपलब्ध छैन"
        unavailable_page = "पृष्ठ उपलब्ध छैन"
        unavailable_document = "कागजातको नाम उपलब्ध छैन"
        unavailable_text = "कानुनी पाठ उपलब्ध छैन"
    else:
        formatted_results = [
            "Based on the relevant legal provisions:\n"
        ]
        section_label = "Section"
        page_label = "Page"
        unavailable_section = "Section unavailable"
        unavailable_page = "Page unavailable"
        unavailable_document = "Document name unavailable"
        unavailable_text = "Legal text unavailable"

    for index, result in enumerate(results[:3], start=1):
        if not isinstance(result, dict):
            continue

        metadata = result.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}

        document_name = (
            metadata.get("file_name")
            or metadata.get("law_name")
            or unavailable_document
        )
        section = metadata.get("section_name") or unavailable_section
        page_number = metadata.get("page_number")
        page = page_number if page_number is not None else unavailable_page
        legal_text = summarize_legal_text(
            result.get("text") or unavailable_text,
            question,
        ) or unavailable_text

        formatted_results.append(
            f"**{index}. {document_name}**\n"
            f"{section_label}: {section}  \n"
            f"{page_label}: {page}  \n"
            f"> {legal_text}"
        )

    if len(formatted_results) == 1:
        if nepali:
            return "ब्याकएन्डले प्रयोग गर्न मिल्ने कानुनी परिणाम दिएन।"

        return "The backend returned no usable legal results."

    return "\n\n".join(formatted_results)

st.set_page_config(
    page_title="NitiShield AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


st.markdown("""
<style>


    .stApp {
        background: #f6f4ef;
        color: #0f172a;
    }

    .stApp:before {
        content: "";
        display: block;
        height: 5px;
        background: #102a43;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: #f6f4ef;
    }

    [data-testid="stHeader"] {
        background: #f6f4ef !important;
    }

    div[role="main"] *,
    .stApp .stMarkdownContainer,
    .stApp .stMarkdownContainer p,
    .stApp .stMarkdownContainer li,
    .stApp .stSelectbox label,
    .stApp .stTextInput label,
    .stApp .stTextArea label,
    .stApp .stDateInput label,
    .stApp .stButton button,
    .stApp .stMetric,
    .stApp .stCaption,
    div[data-testid="stWidgetLabel"],
    .stForm label,
    .stTextInput label,
    .stSelectbox label,
    .stCheckbox label,
    .stRadio label {
        color: #0f172a !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebar"] {
        background: #102a43;
        border-right: 1px solid #183b56;
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    [data-testid="stSidebar"] nav a,
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
        border-radius: 10px;
        color: #1f2937 !important;
    }

    [data-testid="stSidebar"] nav a:hover,
    [data-testid="stSidebar"] button:hover,
    [data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
        background-color: #183b56 !important;
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] [aria-current="page"],
    [data-testid="stSidebar"] .active {
        background-color: #28536f !important;
        color: #ffffff !important;
    }

    [data-testid="stTextInput"] > div,
    [data-testid="stTextArea"] > div,
    [data-testid="stSelectbox"] > div,
    [data-testid="stDateInput"] > div,
    [data-testid="stNumberInput"] > div,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stDateInput > div > div > div,
    .stNumberInput > div > div > input,
    div[data-testid="stBaseSelectbox"],
    div[data-testid="stBaseTextInput"],
    div[data-testid="stBaseTextarea"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input,
    .stSelectbox div[data-baseweb="select"],
    .stSelectbox > div > div > div,
    .stTextInput > div > div > input,
    .stSelectbox input,
    .stSelectbox span,
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    .stSelectbox > div > div,
    div[data-baseweb="select"],
    div[data-baseweb="popover"],
    div[role="listbox"],
    div[role="option"] {
        background-color: #ffffff !important;
        border: 1px solid #dfe7f1 !important;
        color: #0f172a !important;
    }

    div[role="option"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    div[role="option"]:hover,
    div[role="option"][aria-selected="true"] {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
    }

    .stCheckbox input,
    .stRadio input {
        accent-color: #475569 !important;
    }

    div[data-testid="stInfo"] {
        background-color: #f1f5f9 !important;
        border: 1px solid #dfe7f1 !important;
        color: #0f172a !important;
    }

.stApp {
    --primary-color: #93c5fd !important;
    --primaryColor: #93c5fd !important;
}


div[data-testid="stBottom"] {
    background: #f5f7fb !important;
    background-color: #f5f7fb !important;
}

div[data-testid="stBottomBlockContainer"] {
    background: #f5f7fb !important;
    background-color: #f5f7fb !important;
}

div[data-testid="stBottom"] > div,
div[data-testid="stBottomBlockContainer"] > div {
    background: #f5f7fb !important;
}

div[data-testid="stBottom"]::before,
div[data-testid="stBottom"]::after,
div[data-testid="stBottomBlockContainer"]::before,
div[data-testid="stBottomBlockContainer"]::after {
    background: #f5f7fb !important;
    box-shadow: none !important;
}


div[data-testid="stChatInput"] {
    background: #f1f5f9 !important;
    background-color: #f1f5f9 !important;

    border: 1px solid #93c5fd !important;
    border-radius: 12px !important;

    outline: none !important;
    box-shadow: none !important;

    color: #0f172a !important;
}


div[data-testid="stChatInput"] > div {
    background: #f1f5f9 !important;
    background-color: #f1f5f9 !important;

    border: none !important;
    border-radius: 11px !important;

    outline: none !important;
    box-shadow: none !important;
}


div[data-testid="stChatInput"]:focus,
div[data-testid="stChatInput"]:focus-within,
div[data-testid="stChatInput"] > div:focus,
div[data-testid="stChatInput"] > div:focus-within {
    background: #f1f5f9 !important;
    background-color: #f1f5f9 !important;

    border-color: #93c5fd !important;
    outline: none !important;
    box-shadow: none !important;
}



div[data-testid="stChatInput"] textarea {
    background: transparent !important;

    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;

    caret-color: #2563eb !important;

    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}


div[data-testid="stChatInput"] textarea:focus {
    background: transparent !important;

    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;

    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}


div[data-testid="stChatInput"] textarea,
div[data-testid="stChatInput"] textarea:hover,
div[data-testid="stChatInput"] textarea:active,
div[data-testid="stChatInput"] textarea:focus {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}



div[data-testid="stChatInput"] textarea::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
}



div[data-testid="stChatInput"] button {
    color: #475569 !important;
    background: #e2e8f0 !important;

    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}


div[data-testid="stChatInput"] button:hover {
    background: #cbd5e1 !important;
    color: #0f172a !important;
}

div[data-testid="stChatInput"] button:focus,
div[data-testid="stChatInput"] button:focus-visible {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

    div.stButton > button,
    button[kind="primary"],
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #d7d4cc !important;
        border-radius: 999px !important;
        padding: 0.65rem 1.1rem !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }

    div.stButton > button:hover,
    button[kind="primary"]:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: #e9e6df !important;
        border-color: #102a43 !important;
    }

    .main-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 38px;
        font-weight: 800;
        color: #102a43;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
        padding-top: 12px;
    }

    .subtitle {
        color: #5f6b76;
        font-size: 15px;
        margin-bottom: 25px;
    }

    h3 {
        color: #102a43 !important;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 25px !important;
        letter-spacing: 0 !important;
    }

    [data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }

    [data-testid="stHorizontalBlock"] .stButton > button {
        min-height: 44px;
    }

    .nav-brand {
        color: #28004d;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 28px;
        font-weight: 800;
        padding: 9px 0 12px;
    }

    .nav-subtitle {
        color: #5f6b76;
        font-size: 12px;
        padding-bottom: 10px;
    }

    .nav-caption {
        background: #ffffff;
        border-bottom: 3px solid #28004d;
        margin: -8px -4rem 28px;
        padding: 0 4rem;
    }

    .nav-caption + [data-testid="stHorizontalBlock"] {
        background: #ffffff;
    }

    [data-testid="stPopover"] {
        display: flex;
        justify-content: flex-end;
    }

    [data-testid="stPopoverButton"] {
        background: transparent !important;
        color: #000000 !important;
        border: 0 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        font-size: 26px !important;
        line-height: 1 !important;
        min-height: 44px !important;
        padding: 0.2rem 0.5rem !important;
        width: 48px !important;
    }

    [data-testid="stPopoverButton"] [data-testid="stIconMaterial"] {
        display: none !important;
    }

    [data-testid="stPopoverButton"]:hover {
        background: transparent !important;
        color: #000000 !important;
    }

    [data-testid="stPopover"] [data-testid="stMarkdownContainer"] p {
        color: #102a43 !important;
        font-weight: 700;
    }

    button[kind="tertiary"] {
        background: transparent !important;
        border: 0 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        color: #171323 !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        padding: 0.55rem 0.2rem !important;
        white-space: nowrap !important;
    }

    button[kind="tertiary"]:hover {
        background: transparent !important;
        color: #5b16b8 !important;
        text-decoration: underline;
        text-underline-offset: 5px;
    }

    @media (max-width: 900px) {
        .nav-caption {
            margin-left: -1rem;
            margin-right: -1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }

    .card {
        background: #ffffff;
        border-radius: 18px;
        padding: 24px;
        border: 1px solid #e1ded6;
        box-shadow: 0px 8px 24px rgba(16, 42, 67, 0.06);
        margin-bottom: 18px;
    }

    .metric-title {
        color: #64748b;
        font-size: 14px;
        font-weight: 600;
    }

    .metric-value {
        color: #102a43;
        font-size: 30px;
        font-weight: 800;
        margin-top: 5px;
    }

    .metric-small {
        color: #64748b;
        font-size: 12px;
    }

    .status-good {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        background: #dcfce7;
        color: #166534;
        font-size: 12px;
        font-weight: 700;
    }

    .status-warning {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        background: #fef3c7;
        color: #92400e;
        font-size: 12px;
        font-weight: 700;
    }

    .status-danger {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        background: #fee2e2;
        color: #991b1b;
        font-size: 12px;
        font-weight: 700;
    }

    .status-info {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        background: #dbeafe;
        color: #1e40af;
        font-size: 12px;
        font-weight: 700;
    }


    .finding {
        background: white;
        border-radius: 12px;
        padding: 18px;
        border: 1px solid #e5e7eb;
        margin-bottom: 12px;
    }

    .finding-title {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
    }

    .finding-description {
        color: #64748b;
        font-size: 13px;
        margin-top: 5px;
    }


    .chat-user {
        background: #e9e6df;
        padding: 12px 16px;
        border-radius: 12px;
        margin: 8px 0;
        color: #0f172a;
        border: 1px solid #d7d4cc;
    }

    .chat-ai {
        background: white;
        padding: 14px 16px;
        border-radius: 12px;
        margin: 8px 0;
        border: 1px solid #e1ded6;
        color: #0f172a;
        box-shadow: 0px 5px 15px rgba(16, 42, 67, 0.05);
    }

    .chatbot-helper {
        text-align: center;
    }

    /* ---------- DOCUMENT ---------- */

    .document-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 20px;
        min-height: 180px;
    }

    .document-icon {
        font-size: 35px;
    }

    .document-title {
        font-size: 17px;
        font-weight: 700;
        margin-top: 10px;
    }

    .document-description {
        color: #64748b;
        font-size: 13px;
        margin-top: 5px;
    }

    /* ---------- HEADER ---------- */

    .topbar {
        background: white;
        padding: 15px 20px;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }

    .announcement-bar {
        background: #28004d;
        color: #ffffff;
        border-radius: 999px;
        padding: 11px 22px;
        margin: 8px 0 22px;
        text-align: center;
        font-size: 13px;
        font-weight: 700;
    }

    .homepage-hero {
        background: #dcd5ff;
        border-radius: 28px;
        padding: 64px 58px 30px;
        margin: 12px 0 28px;
        overflow: hidden;
        text-align: center;
        border: 1px solid #c9c0f3;
    }

    .homepage-kicker {
        color: #4c2b91;
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    .homepage-title {
        color: #160b29;
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(46px, 6vw, 82px);
        line-height: 0.98;
        margin: 18px auto 18px;
        max-width: 900px;
    }

    .homepage-description {
        color: #33274a;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 21px;
        line-height: 1.35;
        margin: 0 auto 28px;
        max-width: 720px;
    }

    .homepage-visual {
        background: #ffffff;
        border: 1px solid #d8d1ed;
        border-radius: 18px 18px 0 0;
        box-shadow: 0 12px 28px rgba(40, 0, 77, 0.14);
        margin: 40px auto -30px;
        max-width: 900px;
        padding: 16px 20px 22px;
        text-align: left;
    }

    .homepage-visual-top {
        color: #4c2b91;
        font-size: 14px;
        font-weight: 800;
        padding-bottom: 13px;
        border-bottom: 1px solid #ebe7f4;
    }

    .homepage-visual-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        padding-top: 15px;
    }

    .homepage-visual-card {
        background: #f7f5fc;
        border-radius: 10px;
        padding: 15px;
    }

    .homepage-visual-label {
        color: #746b85;
        font-size: 11px;
        font-weight: 700;
    }

    .homepage-visual-value {
        color: #160b29;
        font-size: 25px;
        font-weight: 800;
        margin-top: 5px;
    }

    @media (max-width: 700px) {
        .homepage-hero {
            padding: 42px 20px 20px;
        }

        .homepage-description {
            font-size: 18px;
        }

        .homepage-visual-grid {
            grid-template-columns: 1fr;
        }
    }

</style>
""", unsafe_allow_html=True)



if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
elif st.session_state.page == "AI Security Advisor":
    st.session_state.page = "Chatbot"

if "language" not in st.session_state:
    st.session_state.language = "English"

if "settings_section" not in st.session_state:
    st.session_state.settings_section = "Business Profile"

if "scan_started" not in st.session_state:
    st.session_state.scan_started = False

if "scan_complete" not in st.session_state:
    st.session_state.scan_complete = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def render_vulnerability_testing():
    st.markdown("## 🛡️ Vulnerability Testing")

    st.markdown(
        f"""
        <div class="card">
            <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">Security Testing Workspace</div>
            <div style="color: #64748b; line-height: 1.7;">Before performing a security test, confirm that you own this system or have explicit authorization to test it.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    authorized = st.checkbox(
        "I confirm that I own this system or have explicit authorization to perform security testing against it.",
        value=False,
    )

    target = st.text_input("Target", placeholder="Enter authorized target")

    start_button = st.button("Start Security Assessment", disabled=not authorized, use_container_width=True)

    if start_button:
        st.info("Backend vulnerability-testing functionality will be connected here.")


security_score = 72

findings = [
    {
        "name": "Missing Content-Security-Policy",
        "severity": "High",
        "score": 15,
        "description":
            "The website does not appear to define a Content-Security-Policy header."
    },
    {
        "severity": "Medium",
        "score": 10,
        "description":
            "Strict-Transport-Security is not configured."
    },
    {
        "name": "TLS Certificate",
        "severity": "Good",
        "score": 0,
        "description":
            "The TLS certificate is currently valid."
    },
    {
        "name": "HTTPS Configuration",
        "severity": "Good",
        "score": 0,
        "description":
            "The website is accessible over HTTPS."
    },
]


pages = [
    ("Dashboard", "Dashboard"),
    ("Chatbot", "Chatbot"),
    ("Testing", "Vulnerability Testing"),
    ("Compliance", "Legal Compliance"),
    ("Documents", "Document Generator"),
    ("Knowledge", "Knowledge Base"),
    ("Settings", "Settings")
]

st.markdown(
    '<div class="nav-caption">'
    '<div class="nav-brand">NitiShield</div>'
    '<div class="nav-subtitle">Smart Legal Compliance &amp; Cybersecurity Platform</div>'
    '</div>',
    unsafe_allow_html=True,
)

navigation_columns = st.columns(7)
for column, (item, target) in zip(navigation_columns[:6], pages[:6]):
    with column:
        if st.button(
            item,
            key=f"nav_{target}",
            type="tertiary",
            use_container_width=True,
        ):
            st.session_state.page = target
            st.rerun()

with navigation_columns[6]:
    with st.popover("⋮", use_container_width=True):
        st.markdown("Settings")

        for section in [
            "Business Profile",
            "Notification Preferences",
            "Interface",
        ]:
            if st.button(
                section,
                key=f"settings_nav_{section}",
                use_container_width=True,
            ):
                st.session_state.page = "Settings"
                st.session_state.settings_section = section
                st.rerun()


st.markdown(
    f'<div class="main-title">{st.session_state.page}</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Smart legal compliance and cybersecurity platform for Nepali SMEs'
    '</div>',
    unsafe_allow_html=True
)


if st.session_state.page == "Vulnerability Testing":
    render_vulnerability_testing()

elif st.session_state.page == "Dashboard":
    st.markdown(
        '<div class="announcement-bar">NitiShield Signal: Your security and compliance posture, made clear.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <section class="homepage-hero">
        <div class="homepage-kicker">NitiShield AI</div>
        <div class="homepage-title">Security clarity for growing businesses.</div>
        <div class="homepage-description">
            Get an at-a-glance view of your organization's cybersecurity and legal compliance posture.
        </div>
        <div class="homepage-visual">
            <div class="homepage-visual-top">NitiShield Security &amp; Compliance Dashboard</div>
            <div class="homepage-visual-grid">
                <div class="homepage-visual-card">
                    <div class="homepage-visual-label">SECURITY SCORE</div>
                    <div class="homepage-visual-value">{security_score} / 100</div>
                </div>
                <div class="homepage-visual-card">
                    <div class="homepage-visual-label">COMPLIANCE</div>
                    <div class="homepage-visual-value">68%</div>
                </div>
                <div class="homepage-visual-card">
                    <div class="homepage-visual-label">OPEN FINDINGS</div>
                    <div class="homepage-visual-value">{len(findings) - 1}</div>
                </div>
            </div>
        </div>
    </section>
    """, unsafe_allow_html=True)

    st.markdown("## NitiShield Security & Compliance Dashboard")
    st.caption("Get an at-a-glance view of your organization's cybersecurity and legal compliance posture.")

    with st.container():
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            business_name = st.text_input("Business / Website")
        with c2:
            target_url = st.text_input("Website URL")
        with c3:
            st.write("")
            st.write("")
            if st.button("🔍 Scan Website", use_container_width=True):
                st.session_state.page = "Security Scanner"
                st.session_state.scan_started = True
                st.session_state.scan_complete = False
                st.rerun()

    metric_cards = [
        ("🛡️", "Security Score", f"{security_score} / 100", "Needs Attention"),
        ("⚖️", "Compliance", "68%", "In Progress"),
        ("⚠️", "Security Findings", str(len(findings) - 1), "Need Attention"),
        ("📄", "Documents", "5", "Up to Date"),
    ]
    metric_columns = st.columns(4)
    for column, (icon, title, value, status) in zip(metric_columns, metric_cards):
        with column:
            st.markdown(f"""
            <div class="card" style="min-height:132px;">
                <div style="font-size:20px;">{icon}</div>
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-small">{status}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### Security Posture")
    posture, compliance = st.columns([1, 1])
    with posture:
        st.markdown("**Current security score**")
        st.markdown(f"<div class=\"metric-value\">{security_score} / 100</div>", unsafe_allow_html=True)
        st.progress(security_score / 100)
        st.caption("Your current security posture is good, but some issues require attention.")
        st.markdown('<span class="status-warning">Needs Attention</span>', unsafe_allow_html=True)
        st.write("")
        if st.button("View Security Findings", key="dashboard_findings", use_container_width=True):
            st.session_state.page = "Security Scanner"
            st.rerun()

    with compliance:
        st.markdown("### Compliance Progress")
        compliance_items = [
            ("Company Act 2063", 85, "Compliant"),
            ("Labor Act", 70, "Needs Attention"),
            ("Individual Privacy Act 2075", 55, "Needs Attention"),
            ("Electronic Transactions Act 2063", 65, "In Progress"),
        ]
        for name, value, status in compliance_items:
            item_col, value_col = st.columns([3, 1])
            with item_col:
                st.write(f"**{name}**")
                st.progress(value / 100)
            with value_col:
                st.caption(f"{value}%")
                st.caption(status)
        if st.button("View Compliance", key="dashboard_compliance", use_container_width=True):
            st.session_state.page = "Legal Compliance"
            st.rerun()

    st.markdown("### Needs Attention")
    attention_items = [
        ("HIGH", "Missing Content-Security-Policy", "Improve website security by adding a Content-Security-Policy header.", "Review", "Security Scanner"),
        ("MEDIUM", "Security Configuration Review", "Review current security configuration and recommended controls.", "View Details", "Security Scanner"),
    ]
    for index, (severity, title, description, action, destination) in enumerate(attention_items):
        finding_col, action_col = st.columns([5, 1])
        with finding_col:
            status_class = "status-danger" if severity == "HIGH" else "status-warning"
            st.markdown(f"""
            <div class="finding">
                <div class="finding-title"><span class="{status_class}">{severity}</span> &nbsp; {title}</div>
                <div class="finding-description">{description}</div>
            </div>
            """, unsafe_allow_html=True)
        with action_col:
            st.write("")
            if st.button(action, key=f"dashboard_attention_{index}", use_container_width=True):
                st.session_state.page = destination
                st.rerun()

    monitoring, activity = st.columns([1, 1])
    with monitoring:
        st.markdown("### Security Monitoring")
        monitoring_items = [
            ("Website Security", "● Monitored", "status-good"),
            ("TLS Certificate", "● Valid", "status-good"),
            ("Security Headers", "⚠ 2 Missing", "status-warning"),
            ("Compliance Monitoring", "● Active", "status-good"),
        ]
        for title, status, status_class in monitoring_items:
            item_col, status_col = st.columns([3, 2])
            with item_col:
                st.write(f"**{title}**")
            with status_col:
                st.markdown(f'<span class="{status_class}">{status}</span>', unsafe_allow_html=True)

    with activity:
        st.markdown("### Recent Activity")
        for title, date in [
            ("Security assessment completed", "Today"),
            ("Compliance review updated", "Yesterday"),
            ("Privacy policy review scheduled", "15 September 2026"),
        ]:
            st.write(f"**{title}**")
            st.caption(date)

    st.markdown("### Quick Actions")
    action_columns = st.columns(4)
    quick_actions = [
        ("🔍 Run Security Scan", "Security Scanner"),
        ("⚖️ Review Compliance", "Legal Compliance"),
        ("🤖 Open Chatbot", "Chatbot"),
        ("📄 Generate Document", "Document Generator"),
    ]
    for column, (label, destination) in zip(action_columns, quick_actions):
        with column:
            if st.button(label, key=f"dashboard_action_{destination}", use_container_width=True):
                st.session_state.page = destination
                st.rerun()


elif st.session_state.page == "Security Scanner":

    st.markdown("## Website Security Scanner")

    url = st.text_input(
        "Target Website"
    )

    scan_col1, scan_col2 = st.columns([1, 4])

    with scan_col1:
        start_scan = st.button(
            " Start Scan",
            use_container_width=True
        )

    with scan_col2:
        st.caption("Target website will be analyzed for common security issues.")

    if start_scan:

        progress = st.progress(0)
        status = st.empty()

        steps = [
            "Validating URL...",
            "Connecting to HTTPS port 443...",
            "Checking TLS certificate...",
            "Inspecting HTTP security headers...",
            "Calculating security risk...",
            "Preparing security report..."
        ]

        for i, step in enumerate(steps):
            status.info(step)
            progress.progress(int(((i + 1) / len(steps)) * 100))
            time.sleep(0.25)

        status.success("Scan completed successfully.")
        st.session_state.scan_complete = True

    if st.session_state.scan_complete:

        st.markdown("## Scan Results")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Security Score",
                "72 / 100"
            )

        with c2:
            st.metric(
                "High Risk",
                "1"
            )

        with c3:
            st.metric(
                "Medium Risk",
                "1"
            )

        st.markdown("### Vulnerability Findings")

        for finding in findings:

            if finding["severity"] == "High":

                st.error(
                    f"🔴 **{finding['name']}**\n\n"
                    f"{finding['description']}"
                )

            elif finding["severity"] == "Medium":

                st.warning(
                    f"🟠 **{finding['name']}**\n\n"
                    f"{finding['description']}"
                )

            else:

                st.success(
                    f"🟢 **{finding['name']}**\n\n"
                    f"{finding['description']}"
                )

        st.markdown("### Risk Calculation")

        st.latex(
            r"Score = 100 - \sum w_i \times C_i"
        )


        st.download_button(
            "📥 Download Security Report",
            data="NitiShield AI Security Report\n\n"
                 "Security Score: 72/100\n"
                 "High Risk Findings: 1\n"
                 "Medium Risk Findings: 1",
            file_name="nitishield_security_report.txt",
            mime="text/plain"
        )

elif st.session_state.page == "Legal Compliance":

    st.markdown("## Legal Compliance Center")

    st.write(
        "Review business compliance requirements based on the "
        "Nepali legal framework included in NitiShield AI."
    )

    search = st.text_input(
        "🔎 Search compliance requirement",
        placeholder="Example: employment contract, privacy, tax..."
    )

    laws = [
        {
            "name": "Company Act 2063",
            "category": "Business Registration & Governance",
            "status": "Compliant",
            "progress": 85
        },
        {
            "name": "Labor Act",
            "category": "Employment & Contracts",
            "status": "Needs Attention",
            "progress": 70
        },
        {
            "name": "Individual Privacy Act 2075",
            "category": "Privacy & Data Protection",
            "status": "Needs Attention",
            "progress": 55
        },
        {
            "name": "Electronic Transactions Act 2063",
            "category": "Digital & Cybersecurity",
            "status": "In Progress",
            "progress": 65
        }
    ]

    for law in laws:

        if search and search.lower() not in (
            law["name"] + law["category"]
        ).lower():
            continue

        c1, c2, c3 = st.columns([3, 2, 1])

        with c1:

            st.markdown(f"### {law['name']}")

            st.caption(law["category"])

            st.progress(law["progress"] / 100)

        with c2:

            st.write("Compliance Level")

            st.write(
                f"**{law['progress']}%**"
            )

        with c3:

            if law["status"] == "Compliant":

                st.markdown(
                    '<span class="status-good">Compliant</span>',
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    '<span class="status-warning">Needs Attention</span>',
                    unsafe_allow_html=True
                )

    st.markdown("### Upcoming Compliance Deadlines")

    deadlines = [
        ("Employment Contract Review", "15 September 2026", "High"),
        ("Privacy Policy Review", "30 September 2026", "Medium"),
        ("Business Documentation Review", "15 October 2026", "Low")
    ]

    for task, date, priority in deadlines:

        c1, c2, c3 = st.columns([4, 2, 1])

        with c1:
            st.write(f"**{task}**")

        with c2:
            st.write(date)

        with c3:
            st.write(priority)



elif st.session_state.page == "Chatbot":

    if not st.session_state.chat_history:
        if st.session_state.language == "नेपाली":
            helper_text = (
                "तपाईंको वेबसाइटको सुरक्षा सम्बन्धी प्रश्न सोध्नुहोस्। "
                "AI ले सरल नेपाली भाषामा समाधान बताउनेछ।"
            )
        else:
            helper_text = (
                "Ask questions about your website security. "
                "The AI advisor will explain technical findings in simple language."
            )

        st.markdown(
            f'<div class="chatbot-helper">{helper_text}</div>',
            unsafe_allow_html=True,
        )

    for message in st.session_state.chat_history:

        if message["role"] == "user":

            st.markdown(
                f"""
                <div class="chat-user">
                    <b>You</b><br>
                    {message["content"]}
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(message["content"])

    user_question = st.chat_input(
        "Ask NitiShield AI..."
    )

    if user_question is not None:
        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": user_question
            }
        )

        results, error_message, answer = search_legal_documents(
            user_question,
            detect_question_language(
                user_question,
                st.session_state.language,
            ),
        )
        response = error_message or answer or format_search_results(
                results,
                detect_question_language(
                    user_question,
                    st.session_state.language,
                ),
                user_question,
            )

        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.rerun()


elif st.session_state.page == "Document Generator":

    st.markdown("## 📄 Legal Document Generator")

    st.write(
        "Generate customizable SME documents using the "
        "NitiShield AI document templates."
    )

    documents = [
        (
            "📄",
            "Employment Contract",
            "Employment agreement based on applicable labor requirements."
        ),
        (
            "🤝",
            "Service Agreement",
            "Agreement template for services provided by your business."
        ),
        (
            "🔐",
            "Privacy Policy",
            "Privacy policy template for websites and digital businesses."
        ),
        (
            "🌐",
            "Terms of Service",
            "Terms and conditions for your online service."
        ),
        (
            "🏢",
            "Business Agreement",
            "General agreement template for business operations."
        )
    ]

    cols = st.columns(2)

    for i, document in enumerate(documents):

        with cols[i % 2]:

            icon, title, description = document

            st.markdown(f"""
            <div class="document-card">
                <div class="document-icon">{icon}</div>
                <div class="document-title">{title}</div>
                <div class="document-description">
                    {description}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(
                f"Create {title}",
                key=f"document_{i}",
                use_container_width=True
            ):

                st.session_state.selected_document = title

    if "selected_document" in st.session_state:

        st.divider()

        st.markdown(
            f"### Create: {st.session_state.selected_document}"
        )

        with st.form("document_form"):

            business = st.text_input(
                "Business Name"
            )

            owner = st.text_input(
                "Owner / Representative Name"
            )

            address = st.text_area(
                "Business Address"
            )

            effective_date = st.date_input(
                "Effective Date",
                datetime.today()
            )

            submitted = st.form_submit_button(
                "Generate Document"
            )

            if submitted:

                st.success(
                    "Document generation request prepared. "
                    "The backend document generator can be connected here."
                )

                document_text = f"""
NitiShield AI
{st.session_state.selected_document}

Business Name:
{business}

Representative:
{owner}

Address:
{address}

Effective Date:
{effective_date}

Generated by NitiShield AI
"""

                st.download_button(
                    "📥 Download Preview",
                    data=document_text,
                    file_name="nitishield_document.txt",
                    mime="text/plain"
                )


elif st.session_state.page == "Knowledge Base":

    st.markdown("## 📚 Legal Knowledge Base")

    st.write(
        "Search the verified legal knowledge base used by the "
        "NitiShield AI compliance assistant."
    )

    query = st.text_input(
        "Search laws and regulations",
        placeholder="Search Company Act, privacy, labor, cybersecurity..."
    )

    knowledge_items = [
        (
            "Electronic Transactions Act 2063",
            "Digital transactions, electronic records and cyber-related provisions."
        ),
        (
            "Individual Privacy Act 2075",
            "Privacy and protection of personal information."
        ),
        (
            "Company Act 2063",
            "Business registration, governance and corporate requirements."
        ),
        (
            "Labor Act",
            "Employment standards, contracts and worker-related requirements."
        ),
        (
            "National Cyber Security Policy",
            "National cybersecurity direction and security principles."
        )
    ]

    for title, description in knowledge_items:

        if query and query.lower() not in (
            title + description
        ).lower():
            continue

        st.markdown(f"""
        <div class="card">
            <h3>{title}</h3>
            <p style="color:#64748b;">
                {description}
            </p>
            <span class="status-info">
                Verified Knowledge Source
            </span>
        </div>
        """, unsafe_allow_html=True)


elif st.session_state.page == "Settings":

    st.markdown("## ⚙️ Settings")

    if st.session_state.settings_section == "Business Profile":
        st.markdown("### Business Profile")

        with st.form("settings_form"):
            business_name = st.text_input(
                "Business Name",
                "My Nepali SME"
            )

            business_type = st.selectbox(
                "Business Type",
                [
                    "E-Commerce",
                    "IT / Software",
                    "Retail",
                    "Service",
                    "Education",
                    "Other"
                ]
            )

            website = st.text_input(
                "Website",
                "https://example.com"
            )

            email = st.text_input(
                "Business Email"
            )

            save = st.form_submit_button(
                "Save Settings"
            )

            if save:
                st.success(
                    "Settings saved in frontend session."
                )

    elif st.session_state.settings_section == "Notification Preferences":
        st.markdown("### Notification Preferences")

        st.checkbox(
            "Security scan notifications",
            value=True,
            key="security_scan_notifications",
        )

        st.checkbox(
            "Compliance deadline reminders",
            value=True,
            key="compliance_deadline_reminders",
        )

        st.checkbox(
            "AI security recommendations",
            value=True,
            key="ai_security_recommendations",
        )

    else:
        st.markdown("### Interface")

        st.selectbox(
            "Theme",
            ["Light", "System"],
            key="interface_theme",
        )

        selected_language = st.selectbox(
            "Language",
            ["English", "नेपाली"],
            index=0 if st.session_state.language == "English" else 1,
            key="interface_language",
        )

        st.session_state.language = selected_language

st.divider()
