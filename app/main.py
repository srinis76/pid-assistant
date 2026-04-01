"""
P&ID Assistant - Main Streamlit UI v2.0
"""

import streamlit as st
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag_engine import RAGEngine
from app.vision_engine import VisionEngine
from app.query_router import QueryRouter
from app.mock_data import get_ticket, format_ticket


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="P&ID Assistant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Import font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hide default Streamlit header decoration */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
section[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #f1f5f9 !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* Demo question buttons */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
    font-weight: 400 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    width: 100% !important;
    padding: 8px 12px !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    line-height: 1.4 !important;
    transition: all 0.15s ease !important;
    margin-bottom: 4px !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(56,189,248,0.12) !important;
    border-color: #38bdf8 !important;
    color: #e0f2fe !important;
}

/* Clear chat button */
section[data-testid="stSidebar"] button[kind="primary"] {
    background: rgba(239,68,68,0.12) !important;
    border: 1px solid rgba(239,68,68,0.35) !important;
    border-radius: 8px !important;
    color: #fca5a5 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] button[kind="primary"]:hover {
    background: rgba(239,68,68,0.22) !important;
    border-color: #ef4444 !important;
}

/* Sidebar divider */
section[data-testid="stSidebar"] hr {
    border-color: #334155 !important;
    margin: 12px 0 !important;
}

/* Sidebar caption */
section[data-testid="stSidebar"] .stCaption {
    color: #475569 !important;
    font-size: 0.75rem !important;
}

/* ── Main area ── */
.main-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0369a1 100%);
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 24px;
    border: 1px solid #0284c7;
    display: flex;
    align-items: center;
    gap: 16px;
}
.main-header h1 {
    color: #f0f9ff !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
    letter-spacing: -0.02em;
}
.main-header p {
    color: #7dd3fc !important;
    font-size: 0.88rem !important;
    margin: 4px 0 0 0 !important;
}
.header-icon {
    font-size: 2.4rem;
    line-height: 1;
}
.header-badge {
    margin-left: auto;
    background: rgba(14,165,233,0.2);
    border: 1px solid #0284c7;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.75rem;
    color: #7dd3fc !important;
    font-weight: 500;
    white-space: nowrap;
}

