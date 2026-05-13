NAVY = "#0B1F3A"
GOLD = "#C9A227"
GRAY_BG = "#F5F6F8"
GRAY_BORDER = "#D1D5DB"
GREEN = "#166534"
AMBER = "#92400E"
RED = "#991B1B"

STATUS_COLORS = {
    "Ready": GREEN,
    "Success": GREEN,
    "Needs Review": AMBER,
    "Warning": AMBER,
    "Blocked": RED,
    "Error": RED,
}

def inject_streamlit_css(st):
    st.markdown(f"""
    <style>
    .main .block-container {{padding-top: 1.5rem;}}
    h1, h2, h3 {{color: {NAVY};}}
    .occam-hero {{background:{NAVY}; color:white; padding:1.25rem 1.5rem; border-radius:14px; border-left:8px solid {GOLD}; margin-bottom:1rem;}}
    .occam-card {{background:{GRAY_BG}; border:1px solid {GRAY_BORDER}; padding:1rem; border-radius:12px; margin:.5rem 0;}}
    .occam-status {{font-weight:700; padding:.3rem .6rem; border-radius:999px; color:white; display:inline-block;}}
    div.stButton > button:first-child {{background:{GOLD}; color:{NAVY}; border:0; font-weight:700;}}
    </style>
    """, unsafe_allow_html=True)

def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, NAVY)
    return f"<span class='occam-status' style='background:{color}'>{status}</span>"
