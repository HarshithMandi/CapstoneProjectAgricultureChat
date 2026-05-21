import streamlit as st
import httpx
import os
import json

API_URL = os.getenv("API_URL", "http://localhost:8000")
ASSISTANT_GREETING = "Hi! Do you have any agriculture-related questions you'd like help with?"

def init_session_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


def reset_chat_messages(messages=None):
    st.session_state.messages = []

    for msg in messages or []:
        st.session_state.messages.append({"role": msg["role"], "content": msg["content"]})

    if not st.session_state.messages:
        st.session_state.messages.append({"role": "assistant", "content": ASSISTANT_GREETING})


def create_chat_session(load_messages=True):
    result = api_request("POST", "/chat/sessions", json={})
    if not result:
        return False

    st.session_state.session_id = result.get("id") or result.get("_id")
    if load_messages:
        reset_chat_messages(result.get("messages"))
    return bool(st.session_state.session_id)


def render_sources(sources):
    if not sources:
        return

    with st.expander("Sources"):
        for src in sources:
            if isinstance(src, dict):
                source = src.get("source", "unknown")
                similarity = src.get("similarity")
                if similarity is not None:
                    try:
                        st.write(f"- {source} ({float(similarity):.2f})")
                    except (TypeError, ValueError):
                        st.write(f"- {source} ({similarity})")
                else:
                    st.write(f"- {source}")
            else:
                st.write(f"- {src}")

def api_request(method, endpoint, json=None, params=None):
    url = f"{API_URL}{endpoint}"
    try:
        with httpx.Client() as client:
            if method == "GET":
                response = client.get(url, params=params, timeout=5.0)
            else:
                response = client.post(url, json=json, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


def stream_chat(session_id: str, message: str):
    url = f"{API_URL}/chat/sessions/{session_id}/messages/stream"
    timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=30.0)

    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", url, json={"message": message}) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                if not payload:
                    continue
                yield payload


def main():
    st.set_page_config(page_title="Agri RAG Chatbot", page_icon="🌾", layout="wide")
    init_session_state()

    st.sidebar.title("🌾 Agri RAG Assistant")

    page = st.sidebar.radio("Navigation", ["Chat", "Ingest Data", "Search", "Settings"])

    if page == "Chat":
        chat_page()
    elif page == "Ingest Data":
        ingest_page()
    elif page == "Search":
        search_page()
    elif page == "Settings":
        settings_page()


def chat_page():
    st.header("💬 Agriculture Chat Assistant")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("New Session"):
            st.session_state.session_id = None
            reset_chat_messages()
            st.rerun()

    if not st.session_state.messages:
        reset_chat_messages()

    if st.session_state.session_id:
        st.caption(f"Session ID: {st.session_state.session_id}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            render_sources(msg.get("sources"))

    if prompt := st.chat_input("Ask about crops, diseases, fertilizers..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            assistant_box = st.empty()
            sources_box = st.empty()

            full_text = ""
            sources = []
            try:
                if not st.session_state.session_id:
                    with st.spinner("Starting chat session..."):
                        if not create_chat_session(load_messages=False):
                            raise RuntimeError(
                                "Could not create a backend chat session. Check the MongoDB connection, then try again."
                            )

                for payload in stream_chat(st.session_state.session_id, prompt):
                    event = None
                    try:
                        event = json.loads(payload)
                    except Exception:
                        continue

                    if event.get("type") == "meta":
                        sources = event.get("sources") or []
                        continue

                    if event.get("type") == "token":
                        full_text += event.get("content", "")
                        assistant_box.markdown(full_text)
                        continue

                    if event.get("type") == "done":
                        break

                st.session_state.messages.append({"role": "assistant", "content": full_text, "sources": sources})
                if sources:
                    with sources_box.container():
                        render_sources(sources)
            except Exception as e:
                st.error(f"API Error: {str(e)}")


def ingest_page():
    st.header("📥 Ingest Agriculture Data")

    tab1, tab2, tab3 = st.tabs(["Single URL", "Multiple URLs", "Raw Text"])

    with tab1:
        with st.form("ingest_url"):
            url = st.text_input("URL", placeholder="https://example.com/agriculture-article")
            title = st.text_input("Title (optional)")
            topic = st.selectbox("Topic", ["general", "crops", "diseases", "fertilizers", "weather", "irrigation"])
            if st.form_submit_button("Ingest URL"):
                result = api_request("POST", "/ingest/url", json={"url": url, "title": title or None, "topic": topic})
                if result:
                    st.success(f"Ingested {result['chunks_created']} chunks!")

    with tab2:
        with st.form("ingest_urls"):
            urls_text = st.text_area("URLs (one per line)")
            topic_multi = st.selectbox("Topic", ["general", "crops", "diseases", "fertilizers"], key="multi_topic")
            if st.form_submit_button("Ingest URLs"):
                urls = [u.strip() for u in urls_text.split("\n") if u.strip()]
                result = api_request("POST", "/ingest/urls", json={"urls": urls, "topic": topic_multi})
                if result:
                    st.success(f"Ingested {result['chunks_created']} chunks!")

    with tab3:
        with st.form("ingest_text"):
            text = st.text_area("Text Content", height=200)
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Title")
            with col2:
                topic = st.selectbox("Topic", ["general", "crops", "diseases", "fertilizers", "weather"], key="text_topic")
            source = st.text_input("Source")
            if st.form_submit_button("Ingest Text"):
                result = api_request("POST", "/ingest/text", json={"text": text, "title": title, "source": source, "topic": topic})
                if result:
                    st.success(f"Ingested {result['chunks_created']} chunks!")


def search_page():
    st.header("🔍 Semantic Search")

    query = st.text_input("Search Query", placeholder="rice leaf blight symptoms")
    top_k = st.slider("Results", 1, 20, 5)

    if st.button("Search") and query:
        with st.spinner("Searching..."):
            result = api_request("POST", "/retrieval/search", json={"query": query, "top_k": top_k})
            if result:
                st.subheader(f"Found {len(result['results'])} results")
                for i, r in enumerate(result["results"], 1):
                    with st.expander(f"Result {i} (similarity: {r['similarity']:.2f})"):
                        st.write(r["content"])
                        st.json(r["metadata"])


def settings_page():
    st.header("⚙️ Settings")

    st.subheader("API Connection")
    api_url = st.text_input("Backend URL", value=API_URL)

    if st.button("Test Connection"):
        result = api_request("GET", "/health")
        if result and result.get("status") == "healthy":
            st.success("✅ Connected to backend!")
        else:
            st.error("❌ Cannot connect to backend")


if __name__ == "__main__":
    main()
