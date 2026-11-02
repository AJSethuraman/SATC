"""Build the credit-review procedure: Markdown source and one self-contained HTML (screenshots embedded), then a PDF.

    python3 workpaper-studio/docs/walkthrough/build_procedure.py

The steps are the route walked on 2 November 2026; the screenshots are from the second walk that day, after the fixes. Walk it again after a change and
each step either matches its picture or does not.
"""
import base64
import shutil
import subprocess
from html import escape as E
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "credit-review-2026-11-02"
MD = HERE.parent / "PROCEDURE-credit-review.md"
HTML = SHOTS / "PROCEDURE-credit-review-2026-11-02.html"
PDF = SHOTS / "PROCEDURE-credit-review-2026-11-02.pdf"

# (part, who, title, do, correct, [images])
STEPS = [
    ("Set up the tool", "Anyone", "Sign in",
     "Open the app (http://127.0.0.1:5077). Choose your name on “Who is working?”.",
     "A list of five people, each with what they can do. Choosing a name is not a password check; it is how the record knows who did what.",
     ["step-01-sign-in.png"]),
    ("Set up the tool", "Designer (M. Okafor)", "Propose the tool for publishing",
     "Go to **Tools**. On the Credit file review row, click **Propose for publishing**.",
     "The row's state changes to “Proposed by M. Okafor, waiting for an approver”. You will not see an Approve button: nobody approves their own proposal.",
     ["step-02-tools-not-proposed-zoom.png", "step-03-proposed.png"]),
    ("Set up the tool", "Approver (K. Owens)", "Read the tool and approve it",
     "Sign in as the approver. On **Tools**, click the tool's name to read its outline, and **Preview it filled in** to see it working on the pack's own example. Then go back and click **Approve**.",
     "The preview says nothing in it is saved. After approval the state reads “Published: proposed by M. Okafor, approved by K. Owens”. New cases now use this version; the fingerprint identifies it exactly.",
     ["step-04-approver-reads-outline.png", "step-04b-approver-previews.png", "step-05-approve-zoom.png", "step-06-published.png"]),
    ("Set up the tool", "Admin (M. Okafor)", "Confirm the organization's limit",
     "Go to **Settings**. The debt-to-income limit is *Not confirmed*. Type your organization's limit (40 for this demonstration) and click **Confirm**.",
     "State reads “Confirmed by M. Okafor” with the date, and a new version appears under Versions. Until a limit is confirmed, no result is tested against it. The 40% is fictional.",
     ["step-07-settings-unconfirmed-zoom.png", "step-08-limit-confirmed.png"]),
    ("Prepare the case", "Preparer (A. Rivera)", "Start a case",
     "Sign in as the preparer. On **Cases**, click **New credit file review**.",
     "A new case opens (CFR-0001). Every required box is amber. The strip says Ready for review: No, Still missing: 19.",
     ["step-09-cases-start-zoom.png", "step-10-new-case-zoom.png", "step-10-new-case.png"]),
    ("Prepare the case", "Preparer", "Fill the detail panels",
     "Fill Tester, Test date, Reviewer, Quarter end, Scope, Borrower name, Security and New money request. Each entry saves when you leave the box.",
     "Each panel's footer turns to a green Complete. “Saved” appears at the foot of the page. Still missing drops to 12. "
     "Tab moves on as you would expect; each box's small N/A button is one Tab stop of its own.",
     ["step-11-details-filled-zoom.png"]),
    ("Prepare the case", "Preparer", "Enter the facilities",
     "Enter each facility on its own row: type, rating, commitment, outstanding. A new empty row appears as you use the last one.",
     "A row that is started but incomplete shows its missing box in amber, the section says “1 missing”, and the total under that column reads "
     "**Not calculated** until the gap is filled. When every row is complete the footer reads Complete.",
     ["step-12-facility-row-incomplete-zoom.png", "step-13-facilities-complete-zoom.png"]),
    ("Prepare the case", "Preparer", "Answer the test questions",
     "Rate each question from the list. Open *How to test* under a question to read its steps. Write a comment where you have one.",
     "Ratings show in green, amber or red. A rating of Partially or Not effective makes the comment box amber and required until you write one. "
     "Questions that depend on an answer (for example 5.02, only for new money) say so under the number.",
     ["step-14-question-needs-comment-zoom.png"]),
    ("Prepare the case", "Preparer", "Complete the supporting analysis",
     "Click **Analysis** in the band. Enter income sources, existing debts and the proposed monthly payment. The cash flow and collateral tables are optional.",
     "While any input is missing, debt-to-income reads **Not calculated**, never 0. The reason is listed under “Why there is no result”. "
     "When every input is in, the result shows (51.3% here) with its verdict against the confirmed limit. A zero payment is disclosed, not hidden.",
     ["step-15-analysis-empty-zoom.png", "step-16-dti-not-calculated-zoom.png", "step-17-dti-above-limit-zoom.png"]),
    ("Prepare the case", "Preparer", "Record an exception for a result above the limit",
     "Under the result, choose a reason, explain it, and click **Record exception**.",
     "The exception is listed beside the result, “Waiting for the reviewer to acknowledge it”. The result itself does not change.",
     ["step-18-record-exception-zoom.png", "step-19-exception-recorded-zoom.png"]),
    ("Prepare the case", "Preparer", "Submit for review",
     "Click **Submit for review**. If anything is missing you land on the release check with a message; click **Go to it** on each line, fill it, and submit again.",
     "When it goes through, the Status chip reads **In review** and your boxes lock. Every line on the release check is OK except the exception (waiting for the reviewer) and the approval.",
     ["step-20-submit-refused-zoom.png", "step-22-conclusion-zoom.png", "step-23-submitted.png"]),
    ("Review", "Reviewer (D. Patel)", "Open the case and raise a point",
     "Sign in as the reviewer. The case is under **Waiting for your review**; open it. Under the section concerned, write the point and click **Raise point**.",
     "Your boxes are read-only: a reviewer never changes the preparer's entries. The point shows as Open with your name and the time.",
     ["step-24-reviewer-home-zoom.png", "step-25-reviewer-case-zoom.png", "step-26-raise-point-zoom.png", "step-27-point-raised-zoom.png"]),
    ("Review", "Reviewer", "Acknowledge the exception",
     "Clicking **Approve** now is refused, and the message names what is open. Go to **Analysis** and click **Acknowledge** on the exception.",
     "The exception reads “Acknowledged by D. Patel” with the time.",
     ["step-28-approve-refused-zoom.png", "step-29-acknowledge-zoom.png"]),
    ("Review", "Preparer", "Answer the point",
     "Sign in as the preparer. Your Cases list shows “1 (waiting for your answer)” under Open points. Open the case: a banner at the top links to the point. Write your answer under it and click **Answer**.",
     "Your answer appears under the point with your name and the time.",
     ["step-30-preparer-home-zoom.png", "step-31-answer-point-zoom.png"]),
    ("Approve and release", "Reviewer", "Clear the point, approve, release",
     "Sign in as the reviewer. Click **Clear point P1**, then **Approve**, then **Release**.",
     "The point reads Cleared. Each action confirms itself in a green banner. The status goes to Approved, then Released, and Outputs lists the released files, each with its SHA-256 fingerprint: "
     "the data feed (JSON and CSV) and the workbook. The workbook has an Exceptions and review sheet; the borrower's name is masked in every released file.",
     ["step-32-point-cleared-zoom.png", "step-33-approved.png", "step-35-outputs-zoom.png"]),
    ("Approve and release", "Anyone", "Read the record",
     "Click **History**.",
     "Every entry and every action, newest first, with who and when. Nothing in it can be changed or removed; the case on screen is rebuilt from it.",
     ["step-36-history.png"]),
]

