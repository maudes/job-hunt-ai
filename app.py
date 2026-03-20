"""
app.py — Job Hunt AI Streamlit UI
----------------------------------
Run with:  uv run streamlit run app.py
"""

import os
import re
import streamlit as st

from services.read import fetch_job_content, NOT_A_JOB
from services.aianalyzer import analyze
from services.updatesheet import upsert_job, update_llm_summary

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Job Hunt AI",
    page_icon="🎯",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Session state — must come BEFORE theme so dark_mode exists
# ---------------------------------------------------------------------------

for key in ["logs", "result", "save_done", "processing"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "logs" else None if key == "result" else False

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

T = {
    "bg":           "#f5f4f0",
    "surface":      "#ffffff",
    "border":       "#dddbd0",
    "text":         "#1a1a1a",
    "text_muted":   "#6b6b7b",
    "accent":       "#4f46e5",
    "accent_hover": "#3d35c0",
    "input_bg":     "#ffffff",
    "input_color":  "#1a1a1a",
    "placeholder":  "#aaa8b8",
    "log_bg":       "#eeecea",
    "log_text":     "#4a5a6a",
    "tag_bg":       "#ebe9f8",
    "tag_text":     "#4f46e5",
    "tag_border":   "#c5c1f0",
    "divider":      "#dddbd0",
    "title":        "#1a1a1a",
    "subtitle":     "#8a8a9a",
    "v_strong_bg":  "#dcfce7", "v_strong_text":  "#166534", "v_strong_border":  "#86efac",
    "v_good_bg":    "#dbeafe", "v_good_text":    "#1e40af", "v_good_border":    "#93c5fd",
    "v_strat_bg":   "#fef9c3", "v_strat_text":   "#854d0e", "v_strat_border":   "#fde047",
    "v_border_bg":  "#ffedd5", "v_border_text":  "#9a3412", "v_border_border":  "#fdba74",
    "v_no_bg":      "#fee2e2", "v_no_text":      "#991b1b", "v_no_border":      "#fca5a5",
}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
h1, h2, h3 {{ font-family: 'Syne', sans-serif; }}

.stApp {{ background-color: {T["bg"]}; color: {T["text"]}; }}

/* Input */
.stTextInput input {{
    background-color: {T["input_bg"]} !important;
    border: 1px solid {T["border"]} !important;
    color: {T["input_color"]} !important;
    border-radius: 8px;
    font-size: 0.9rem;
}}
.stTextInput input::placeholder {{ color: {T["placeholder"]} !important; }}
.stTextInput input:focus {{
    border-color: {T["accent"]} !important;
    box-shadow: 0 0 0 2px rgba(108, 99, 255, 0.2) !important;
}}

/* Buttons */
.stButton > button {{
    background-color: {T["accent"]};
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    padding: 0.5rem 1.5rem;
    transition: background 0.2s ease;
}}
.stButton > button:hover {{ background-color: {T["accent_hover"]}; color: #ffffff; }}
.stButton > button:disabled {{
    background-color: {T["border"]} !important;
    color: {T["text_muted"]} !important;
}}

/* Cards */
.card {{
    background-color: {T["surface"]};
    border: 1px solid {T["border"]};
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}}
.card h4 {{
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {T["accent"]};
    margin-bottom: 0.5rem;
}}
.card p, .card li {{ color: {T["text"]}; font-size: 0.9rem; line-height: 1.6; }}

/* Verdict badges — theme-aware */
.verdict-badge {{
    display: inline-block;
    padding: 0.3rem 0.9rem;
    border-radius: 20px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    margin-bottom: 1rem;
}}
.verdict-strong    {{ background:{T["v_strong_bg"]};  color:{T["v_strong_text"]};  border:1px solid {T["v_strong_border"]}; }}
.verdict-good      {{ background:{T["v_good_bg"]};    color:{T["v_good_text"]};    border:1px solid {T["v_good_border"]}; }}
.verdict-strategic {{ background:{T["v_strat_bg"]};   color:{T["v_strat_text"]};   border:1px solid {T["v_strat_border"]}; }}
.verdict-borderline{{ background:{T["v_border_bg"]};  color:{T["v_border_text"]};  border:1px solid {T["v_border_border"]}; }}
.verdict-no        {{ background:{T["v_no_bg"]};      color:{T["v_no_text"]};      border:1px solid {T["v_no_border"]}; }}

/* Tags */
.tag {{
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    margin-right: 0.4rem;
    background-color: {T["tag_bg"]};
    color: {T["tag_text"]};
    border: 1px solid {T["tag_border"]};
}}

/* Log area */
.log-box {{
    background-color: {T["log_bg"]};
    border: 1px solid {T["border"]};
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    max-height: 160px;
    overflow-y: auto;
    color: {T["log_text"]};
}}
.log-error   {{ color: #dc2626; }}
.log-success {{ color: #16a34a; }}

/* Score label */
.score-label {{
    font-size: 0.8rem;
    color: {T["text_muted"]};
    margin-bottom: 0.2rem;
    font-family: 'Syne', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

/* Divider */
.divider {{ border:none; border-top:1px solid {T["divider"]}; margin:1.5rem 0; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_url(text: str) -> bool:
    return bool(re.match(r'https?://[^\s]+', text.strip()))


def _verdict_class(verdict: str) -> str:
    return {
        "Strong Match":    "verdict-strong",
        "Good Match":      "verdict-good",
        "Strategic Apply": "verdict-strategic",
        "Borderline":      "verdict-borderline",
        "Not Recommended": "verdict-no",
    }.get(verdict, "verdict-no")


def _render_list(items: list) -> str:
    if not items:
        return f"<p style='color:{T['text_muted']}'>None.</p>"
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def _log(msg: str, level: str = "info"):
    st.session_state.logs.append((msg, level))


def _reset():
    st.session_state.logs = []
    st.session_state.result = None
    st.session_state.save_done = False
    st.session_state.processing = False


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(f"""
<h1 style='font-family:Syne; font-size:1.8rem; color:{T["title"]}; margin-bottom:0;'>
    🎯 Job Hunt AI
</h1>
<p style='color:{T["subtitle"]}; font-size:0.85rem; margin-top:0.1rem; margin-bottom:0.4rem;'>
    Paste a job URL. Get an honest assessment.
</p>
<hr style='border:none; border-top:1px solid {T["divider"]}; margin:0.6rem 0 1rem 0;'>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

url_input = st.text_input(
    label="Job URL",
    placeholder="Please input the url of the interested job position",
    label_visibility="collapsed",
    disabled=st.session_state.processing,
)

analyze_btn = st.button(
    "Analyze",
    disabled=st.session_state.processing,
    use_container_width=False,
)

# ---------------------------------------------------------------------------
# Validation & pipeline trigger
# ---------------------------------------------------------------------------

if analyze_btn:
    url = url_input.strip()
    if not url:
        st.error("Please input the url.")
    elif not _is_valid_url(url):
        st.error("Invalid content, please input the url of the job position.")
    else:
        _reset()
        st.session_state.processing = True
        st.rerun()

# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

if st.session_state.processing and st.session_state.result is None:
    url = url_input.strip()
    error_msg = None

    _log(f"Fetching job content from {url}...", "info")
    raw = fetch_job_content(url)

    if raw is None:
        error_msg = "Could not fetch job content. Please check the URL and try again."
        _log(error_msg, "error")
    elif raw == NOT_A_JOB:
        error_msg = "It's not a job position page, please input the correct url."
        _log(error_msg, "error")
    else:
        _log(f"Job content fetched ({len(raw)} chars).", "success")
        _log("AI analyzing job description against your CV...", "info")
        try:
            result = analyze(raw, url)
            _log(f"Analysis complete — {result.get('apply_verdict')} ({result.get('match_score')}% match).", "success")
            st.session_state.result = result
        except Exception as e:
            error_msg = f"Analysis failed: {e}. Please try again."
            _log(error_msg, "error")

    st.session_state.processing = False
    if error_msg:
        st.session_state.result = {"_error": error_msg}
    st.rerun()

# ---------------------------------------------------------------------------
# Log area
# ---------------------------------------------------------------------------

if st.session_state.logs:
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    log_lines = ""
    for msg, level in st.session_state.logs:
        css = "log-error" if level == "error" else ("log-success" if level == "success" else "")
        log_lines += f"<div class='{css}'>{msg}</div>"
    st.markdown(f"<div class='log-box'>{log_lines}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Error state
# ---------------------------------------------------------------------------

if isinstance(st.session_state.result, dict) and "_error" in st.session_state.result:
    st.error(st.session_state.result["_error"])

# ---------------------------------------------------------------------------
# Result section
# ---------------------------------------------------------------------------

elif st.session_state.result:
    r = st.session_state.result
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # Verdict + tags
    verdict     = r.get("apply_verdict", "Unknown")
    verdict_cls = _verdict_class(verdict)
    relocation  = r.get("relocation_feasibility", "Unknown")
    effort      = r.get("application_effort", "Unknown")

    st.markdown(f"""
    <div class='verdict-badge {verdict_cls}'>{verdict}</div>
    <span class='tag'>📍 Relocation: {relocation}</span>
    <span class='tag'>⚡ Effort: {effort}</span>
    <br><br>
    """, unsafe_allow_html=True)

    # Scores
    match_score     = r.get("match_score", 0)
    alignment_score = r.get("career_alignment", 0)

    def _score_color(score):
        if score >= 75: return "#16a34a"
        if score >= 60: return "#2563eb"
        if score >= 45: return "#d97706"
        return "#dc2626"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style='text-align:center; padding:1rem 0;'>
            <div style='font-family:Syne; font-size:0.7rem; text-transform:uppercase;
                        letter-spacing:0.12em; color:{T["text_muted"]}; margin-bottom:0.3rem;'>
                Match Score
            </div>
            <div style='font-family:Syne; font-size:3rem; font-weight:700;
                        color:{_score_color(match_score)}; line-height:1;'>
                {match_score}<span style='font-size:1.2rem; color:{T["text_muted"]};'>%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style='text-align:center; padding:1rem 0;'>
            <div style='font-family:Syne; font-size:0.7rem; text-transform:uppercase;
                        letter-spacing:0.12em; color:{T["text_muted"]}; margin-bottom:0.3rem;'>
                Career Alignment
            </div>
            <div style='font-family:Syne; font-size:3rem; font-weight:700;
                        color:{_score_color(alignment_score)}; line-height:1;'>
                {alignment_score}<span style='font-size:1.2rem; color:{T["text_muted"]};'>%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Job meta card
    original_url = r.get("original_url", "")
    link_html = f'· <a href="{original_url}" target="_blank" style="color:{T["accent"]};">View original ↗</a>' if original_url else ""
    st.markdown(f"""
    <div class='card'>
        <h4>Position</h4>
        <p style='color:{T["text"]}'><strong>{r.get("job_title","")}</strong> — {r.get("company","")}</p>
        <p style='color:{T["text_muted"]}; font-size:0.8rem;'>
            {r.get("location","")} · {r.get("job_type","")} {link_html}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Full-width text cards
    for label, key in [
        ("Description Summary",  "description_summary"),
        ("Verdict Explanation",  "holistic_explanation"),
        ("Strategic Value",      "strategic_value"),
    ]:
        st.markdown(f"""
        <div class='card'>
            <h4>{label}</h4>
            <p>{r.get(key, "None.")}</p>
        </div>
        """, unsafe_allow_html=True)

    # Two-column list cards
    col_a, col_b = st.columns(2)
    left_cards  = [("Key Requirements","key_requirements"), ("Matching Points","matching_points"), ("Skills to Highlight","skills_to_highlight")]
    right_cards = [("Highlights","highlights"), ("Gaps","gaps"), ("Risk Flags","risk_flags")]

    with col_a:
        for label, key in left_cards:
            st.markdown(f"""
            <div class='card'><h4>{label}</h4>{_render_list(r.get(key,[]))}</div>
            """, unsafe_allow_html=True)

    with col_b:
        for label, key in right_cards:
            st.markdown(f"""
            <div class='card'><h4>{label}</h4>{_render_list(r.get(key,[]))}</div>
            """, unsafe_allow_html=True)

    # Quick CV edits
    st.markdown(f"""
    <div class='card'><h4>Quick CV Edits</h4>{_render_list(r.get("quick_cv_edits",[]))}</div>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Confirm / Save
    # ---------------------------------------------------------------------------

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    if st.session_state.save_done:
        st.success("Done. Saved to Google Sheet.")
    else:
        should_apply = r.get("should_apply", False)
        btn_label    = "Update to Google Sheet" if should_apply else "Update Anyway"
        btn_help     = None if should_apply else "This role was marked as not recommended, but you can still save it."

        if st.button(btn_label, help=btn_help):
            with st.spinner("Saving to Google Sheet..."):
                try:
                    sheet_id = os.getenv("GOOGLE_SHEET_ID")
                    upsert_job(
                        spreadsheet_id=sheet_id,
                        url=r.get("original_url", ""),
                        company=r.get("company", ""),
                        title=r.get("job_title", ""),
                        location=r.get("location", ""),
                        verdict=r.get("apply_verdict", ""),
                        match_score=r.get("match_score", ""),
                        alignment=r.get("career_alignment", ""),
                        relocation=r.get("relocation_feasibility", ""),
                        effort=r.get("application_effort", ""),
                        description_summary=r.get("description_summary", ""),
                        key_requirements=r.get("key_requirements", []),
                        matching_points=r.get("matching_points", []),
                        gaps=r.get("gaps", []),
                        risk_flags=r.get("risk_flags", []),
                        skills_to_highlight=r.get("skills_to_highlight", []),
                        quick_cv_edits=r.get("quick_cv_edits", []),
                        strategic_value=r.get("strategic_value", ""),
                        holistic_explanation=r.get("holistic_explanation", ""),
                    )
                    st.session_state.save_done = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving to sheet: {e}. Please try again.")