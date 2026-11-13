# ─────────────────────────────────────────────
#  frontend/ui_config.py
#  Cấu hình UI: màu sắc, icon, gợi ý câu hỏi.
#  Tách riêng để designer/PM chỉnh mà không
#  phải đụng vào logic app.py.
# ─────────────────────────────────────────────

import pandas as pd
import plotly.express as px
import streamlit as st


# ── Role UI config ─────────────────────────────────────────────────────────

ROLE_CONFIG = {
    "CEO": {
        "icon":  "👔",
        "color": "#f59e0b",
        "desc":  "Tầm nhìn chiến lược, doanh thu & nhân sự cấp cao",
        "suggestions": [
            "Doanh thu cao nhất của công ty là bao nhiêu?",
            "Nhân viên bán hàng giỏi nhất là ai?",
            "Văn phòng nào có doanh số tốt nhất?",
        ],
    },
    "Technical Mentor": {
        "icon":  "🧑‍💻",
        "color": "#6366f1",
        "desc":  "Hướng dẫn SQL, kiến trúc database, kỹ thuật query",
        "suggestions": [
            "Tôi cần query top 5 sản phẩm bán chạy nhất thì làm thế nào?",
            "Bảng nào chứa thông tin doanh thu theo tháng?",
            "Làm sao để JOIN bảng orders và customers?",
        ],
    },
    "Head of Sales": {
        "icon":  "📊",
        "color": "#10b981",
        "desc":  "Số liệu thực tế, phân tích kinh doanh, dashboard",
        "suggestions": [
            "Top 5 sản phẩm bán chạy nhất?",
            "Doanh thu theo từng tháng năm 2004?",
            "Khách hàng nào chi tiêu nhiều nhất?",
            "Số lượng đơn hàng theo trạng thái?",
        ],
    },
}


# ── Chart helpers ──────────────────────────────────────────────────────────

def get_numeric_cols(df: pd.DataFrame) -> list[str]:
    """Trả về danh sách cột có thể ép về số."""
    result = []
    for col in df.columns:
        try:
            pd.to_numeric(
                df[col].astype(str)
                       .str.replace(",", "")
                       .str.replace("$", "")
                       .str.strip()
            )
            result.append(col)
        except Exception:
            pass
    return result


def should_draw_chart(df: pd.DataFrame, question: str, role: str) -> bool:
    """Kiểm tra có nên vẽ chart không."""
    if role == "Technical Mentor":
        return False
    if df is None or df.empty or len(df) < 2 or len(df.columns) < 2:
        return False
    if not get_numeric_cols(df):
        return False

    # Câu hỏi về danh sách tên/địa chỉ → không cần chart
    no_chart_keywords = [
        "ai ", "nào ", "tên", "địa chỉ", "email",
        "điện thoại", "thông tin", "danh sách",
    ]
    if any(k in question.lower() for k in no_chart_keywords):
        return False

    return True


def draw_chart(df: pd.DataFrame, question: str, role: str) -> None:
    """Vẽ bar hoặc line chart tùy loại câu hỏi."""
    try:
        num_cols = get_numeric_cols(df)
        cat_cols = [c for c in df.columns if c not in num_cols]

        x_col = cat_cols[0] if cat_cols else df.columns[0]
        y_col = num_cols[0]
        color = ROLE_CONFIG[role]["color"]

        df_plot = df.copy()
        df_plot[y_col] = pd.to_numeric(
            df_plot[y_col].astype(str)
                          .str.replace(",", "")
                          .str.replace("$", "")
                          .str.strip(),
            errors="coerce",
        )
        df_plot = df_plot.dropna(subset=[y_col])

        time_keywords = ["tháng", "năm", "ngày", "quý", "thời gian"]
        use_line = any(k in question.lower() for k in time_keywords)

        if use_line:
            fig = px.line(
                df_plot, x=x_col, y=y_col,
                title=f"{y_col} theo {x_col}",
                template="plotly_dark",
                color_discrete_sequence=[color],
                markers=True,
            )
        else:
            fig = px.bar(
                df_plot, x=x_col, y=y_col,
                title=f"{y_col} theo {x_col}",
                template="plotly_dark",
                color_discrete_sequence=[color],
            )

        fig.update_layout(
            plot_bgcolor="#1a1d27",
            paper_bgcolor="#1a1d27",
            font_color="#a0aec0",
            title_font_color="#e2e8f0",
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception:
        pass  # Nếu vẽ lỗi thì bỏ qua, không crash app