ROUTE = [("Tools", "propose · approve"), ("Settings", "confirm limit"), ("Workpaper", "details · facilities · questions"),
         ("Analysis", "inputs · result · exception"), ("Check", "submit"), ("Review", "point · acknowledge"),
         ("Answer", "preparer replies"), ("Approve", "clear · approve"), ("Release", "files fingerprinted")]


def md():
    out = ["# Procedure: a credit file review, from tool to released record", "",
           "*Walked through the screens on 2 November 2026. Synthetic people and data; the limit and the method are fictional demonstrations.*",
           "*Rendered copy with every screenshot embedded: `walkthrough/credit-review-2026-11-02/PROCEDURE-credit-review-2026-11-02.pdf`.*", "",
           "**The route:** " + " → ".join(f"{a} ({b})" for a, b in ROUTE), ""]
    part = None
    for i, (pt, who, title, do, ok, imgs) in enumerate(STEPS, 1):
        if pt != part:
            out += [f"## {pt}", ""]
            part = pt
        out += [f"### {i}. {title}", f"*{who}*", "", f"**Do.** {do}", "", f"**A correct screen.** {ok}", ""]
        out += [f"![{title}](walkthrough/credit-review-2026-11-02/{im})" for im in imgs] + [""]
    return "\n".join(out)


def b64(name):
    return "data:image/png;base64," + base64.b64encode((SHOTS / name).read_bytes()).decode()


def inline(s):
    import re
    s = E(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)


