COLORS={"Ready":"#C6EFCE","Complete":"#C6EFCE","QC Approved":"#C6EFCE","Warning":"#FFEB9C","Needs Review":"#FFEB9C","Blocked":"#FFC7CE","Finding":"#FFC7CE","Not Started":"#D9E2F3"}
def status_badge(status):
    color=COLORS.get(status,"#D9E2F3")
    return f"<span style='background:{color};padding:0.25rem 0.5rem;border-radius:0.25rem;font-weight:700'>{status}</span>"
def inject_css(st):
    st.markdown("""<style>.stApp {background:#f7f8fa}.metric-card{border:1px solid #d0d7de;border-left:6px solid #1F4E78;padding:1rem;background:white}.navy{color:#1F4E78}.gold{color:#D9A441}</style>""", unsafe_allow_html=True)
def next_action(counts):
    if counts.get('Blocked',0): return "Resolve blocked loans before final export."
    if counts.get('Warning',0): return "Review warning loans and document findings/evidence."
    if counts.get('Ready',0): return "Select a loan and complete the linesheet."
    return "Set up an engagement and upload a loan tape."
