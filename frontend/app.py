# ─────────────────────────────────────────────
#  frontend/app.py  —  Streamlit UI
#  Chạy: streamlit run frontend/app.py
#
#  Không chứa business logic hay prompt.
#  Mọi xử lý qua backend/agent.py.
# ─────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

from backend.agent import ask
from frontend.ui_config import ROLE_CONFIG, should_draw_chart, draw_chart


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ClassicModels AI",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    section[data-testid="stSidebar"] {
        background-color: #1a1d27;
        border-right: 1px solid #2d3148;
    }
    .stChatMessage {
        background-color: #1a1d27 !important;
        border: 1px solid #2d3148;
        border-radius: 12px;
        padding: 4px;
        margin-bottom: 8px;
    }
    h1, h2, h3 { color: #e2e8f0 !important; }
    p, li, label { color: #a0aec0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚗 ClassicModels AI")
    st.divider()

    st.markdown("#### 👤 Chọn Role")
    selected_role = st.selectbox(
        "Role của bạn:",
        options=list(ROLE_CONFIG.keys()),
        format_func=lambda r: f"{ROLE_CONFIG[r]['icon']} {r}",
        key="selected_role",
    )

    cfg = ROLE_CONFIG[selected_role]
    st.markdown(f"""
    <div style="background:#1e2235;border:1px solid #2d3148;border-radius:8px;padding:10px;margin-top:8px;">
        <span style="color:{cfg['color']};font-weight:600;">{cfg['icon']} {selected_role}</span><br>
        <span style="color:#a0aec0;font-size:13px;">{cfg['desc']}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 💡 Gợi ý câu hỏi")
    for suggestion in cfg["suggestions"]:
        if st.button(suggestion, key=suggestion, use_container_width=True):
            st.session_state["pending_question"] = suggestion

    st.divider()
    st.markdown("#### 🗄️ Database")
    st.markdown("""
    `customers` · `orders` · `orderdetails`
    `products` · `productlines` · `employees`
    `offices` · `payments`
    """)
    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Session state init ────────────────────────────────────────────────────────
if "current_role" not in st.session_state:
    st.session_state.current_role = selected_role

# Reset chat khi đổi role
if st.session_state.current_role != selected_role:
    st.session_state.messages     = []
    st.session_state.current_role = selected_role

if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown(f"# {cfg['icon']} ClassicModels — {selected_role}")
st.markdown(f"_{cfg['desc']}_")
st.divider()

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sql"):
            with st.expander("🔍 Xem SQL do AI sinh"):
                st.code(msg["sql"], language="sql")
        if msg.get("df") is not None:
            st.dataframe(msg["df"], use_container_width=True)
            if should_draw_chart(msg["df"], msg.get("question", ""), selected_role):
                draw_chart(msg["df"], msg.get("question", ""), selected_role)

# Input câu hỏi
prompt = st.chat_input(f"Hỏi {selected_role}...")
if "pending_question" in st.session_state:
    prompt = st.session_state.pop("pending_question")

if prompt:
    # Hiển thị câu hỏi
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gọi backend
    with st.chat_message("assistant"):
        with st.spinner(f"{cfg['icon']} {selected_role} đang phân tích..."):
            try:
                answer, df, sql = ask(prompt, role=selected_role)
            except Exception as e:
                answer, df, sql = f"❌ Lỗi: {str(e)}", None, None

        st.markdown(answer)

        if sql:
            with st.expander("🔍 Xem SQL do AI sinh"):
                st.code(sql, language="sql")

        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
            if should_draw_chart(df, prompt, selected_role):
                draw_chart(df, prompt, selected_role)
            elif selected_role != "Technical Mentor":
                st.caption("ℹ️ Dữ liệu này không phù hợp để vẽ biểu đồ.")

    # Lưu vào lịch sử
    st.session_state.messages.append({
        "role":     "assistant",
        "content":  answer,
        "df":       df,
        "sql":      sql,
        "question": prompt,
    })