def route_svg():
    w, h, n = 1000, 150, len(ROUTE)
    bw = (w - 20) / n
    parts = []
    for i, (a, b) in enumerate(ROUTE):
        x = 10 + i * bw
        parts.append(f'<rect x="{x + 4:.0f}" y="20" width="{bw - 22:.0f}" height="58" rx="2" fill="#2B3A55"/>'
                     f'<text x="{x + bw / 2 - 9:.0f}" y="54" fill="#fff" font-size="12" font-weight="700" text-anchor="middle">{E(a)}</text>'
                     + "".join(f'<text x="{x + bw / 2 - 9:.0f}" y="{96 + 13 * k}" fill="#3D3A35" font-size="11" text-anchor="middle">{E(t)}</text>' for k, t in enumerate(b.split(" · "))))
        if i < n - 1:
            parts.append(f'<path d="M{x + bw - 18:.0f} 49 l14 0 m-5 -5 l5 5 l-5 5" stroke="#8C857A" stroke-width="2" fill="none"/>')
    who = [("Designer, approver, admin", 0, 2), ("Preparer", 2, 5), ("Reviewer and preparer", 5, 7), ("Reviewer", 7, 9)]
    for lab, a, b in who:
        x1, x2 = 10 + a * bw + 4, 10 + b * bw - 18
        parts.append(f'<path d="M{x1:.0f} 130 L{x2:.0f} 130" stroke="#CF9A33" stroke-width="3"/><text x="{(x1 + x2) / 2:.0f}" y="146" font-size="11" text-anchor="middle" fill="#8A5A00">{E(lab)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="The route through the screens" font-family="Arial">{"".join(parts)}</svg>'


def html():
    css = """body{font:14px/1.45 Arial,sans-serif;color:#262421;background:#fff;max-width:900px;margin:0 auto;padding:24px}
h1{font-size:24px;margin:0 0 4px;color:#2B3A55}h2{font-size:18px;color:#fff;background:#38517F;padding:6px 10px;margin:28px 0 10px;break-after:avoid}
.step{break-inside:avoid-page;border-top:1px solid #D3CFC8;padding:10px 0 16px}.step h3{margin:0 0 2px;font-size:16px;color:#2B3A55}
.who{color:#8A5A00;font-size:12px;font-weight:700;text-transform:uppercase;margin-bottom:6px}.lab{font-weight:700}
img{max-width:100%;border:1px solid #BDB6A9;margin:6px 0;display:block}.meta{color:#6D6A63;font-size:12px}
.note{background:#F6E3B2;padding:8px 10px;margin:12px 0}@page{margin:14mm}"""
    out = [f"<!doctype html><html lang=en><head><meta charset=utf-8><title>Procedure: credit file review</title><style>{css}</style></head><body>",
           "<h1>A credit file review, from tool to released record</h1>",
           "<p class=meta>Workpaper Studio · walked through the screens on 2 November 2026 · synthetic people and data · the limit and method are fictional demonstrations</p>",
           "<p>Four people take part: a <b>designer</b> who proposes the tool, an <b>approver</b> who approves it, an <b>admin</b> who confirms the organization's limit, "
           "a <b>preparer</b> who completes the case, and a <b>reviewer</b> who reviews, approves and releases it. Nobody approves their own work.</p>",
           "<h2 style='margin-top:14px'>The route</h2>", route_svg(),
           "<p class=note>A red ring marks the control each step is about. Where the thing to read is small, a close-up is shown first and the full screen after it.</p>"]
    part = None
    for i, (pt, who, title, do, ok, imgs) in enumerate(STEPS, 1):
        if pt != part:
            out.append(f"<h2>{E(pt)}</h2>")
            part = pt
        pics = "".join(f'<img src="{b64(im)}" alt="{E(title)}">' for im in imgs)
        out.append(f'<div class=step><h3>{i}. {E(title)}</h3><div class=who>{E(who)}</div><p><span class=lab>Do.</span> {inline(do)}</p>'
                   f'<p><span class=lab>A correct screen.</span> {inline(ok)}</p>{pics}</div>')
    out.append("</body></html>")
    return "".join(out)


def main():
    MD.write_text(md())
    HTML.write_text(html())
    chrome = shutil.which("chromium") or "/opt/pw-browsers/chromium"
    cands = [chrome] + [str(p) for p in Path("/opt/pw-browsers").glob("chromium*/chrome-linux*/chrome")]
    for c in cands:
        if Path(c).is_file():
            subprocess.run([c, "--headless=new", "--no-sandbox", "--no-pdf-header-footer", f"--print-to-pdf={PDF}", HTML.as_uri()],
                           check=True, capture_output=True, timeout=120)
            break
    print(MD, HTML, PDF, sep="\n")


if __name__ == "__main__":
    main()