/* ── Chat bubbles ── */
.user-bubble {
    background: linear-gradient(135deg, #1e3a5f, #0f4c8a);
    border: 1px solid #1d4ed8;
    border-radius: 12px 12px 2px 12px;
    padding: 12px 16px;
    margin: 6px 0;
    color: #e0f2fe;
    font-size: 0.92rem;
    line-height: 1.55;
    max-width: 80%;
    margin-left: auto;
}
.assistant-bubble {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 2px 12px 12px 12px;
    padding: 14px 18px;
    margin: 6px 0;
    color: #1e293b;
    font-size: 0.92rem;
    line-height: 1.6;
}

/* ── Route badge ── */
.route-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.badge-rag {
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #86efac;
}
.badge-vision {
    background: #fef3c7;
    color: #b45309;
    border: 1px solid #fcd34d;
}

/* ── Ticket card ── */
.ticket-card {
    border-left: 3px solid #0284c7;
    background: #f0f9ff;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin-top: 12px;
    font-size: 0.83rem;
}
.ticket-card .ticket-header {
    font-weight: 600;
    color: #0369a1;
    margin-bottom: 4px;
}

/* ── Stats chips ── */
.stat-chip {
    background: rgba(255,255,255,0.06);
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    text-align: center;
    font-size: 0.78rem;
    color: #94a3b8;
}
.stat-chip .val {
    font-size: 1.1rem;
    font-weight: 700;
    color: #38bdf8;
    display: block;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    border-radius: 12px !important;
    border: 1.5px solid #e2e8f0 !important;
    font-size: 0.92rem !important;
    padding: 12px 16px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #0284c7 !important;
    box-shadow: 0 0 0 3px rgba(2,132,199,0.12) !important;
}

/* Expander styling in sidebar */
section[data-testid="stSidebar"] details {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
section[data-testid="stSidebar"] details summary {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 8px 12px !important;
    color: #94a3b8 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Engine init ───────────────────────────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'engines_initialized' not in st.session_state:
    with st.spinner("Initializing P&ID Assistant..."):
        try:
            st.session_state.rag_engine = RAGEngine()
            st.session_state.vision_engine = VisionEngine()
            st.session_state.router = QueryRouter()
            st.session_state.engines_initialized = True
        except Exception as e:
            st.error(f"Error initializing engines: {e}")
            st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo / brand
    st.markdown("""
    <div style='padding: 8px 0 16px 0;'>
        <div style='font-size:1.3rem; font-weight:700; color:#f1f5f9; letter-spacing:-0.01em;'>
            🏭 P&ID Assistant
        </div>
        <div style='font-size:0.75rem; color:#475569; margin-top:3px;'>
            Gas Production Facility · D-254-001
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Demo questions
    st.markdown("### 💡 Questions")
    st.markdown("<div style='font-size:0.72rem; color:#475569; margin-bottom:10px;'>Click any question to run it</div>",
                unsafe_allow_html=True)

    demo_questions = [
        ("1", "What is V-101 and what are its operating conditions?"),
        ("2", "What instruments control pressure on V-101?"),
        ("3", "What safety valves protect the system?"),
        ("4", "Tell me about C-104 compressor — specs and instruments"),
        ("5", "What is connected to V-101 and what are the pipe sizes?"),
        ("6", "Any recent maintenance issues with V-102?"),
    ]

    for num, question in demo_questions:
        if st.button(question, key=f"demo_{num}", use_container_width=True):
            st.session_state.current_query = question
            st.rerun()

    st.markdown("---")

    # Combined system + session info (collapsed)
    rag_engine = st.session_state.rag_engine
    stats = rag_engine.llm_adapter.session_stats
    total_tokens = stats['total_input_tokens'] + stats['total_output_tokens']

    with st.expander("⚙️ System & Session Info"):
        provider = rag_engine.llm_adapter.provider
        model = rag_engine.llm_adapter.model
        chunks = rag_engine.collection.count()

        st.markdown(f"""
        <div style='font-size:0.78rem; line-height:2; color:#94a3b8;'>
            <div style='color:#64748b; font-size:0.68rem; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:4px;'>System</div>
            <b style='color:#cbd5e1;'>Provider:</b> {provider}<br>
            <b style='color:#cbd5e1;'>Model:</b> {model}<br>
            <b style='color:#cbd5e1;'>Vector DB:</b> ChromaDB · {chunks} chunks<br>
            <b style='color:#cbd5e1;'>Embeddings:</b> text-embedding-3-small
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='border-top:1px solid #334155; margin:10px 0;'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class='stat-chip'>
                <span class='val'>{stats['total_queries']}</span>
                Queries
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class='stat-chip'>
                <span class='val'>{total_tokens:,}</span>
                Tokens
            </div>""", unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:0.72rem; color:#475569; margin-top:8px;'>💰 Est. cost: ${stats['total_cost']:.6f}</div>",
                    unsafe_allow_html=True)

    st.markdown("---")

    # Clear chat
    if st.button("🗑️  Clear Conversation", key="clear", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("<div style='font-size:0.7rem; color:#334155; margin-top:8px; text-align:center;'>v2.0 · Gemini Flash · ChromaDB</div>",
                unsafe_allow_html=True)


# ── Header banner ─────────────────────────────────────────────────────────────
st.markdown("""
<div class='main-header'>
    <div class='header-icon'>🏭</div>
    <div>
        <h1>P&ID Assistant</h1>
        <p>Ask questions about plant equipment, instruments, and piping in plain English</p>
    </div>
    <div class='header-badge'>● Live · D-254-001</div>
</div>
""", unsafe_allow_html=True)



# ── Chat history ──────────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            # Route badge
            route = message.get("metadata", {}).get("route", "rag")
            badge_class = "badge-rag" if route == "rag" else "badge-vision"
            badge_label = "RAG · Vector Search" if route == "rag" else "Vision · Image Analysis"
            st.markdown(f"<span class='route-badge {badge_class}'>{badge_label}</span>",
                        unsafe_allow_html=True)

        st.markdown(message["content"])

        # P&ID images for vision queries
        if "images" in message and message["role"] == "assistant":
            st.markdown("**Referenced P&ID Diagrams:**")
            cols = st.columns(min(len(message["images"]), 3))
            for idx, img_path in enumerate(message["images"]):
                with cols[idx % 3]:
                    try:
                        from PIL import Image
                        img = Image.open(img_path)
                        st.image(img, caption=f"Page {idx + 1}", use_container_width=True)
                    except Exception as e:
                        st.error(f"Could not load image: {e}")

        # Maintenance ticket
        if "ticket" in message and message["role"] == "assistant" and message["ticket"]:
            t = message["ticket"]
            st.markdown(f"""
            <div class='ticket-card'>
                <div class='ticket-header'>📋 Maintenance Ticket · {t['equipment']}</div>
                <div><b>Issue:</b> {t['issue']}</div>
                <div><b>Resolution:</b> {t['resolution']}</div>
                <div style='margin-top:4px; font-size:0.78rem; color:#475569;'>
                    {t['status_emoji']} {t['status']} &nbsp;·&nbsp; Priority: {t['priority']} &nbsp;·&nbsp; {t['resolved']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── Chat input & processing ───────────────────────────────────────────────────
prompt = st.chat_input("Ask about equipment, instruments, safety systems...")

if not prompt and st.session_state.get('current_query'):
    prompt = st.session_state.current_query
    st.session_state.current_query = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching P&ID knowledge base..."):
            try:
                # Check for maintenance tickets
                ticket_info = None
                tags = re.findall(r'\b[A-Z]+-\d+[A-Z]?\b', prompt.upper())
                for tag in tags:
                    ticket = get_ticket(tag)
                    if ticket:
                        ticket_info = format_ticket(ticket)
                        break

                # Route query
                route = st.session_state.router.route_query(prompt)

                # Enhance with ticket context if relevant
                enhanced_prompt = prompt
                if ticket_info and any(w in prompt.lower() for w in ['issue', 'problem', 'maintenance', 'recent', 'ticket', 'service']):
                    enhanced_prompt = f"{prompt}\n\nNote: There is a maintenance ticket for this equipment: {ticket_info}"

                # Execute
                if route == "rag":
                    answer, metadata = st.session_state.rag_engine.query_rag(enhanced_prompt)
                else:
                    answer, metadata = st.session_state.vision_engine.query_vision(enhanced_prompt)

                # Show route badge + answer
                badge_class = "badge-rag" if route == "rag" else "badge-vision"
                badge_label = "RAG · Vector Search" if route == "rag" else "Vision · Image Analysis"
                st.markdown(f"<span class='route-badge {badge_class}'>{badge_label}</span>",
                            unsafe_allow_html=True)
                st.markdown(answer)

                # Show ticket card
                if ticket_info:
                    t = ticket_info
                    st.markdown(f"""
                    <div class='ticket-card'>
                        <div class='ticket-header'>📋 Maintenance Ticket · {t['equipment']}</div>
                        <div><b>Issue:</b> {t['issue']}</div>
                        <div><b>Resolution:</b> {t['resolution']}</div>
                        <div style='margin-top:4px; font-size:0.78rem; color:#475569;'>
                            {t['status_emoji']} {t['status']} &nbsp;·&nbsp; Priority: {t['priority']} &nbsp;·&nbsp; {t['resolved']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Save to history
                metadata['route'] = route
                msg = {
                    "role": "assistant",
                    "content": answer,
                    "metadata": metadata,
                    "ticket": ticket_info
                }
                if route == "vision" and "image_paths" in metadata:
                    msg["images"] = metadata["image_paths"]

                st.session_state.messages.append(msg)

            except Exception as e:
                err = f"Error processing query: {str(e)}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})

    st.rerun()
