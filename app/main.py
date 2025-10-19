"""
P&ID Digital Assistant - Main Streamlit UI

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
    page_title="P&ID Digital Assistant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'engines_initialized' not in st.session_state:
    with st.spinner("Initializing P&ID Digital Assistant..."):
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
    st.title("🏭 P&ID Assistant")

    st.markdown("---")

    st.subheader("📊 System Info")

    # Get stats
    rag_engine = st.session_state.rag_engine
    llm_stats = rag_engine.llm_adapter.session_stats

    st.metric("Total Queries", llm_stats['total_queries'])
    st.metric("RAG Queries", llm_stats['queries_by_type']['rag'])
    st.metric("Vision Queries", llm_stats['queries_by_type']['vision'])

    st.markdown("---")

    st.subheader("🔧 Settings")

    provider = st.session_state.rag_engine.llm_adapter.provider
    model = st.session_state.rag_engine.llm_adapter.model

    st.info(f"**Provider:** {provider}\n\n**Model:** {model}")

    st.markdown("---")

    st.subheader("📚 Example Queries")

    examples = [
        "What is V-101?",
        "Show me where V-101 is on the diagram",
        "What are the operating conditions for the separator?",
        "What equipment is connected to V-101?",
        "Tell me about PSV-101",
        "Display the flow path from V-101 to C-104"
    ]

    for example in examples:
        if st.button(example, key=f"ex_{example[:20]}"):
            st.session_state.current_query = example

    st.markdown("---")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()


# Main content
st.title("🏭 P&ID Digital Assistant")
st.markdown("*Ask questions about your P&ID documents in natural language*")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display metadata if available
        if "metadata" in message and message["role"] == "assistant":
            with st.expander("📋 Query Details"):
                meta = message["metadata"]

                if "route" in meta:
                    route_icon = "🖼️" if meta["route"] == "vision" else "📝"
                    st.markdown(f"{route_icon} **Route:** {meta['route'].upper()}")

                if "num_chunks_retrieved" in meta:
                    st.markdown(f"📦 **Chunks Retrieved:** {meta['num_chunks_retrieved']}")

                if "num_pages_analyzed" in meta:
                    st.markdown(f"📄 **Pages Analyzed:** {meta['num_pages_analyzed']}")

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

        # Display ticket info if available
        if "ticket" in message and message["role"] == "assistant":
            st.info(message["ticket"])


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
                # Route query
                router = st.session_state.router
                route = router.route_query(prompt)

                # Process based on route
                if route == "rag":
                    answer, metadata = st.session_state.rag_engine.query_rag(prompt)
                else:  # vision
                    answer, metadata = st.session_state.vision_engine.query_vision(prompt)

                # Display answer
                st.markdown(answer)

                # Check for tickets
                ticket_info = None
                # Simple tag extraction (look for patterns like V-101, PSV-101, etc.)
                import re
                tags = re.findall(r'\b[A-Z]+-\d+[A-Z]?\b', prompt.upper())

                for tag in tags:
                    ticket = get_ticket(tag)
                    if ticket:
                        ticket_info = format_ticket(ticket)
                        st.info(ticket_info)
                        break

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
    P&ID Digital Assistant v1.0 MVP | Powered by Gemini Flash, OpenAI, ChromaDB
</div>
""", unsafe_allow_html=True)
