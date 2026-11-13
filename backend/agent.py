# ─────────────────────────────────────────────
#  backend/agent.py
#  Xử lý logic hỏi-đáp theo từng Role.
#  Prompt text nằm ở prompts/role_prompts.py.
#  Gọi LLM qua llm_client.py (có key rotation).
# ─────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from backend.vanna_setup import vn
from backend.llm_client import call_llm, generate_sql, AllQuotaExhausted
from backend.sql_guard import validate_sql, UnsafeSQLError
from prompt.role_prompts import ROLE_PROMPTS

# Keywords dùng để filter câu hỏi cho role CEO
CEO_ALLOWED_KEYWORDS = [
    "doanh thu", "revenue", "nhân viên", "employee",
    "sales rep", "bán hàng giỏi", "cao nhất", "top",
]


# ── Public API ─────────────────────────────────────────────────────────────

_CACHE: dict[tuple[str, str], tuple[str, pd.DataFrame | None, str | None]] = {}


def ask(question: str, role: str = "Head of Sales") -> tuple[str, pd.DataFrame | None, str | None]:
    """
    Hỏi AI theo role được chọn. Kết quả thành công được cache để tiết kiệm quota.
    Returns: (answer_text, dataframe_or_None, generated_sql_or_None)
    """
    key = (role, " ".join(question.lower().split()))
    if key in _CACHE:
        return _CACHE[key]
    result = _ask(question, role)
    if result[1] is not None:
        _CACHE[key] = result
    return result


def _ask(question: str, role: str) -> tuple[str, pd.DataFrame | None, str | None]:
    role_prompt = ROLE_PROMPTS.get(role, ROLE_PROMPTS["Head of Sales"])

    # Technical Mentor: không query DB, chỉ hướng dẫn SQL
    if role == "Technical Mentor":
        return _ask_llm_only(question, role_prompt), None, None

    # CEO: chỉ query nếu câu hỏi liên quan doanh thu / nhân viên
    if role == "CEO":
        q_lower = question.lower()
        if not any(k in q_lower for k in CEO_ALLOWED_KEYWORDS):
            return _ask_llm_only(question, role_prompt), None, None

    # Head of Sales + CEO (câu hỏi hợp lệ): query DB thực
    return _ask_with_db(question, role, role_prompt)


# ── Private helpers ────────────────────────────────────────────────────────

def _ask_llm_only(question: str, role_prompt: str) -> str:
    """LLM trả lời thuần, không query DB."""
    prompt = f"{role_prompt}\n\nCâu hỏi: {question}\n\nTrả lời bằng tiếng Việt:"
    try:
        return call_llm(prompt)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"


def _ask_with_db(question: str, role: str, role_prompt: str) -> tuple[str, pd.DataFrame | None, str | None]:
    """Sinh SQL → kiểm tra an toàn → chạy query → format câu trả lời theo role."""
    sql = None
    try:
        sql = generate_sql(vn, question)

        try:
            sql = validate_sql(sql)
        except UnsafeSQLError as e:
            return f"🛡️ Câu SQL bị chặn bởi lớp bảo mật: {e}", None, sql

        df = vn.run_sql(sql)

        if df is None or df.empty:
            return "Không tìm thấy dữ liệu phù hợp với câu hỏi này.", None, sql

        answer = _format_answer(question, df, role_prompt)
        return answer, df, sql

    except AllQuotaExhausted as e:
        return str(e), None, sql
    except Exception as e:
        return f"❌ Lỗi: {str(e)}", None, sql


def _format_answer(question: str, df: pd.DataFrame, role_prompt: str) -> str:
    """
    Dùng LLM để format kết quả query thành câu trả lời tự nhiên theo role.
    Fallback về text đơn giản nếu LLM thất bại.
    """
    rows = df.values.tolist()
    data_text = "\n".join(
        f"{i}. {' | '.join(str(v) for v in row)}"
        for i, row in enumerate(rows[:10], 1)
    )

    prompt = f"""{role_prompt}

Dữ liệu từ database:
{data_text}

Câu hỏi của người dùng: {question}

Hãy trả lời theo đúng vai trò của bạn, bằng tiếng Việt, dựa trên dữ liệu trên:"""

    try:
        return call_llm(prompt)
    except Exception:
        # Fallback: trả về dạng danh sách đơn giản
        lines = [
            f"{i}. {' - '.join(str(v) for v in row)}"
            for i, row in enumerate(rows[:10], 1)
        ]
        return f"Kết quả ({len(rows)} bản ghi):\n" + "\n".join(lines)