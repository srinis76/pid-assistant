"""
P&ID Assistant - Main Streamlit UI

A conversational AI system for querying P&ID documents.
"""

import streamlit as st
from pathlib import Path

# Import engines
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag_engine import RAGEngine
from app.vision_engine import VisionEngine
from app.query_router import QueryRouter
from app.mock_data import get_ticket, format_ticket


# Page configuration
st.set_page_config(
    page_title="P&ID Assistant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initialize session state
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


# Sidebar
with st.sidebar:
    # Header
    st.title("P&ID Assistant")
    st.caption("AI-powered P&ID Query System")

    # Reduced spacing by 50%
    st.markdown("<div style='margin-top: -10px;'></div>", unsafe_allow_html=True)

    # Custom CSS for clean navigation links
    st.markdown("""
    <style>
    /* Navigation category headers */
    .nav-category {
        font-weight: 600;
        font-size: 0.85rem;
        color: #31333F;
        margin-top: 16px;
        margin-bottom: 8px;
        padding-left: 0px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Target all sidebar buttons globally and apply link styling */
    section[data-testid="stSidebar"] button[kind="secondary"] {
        border: none !important;
        background: none !important;
        box-shadow: none !important;
        padding: 6px 8px 6px 20px !important;
        text-align: left !important;
        font-weight: 400 !important;
        color: #0068c9 !important;
        transition: all 0.2s ease !important;
        font-size: 0.9rem !important;
        line-height: 1.6 !important;
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: #e3f2fd !important;
        color: #0051a8 !important;
        border-radius: 4px !important;
        text-decoration: underline !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:focus {
        box-shadow: none !important;
        outline: none !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:active {
        background-color: #bbdefb !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Example Queries Section
    st.markdown("### 💡 Example Queries")

    # Text Queries Category
    st.markdown('<div class="nav-category">📝 Text Queries (RAG)</div>', unsafe_allow_html=True)
    text_examples = [
        "What is PSV-101?",
        "What are the operating conditions for C-104?",
        "Any recent issues with V-102?"
    ]
    for idx, example in enumerate(text_examples):
        if st.button(example, key=f"ex_text_{idx}"):
            st.session_state.current_query = example
            st.rerun()

    # Visual Queries Category
    st.markdown('<div class="nav-category">🖼️ Visual Queries (Vision)</div>', unsafe_allow_html=True)
    visual_examples = [
        "Show me where V-101 is on the diagram",
        "What equipment is connected to V-101?",
        "Display the flow path from V-101 to C-104"
    ]
    for idx, example in enumerate(visual_examples):
        if st.button(example, key=f"ex_vis_{idx}"):
            st.session_state.current_query = example
            st.rerun()

    # Quick Actions
    st.markdown("---")
    st.markdown("### 🎯 Quick Actions")

    rag_engine = st.session_state.rag_engine
    llm_stats = rag_engine.llm_adapter.session_stats

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    with col_b:
        if st.button("📊 Show Stats", use_container_width=True):
            st.session_state.show_stats = True

    # Session Statistics (below quick actions)
    st.markdown("---")
    with st.expander("📊 **Session Statistics**", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", llm_stats['total_queries'], delta=None)
        with col2:
            total_tokens = llm_stats['total_input_tokens'] + llm_stats['total_output_tokens']
            st.metric("Tokens", f"{total_tokens:,}", delta=None)

        col3, col4 = st.columns(2)
        with col3:
            st.metric("📝 RAG", llm_stats['queries_by_type']['rag'])
        with col4:
            st.metric("🖼️ Vision", llm_stats['queries_by_type']['vision'])

        st.caption(f"💰 Total Cost: ${llm_stats['total_cost']:.6f}")

    # System Configuration (below statistics)
    with st.expander("⚙️ **System Configuration**", expanded=False):
        provider = st.session_state.rag_engine.llm_adapter.provider
        model = st.session_state.rag_engine.llm_adapter.model

        st.markdown(f"""
        **LLM Provider:** `{provider}`
        **Model:** `{model}`
        **Vector DB:** ChromaDB
        **Embeddings:** text-embedding-3-small
        """)

        # Collection info
        collection_count = st.session_state.rag_engine.collection.count()
        st.markdown(f"**Indexed Chunks:** {collection_count}")

    # Footer
    st.markdown("---")
    st.caption("**Status:** ✅ Online")
    st.caption(f"**Queries:** {llm_stats['total_queries']} | **Cost:** ${llm_stats['total_cost']:.4f}")


# Main content
st.title("P&ID Assistant")
st.markdown("*Ask questions about your P&ID documents in natural language*")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display P&ID images for vision queries
        if "images" in message and message["role"] == "assistant":
            st.markdown("#### 📊 Referenced P&ID Diagrams:")
            cols = st.columns(len(message["images"]))
            for idx, img_path in enumerate(message["images"]):
                with cols[idx]:
                    try:
                        from PIL import Image
                        img = Image.open(img_path)
                        st.image(img, caption=f"Page {idx+1}", use_container_width=True)
                    except Exception as e:
                        st.error(f"Error loading image: {e}")

        # Display ticket info if available (compact version)
        if "ticket" in message and message["role"] == "assistant" and message["ticket"]:
            ticket = message["ticket"]
            st.markdown(f"""
            <div style='border-left: 3px solid #0068c9; padding: 8px 12px; margin-top: 12px; font-size: 0.85rem;'>
                <div style='font-weight: 600; margin-bottom: 4px; color: #0068c9;'>📋 {ticket['equipment']}</div>
                <div style='margin-bottom: 4px;'><b>Issue:</b> {ticket['issue']}</div>
                <div style='margin-bottom: 4px;'><b>Resolution:</b> {ticket['resolution']}</div>
                <div style='font-size: 0.8rem;'>
                    {ticket['status_emoji']} {ticket['status']} • Priority: {ticket['priority']} • {ticket['resolved']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# Chat input
if prompt := st.chat_input("Ask me about P&IDs...") or st.session_state.get('current_query'):
    # Use example query if available
    if st.session_state.get('current_query'):
        prompt = st.session_state.current_query
        st.session_state.current_query = None

    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Process query
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                # Check for tickets BEFORE processing query
                ticket_info = None
                import re
                tags = re.findall(r'\b[A-Z]+-\d+[A-Z]?\b', prompt.upper())

                for tag in tags:
                    ticket = get_ticket(tag)
                    if ticket:
                        ticket_info = format_ticket(ticket)
                        break

                # Route query
                router = st.session_state.router
                route = router.route_query(prompt)

                # If there's a ticket and query is about issues/maintenance, enhance the query
                enhanced_prompt = prompt
                if ticket_info and any(word in prompt.lower() for word in ['issue', 'problem', 'maintenance', 'recent', 'ticket', 'service']):
                    enhanced_prompt = f"{prompt}\n\nNote: There is a maintenance ticket for this equipment: {ticket_info}"

                # Process based on route
                if route == "rag":
                    answer, metadata = st.session_state.rag_engine.query_rag(enhanced_prompt)
                else:  # vision
                    answer, metadata = st.session_state.vision_engine.query_vision(enhanced_prompt)

                # Display answer
                st.markdown(answer)

                # Display ticket if available (compact version)
                if ticket_info:
                    with st.container():
                        st.markdown(f"""
                        <div style='border-left: 3px solid #0068c9; padding: 8px 12px; margin-top: 12px; font-size: 0.85rem;'>
                            <div style='font-weight: 600; margin-bottom: 4px; color: #0068c9;'>📋 {ticket_info['equipment']}</div>
                            <div style='margin-bottom: 4px;'><b>Issue:</b> {ticket_info['issue']}</div>
                            <div style='margin-bottom: 4px;'><b>Resolution:</b> {ticket_info['resolution']}</div>
                            <div style='font-size: 0.8rem;'>
                                {ticket_info['status_emoji']} {ticket_info['status']} • Priority: {ticket_info['priority']} • {ticket_info['resolved']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                # Save to chat history
                metadata['route'] = route
                message_data = {
                    "role": "assistant",
                    "content": answer,
                    "metadata": metadata,
                    "ticket": ticket_info
                }

                # Add images if vision query
                if route == "vision" and "image_paths" in metadata:
                    message_data["images"] = metadata["image_paths"]

                st.session_state.messages.append(message_data)

            except Exception as e:
                error_msg = f"Error processing query: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

    # Rerun to update UI
    st.rerun()


# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
    P&ID Assistant v1.0 MVP | Powered by Gemini Flash, OpenAI, ChromaDB
</div>
""", unsafe_allow_html=True)
