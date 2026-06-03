from pathlib import Path
import pandas as pd
import streamlit as st
from linesheet_builder.db import init_db, get_connection, create_or_get_client, create_engagement
from linesheet_builder.sample_data import seed_demo, create_demo_loan_tape
from linesheet_builder.import_engine import load_loan_tape, save_raw_import, create_import_batch
from linesheet_builder.mapping_engine import suggest_mappings, apply_mapping, save_mapping_profile, load_mapping_profile, persist_loan_records
from linesheet_builder.template_engine import load_template_yaml, get_applicable_questions, discover_templates, load_template
from linesheet_builder.validation_engine import validate_loan_records, persist_validation_issues, validation_summary_table
from linesheet_builder.review_engine import create_review_cases, save_answer, calculate_completion_status, set_review_status
from linesheet_builder.export_engine import generate_excel_linesheet, generate_data_mart_csv, generate_exception_report_csv, generate_audit_log_csv
from linesheet_builder.dti_engine import load_dti_config, load_dti_inputs, save_dti_inputs, compute_dti, block_lines
from linesheet_builder.cash_flow_engine import load_cash_flow_config, load_cash_flow_inputs, save_cash_flow_inputs, compute_cash_flow, source_lines
from linesheet_builder.ui_helpers import inject_css, status_badge, next_action

ROOT=Path(__file__).parent; DB=ROOT/'data'/'app.db'; TEMPLATE_PATH=ROOT/'configs'/'templates'/'commercial_linesheet_v1.yaml'
st.set_page_config(page_title="Linesheet Builder", layout="wide")
inject_css(st); init_db(DB); seed_demo(DB)
conn=get_connection(DB)
st.sidebar.title("Linesheet Builder")
page=st.sidebar.radio("Navigation", ["Dashboard","Setup","Templates","Upload","Mapping","Validation","Review","Cash Flow","DTI / ATR","Export","Audit"])
engagements=pd.read_sql_query("SELECT e.*, c.client_name FROM engagements e JOIN clients c ON e.client_id=c.client_id ORDER BY e.engagement_id DESC", conn)
eng_id=int(st.sidebar.selectbox("Engagement", engagements.engagement_id, format_func=lambda x: f"{engagements[engagements.engagement_id==x].iloc[0].client_name} / {x}")) if not engagements.empty else None
eng=engagements[engagements.engagement_id==eng_id].iloc[0].to_dict() if eng_id else {}
TEMPLATES=discover_templates()
try:
    template=load_template(eng.get('template_id') or 'commercial_linesheet_v1')
except Exception:
    template=load_template_yaml(TEMPLATE_PATH)
st.sidebar.caption(f"Template: {template.template_name}")
st.sidebar.markdown("---")
st.sidebar.caption("Local pilot. No credit scoring. No underwriting decisions.")

def get_loans(): return pd.read_sql_query("SELECT * FROM loan_records WHERE engagement_id=?", conn, params=(eng_id,)) if eng_id else pd.DataFrame()
def get_cases(): return pd.read_sql_query("SELECT rc.review_case_id, lr.loan_id, lr.borrower_name, rc.status, lr.validation_status FROM review_cases rc JOIN loan_records lr ON rc.loan_record_id=lr.loan_record_id WHERE rc.engagement_id=?", conn, params=(eng_id,)) if eng_id else pd.DataFrame()

if page=="Dashboard":
    st.title("Linesheet Builder")
    st.write("Professional, audit-ready commercial loan linesheets generated from controlled loan tape, validation, review, and export workflows.")
    loans=get_loans(); counts=loans.validation_status.value_counts().to_dict() if not loans.empty else {}
    cols=st.columns(6)
    for c,label,val in zip(cols,["Client","Review Period","Template","Loans","Ready","Blocked"],[eng.get('client_name','Not selected'),eng.get('review_period',''),template.template_name,len(loans),counts.get('Ready',0),counts.get('Blocked',0)]): c.metric(label,val)
    st.markdown(f"**Current status:** {status_badge(eng.get('status','Not Started'))}", unsafe_allow_html=True)
    st.info("Next action: " + next_action(counts))
    st.subheader("Workflow")
    st.write("Use the sidebar: Setup → Upload → Mapping → Validation → Review → Export → Audit.")
    if not loans.empty: st.dataframe(loans[["loan_id","borrower_name","product_type","outstanding_balance","validation_status"]], use_container_width=True)

elif page=="Setup":
    st.title("Client / Engagement Setup")
    st.write("Create or select a local engagement. Setup is persisted in SQLite.")
    with st.form("setup"):
        client=st.text_input("Client name", "Demo Bank")
        period=st.text_input("Review period", "Q4 2025")
        review_type=st.text_input("Review type", "Commercial Loan Review")
        tmpl_ids=list(TEMPLATES.keys()) or ["commercial_linesheet_v1"]
        tmpl=st.selectbox("Template", tmpl_ids, format_func=lambda x: TEMPLATES.get(x,{}).get("name",x))
        reviewer=st.text_input("Reviewer name", "Demo Reviewer")
        qc=st.text_input("QC reviewer name", "Demo QC")
        st.text_input("Output folder", str(ROOT/'outputs'))
        if st.form_submit_button("Save engagement"):
            cid=create_or_get_client(conn, client); new_id=create_engagement(conn,cid,period,review_type,tmpl,reviewer,qc)
            st.success(f"Engagement saved: {new_id}")

elif page=="Templates":
    st.title("Linesheet Templates")
    st.write("Custom linesheet templates discovered from `configs/templates/`. New templates are produced en masse with the template builder (`linesheet_builder/template_builder.py`) — a few lines of spec per sheet.")
    reg=discover_templates()
    rows=[]
    for tid, meta in reg.items():
        try:
            t=load_template(tid); rows.append({"template_id":tid,"name":meta["name"],"version":meta["version"],"sections":len(t.sections),"questions":sum(len(s.questions) for s in t.sections)})
        except Exception as e:
            rows.append({"template_id":tid,"name":meta["name"],"version":meta["version"],"sections":0,"questions":f"error: {e}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    if reg:
        sel=st.selectbox("Preview template", list(reg.keys()), format_func=lambda x: reg[x]["name"])
        t=load_template(sel)
        st.caption(f"{t.template_name} · v{t.version} · {len(t.sections)} sections")
        for s in t.sections:
            with st.expander(f"{s.display_order}. {s.section_name}  ({len(s.questions)} questions)"):
                st.dataframe(pd.DataFrame([{"#":q.display_order,"id":q.question_id,"question":q.question_text,"type":q.answer_type,"required":q.required,"rule":q.exception_if or q.warning_if or q.applies_if or ""} for q in s.questions]), use_container_width=True)

elif page=="Upload":
    st.title("Upload Loan Tape")
    st.write("Upload CSV/XLSX or load the included demo tape. A timestamped raw copy is preserved.")
    uploaded=st.file_uploader("Loan tape", type=["csv","xlsx"])
    if st.button("Load demo loan tape"):
        st.session_state.file_path=create_demo_loan_tape(); st.success(st.session_state.file_path)
    if uploaded:
        raw=save_raw_import(uploaded); st.session_state.file_path=raw
    if st.session_state.get('file_path'):
        df=load_loan_tape(st.session_state.file_path); st.write(f"Rows: {len(df)} | Columns: {len(df.columns)}"); st.dataframe(df.head(10), use_container_width=True)
        if st.button("Create import batch"):
            st.session_state.import_batch_id=create_import_batch(conn, eng_id, Path(st.session_state.file_path).name, st.session_state.file_path, df, eng.get('reviewer_name','user'))
            st.success(f"Import batch created: {st.session_state.import_batch_id}")

elif page=="Mapping":
    st.title("Mapping")
    st.write("Confirm incoming loan tape columns against the standard schema. Mapping profiles are reusable YAML plus SQLite records.")
    path=st.session_state.get('file_path') or str(ROOT/'data'/'demo_loan_tape.xlsx')
    df=load_loan_tape(path); suggestions=suggest_mappings(df.columns)
    mappings={}
    cols=[""]+list(__import__('linesheet_builder.mapping_engine').mapping_engine.STANDARD_FIELDS)
    with st.form("mapping"):
        for col,sug in suggestions.items(): mappings[col]=st.selectbox(col, cols, index=cols.index(sug) if sug in cols else 0)
        if st.form_submit_button("Confirm mapping and normalize"):
            profile={"client_name":eng.get('client_name'),"template_id":template.template_id,"mappings":mappings}
            save_mapping_profile(profile, ROOT/'configs'/'mappings'/'last_mapping.yaml', conn, int(eng['client_id']), template.template_id, eng.get('reviewer_name','user'))
            mapped=apply_mapping(df, profile)
            batch_id=st.session_state.get('import_batch_id') or create_import_batch(conn, eng_id, Path(path).name, path, df, eng.get('reviewer_name','user'))
            ids=persist_loan_records(conn, eng_id, batch_id, mapped, eng.get('reviewer_name','user'))
            st.success(f"Normalized {len(ids)} loan records.")

elif page=="Validation":
    st.title("Validation Results")
    loans=get_loans()
    if loans.empty: st.warning("No normalized loans yet. Complete Upload and Mapping first.")
    else:
        if st.button("Run validation"):
            res=validate_loan_records(loans.to_dict('records'), template); persist_validation_issues(conn,res,eng_id,eng.get('reviewer_name','user')); create_review_cases(conn, eng_id, eng.get('reviewer_name'), eng.get('qc_reviewer_name')); st.session_state.validation=validation_summary_table(res)
        if 'validation' in st.session_state: st.dataframe(st.session_state.validation, use_container_width=True)
        else: st.dataframe(loans[["loan_id","borrower_name","product_type","outstanding_balance","validation_status"]], use_container_width=True)

elif page=="Review":
    st.title("Review Workspace")
    cases=get_cases()
    if cases.empty: st.warning("Run validation to create review cases.")
    else:
        rcid=int(st.selectbox("Select loan", cases.review_case_id, format_func=lambda x: f"{cases[cases.review_case_id==x].iloc[0].loan_id} - {cases[cases.review_case_id==x].iloc[0].borrower_name}"))
        row=conn.execute("SELECT rc.*, lr.* FROM review_cases rc JOIN loan_records lr ON rc.loan_record_id=lr.loan_record_id WHERE rc.review_case_id=?",(rcid,)).fetchone(); loan={k:row[k] for k in row.keys()}
        st.markdown(f"### {loan['borrower_name']} | Loan {loan['loan_id']} | {status_badge(loan['status'])}", unsafe_allow_html=True)
        st.write(f"Product: {loan['product_type']} | Balance: {loan['outstanding_balance']} | Risk rating: {loan['risk_rating']} | Officer: {loan['officer']}")
        status=calculate_completion_status(conn, rcid, loan, template); st.progress(status['completion_pct']/100, text=f"Review completion: {status['completion_pct']}%")
        for sec in template.sections:
            qs=[q for s,q in get_applicable_questions(loan, template) if s.section_id==sec.section_id]
            if not qs: continue
            with st.expander(sec.section_name, expanded=False):
                for q in qs:
                    st.markdown(f"**{q.question_id}. {q.question_text}** {'(Required)' if q.required else ''}")
                    if q.source_field: st.caption(f"Source {q.source_field}: {loan.get(q.source_field)}")
                    key=f"{rcid}_{q.question_id}"
                    if q.answer_type=="yes_no_na": ans=st.selectbox("Answer", ["","Yes","No","N/A"], key=key)
                    elif q.answer_type=="long_text": ans=st.text_area("Answer", key=key)
                    elif q.answer_type in ("number","currency","percent"): ans=st.number_input("Answer", value=float(loan.get(q.source_field) or 0) if q.source_field and str(loan.get(q.source_field) or '').replace('.','',1).isdigit() else 0.0, key=key)
                    elif q.answer_type=="date": ans=st.text_input("Answer (YYYY-MM-DD)", str(loan.get(q.source_field) or ""), key=key)
                    elif q.answer_type=="multi_select": ans=", ".join(st.multiselect("Answer", q.options, key=key))
                    elif q.answer_type=="select": ans=st.selectbox("Answer", [""]+q.options, key=key)
                    else: ans=st.text_input("Answer", str(loan.get(q.source_field) or ""), key=key)
                    comment=st.text_input("Reviewer comment", key=key+"_c")
                    evidence=st.selectbox("Evidence status", ["Not Required","Needed","Attached","Waived"], key=key+"_e")
                    if st.button("Save answer", key=key+"_s"):
                        result=save_answer(conn, rcid, loan, sec, q, ans, comment, evidence, eng.get('reviewer_name','user'), template.template_id, template.version); st.success(f"Saved: {result['status']}")
        st.subheader("Status controls")
        new_status=st.selectbox("Review case status", ["In Review","Needs Review","Blocked","Ready for QC","QC Returned","QC Approved","Finalized"])
        if st.button("Update status"): set_review_status(conn, rcid, new_status); st.success("Status updated")
        if status['blockers']: st.error("Export blockers: " + "; ".join(status['blockers']))

elif page=="Cash Flow":
    st.title("Cash Flow / Income Analysis")
    st.write("Broad, gross (pre-tax) income analysis. Enter up to two periods per source and pick a basis (Annual/Monthly) and method (Latest / Average / Lower of). Salaried income: one period + Latest. Self-employed / variable: two periods + Average. K-1 business owners qualify on cash distributions; pro-rata business income is captured as reference only.")
    cases=get_cases()
    if cases.empty:
        st.warning("Run validation to create review cases.")
    else:
        rcid=int(st.selectbox("Loan / review case", cases.review_case_id, format_func=lambda x: f"{cases[cases.review_case_id==x].iloc[0].loan_id} - {cases[cases.review_case_id==x].iloc[0].borrower_name}"))
        loan_id=cases[cases.review_case_id==rcid].iloc[0].loan_id
        cfg=load_cash_flow_config(); saved=load_cash_flow_inputs(conn, rcid)
        db, dm = cfg["default_basis"], cfg["default_method"]
        with st.form("cash_flow"):
            values={}; last=None
            for section, key, label, role in source_lines(cfg):
                if section!=last: st.subheader(section); last=section
                sv=saved.get(key) or {}
                c=st.columns([3,1.3,1.3,1.2,1.4])
                c[0].markdown(f"{'_'+label+'_' if role=='reference' else label}")
                p1=c[1].number_input("Period 1", min_value=0.0, value=float(sv.get("period1") or 0.0), step=1000.0, key=f"cf_{rcid}_{key}_p1", label_visibility="collapsed")
                p2=c[2].number_input("Period 2", min_value=0.0, value=float(sv.get("period2") or 0.0), step=1000.0, key=f"cf_{rcid}_{key}_p2", label_visibility="collapsed")
                basis=c[3].selectbox("Basis", cfg["bases"], index=cfg["bases"].index(sv.get("basis") or db), key=f"cf_{rcid}_{key}_b", label_visibility="collapsed")
                method=c[4].selectbox("Method", cfg["methods"], index=cfg["methods"].index(sv.get("method") or dm), key=f"cf_{rcid}_{key}_m", label_visibility="collapsed")
                values[key]={"period1":p1,"period2":p2,"basis":basis,"method":method}
            submitted=st.form_submit_button("Save & calculate")
        if submitted:
            save_cash_flow_inputs(conn, rcid, values, eng.get('reviewer_name','user'), loan_id=loan_id)
        result=compute_cash_flow(values if submitted else saved, cfg)
        st.markdown("---"); st.subheader("Qualifying income")
        m=st.columns(3)
        m[0].metric("Total qualifying monthly income", f"${result['qualifying_monthly']:,.0f}")
        m[1].metric("Total qualifying annual income", f"${result['qualifying_annual']:,.0f}")
        m[2].metric("Business income (reference)", f"${result['business_income_reference_monthly']:,.0f}/mo")
        st.caption("Qualifying monthly income can be used as the income basis on the DTI / ATR worksheet.")

elif page=="DTI / ATR":
    st.title("Ability-to-Repay (DTI) Worksheet")
    st.write("Enter monthly amounts. Front-end and back-end DTI, total obligations and residual income calculate automatically and are scored against ability-to-repay guidelines. The same worksheet is exported as a live-formula tab in the Excel linesheet.")
    cases=get_cases()
    if cases.empty:
        st.warning("Run validation to create review cases.")
    else:
        rcid=int(st.selectbox("Loan / review case", cases.review_case_id, format_func=lambda x: f"{cases[cases.review_case_id==x].iloc[0].loan_id} - {cases[cases.review_case_id==x].iloc[0].borrower_name}"))
        loan_id=cases[cases.review_case_id==rcid].iloc[0].loan_id
        cfg=load_dti_config(); saved=load_dti_inputs(conn, rcid)
        blocks=["income","housing","debts"]+(["deductions"] if cfg.get("deductions") else [])
        with st.form("dti"):
            values={}
            for block in blocks:
                st.subheader(cfg[block]["section_name"])
                fcols=st.columns(2)
                for i,(key,label) in enumerate(block_lines(cfg, block)):
                    with fcols[i%2]:
                        values[key]=st.number_input(label, min_value=0.0, value=float(saved.get(key) or 0.0), step=50.0, key=f"dti_{rcid}_{key}")
            submitted=st.form_submit_button("Save & calculate")
        if submitted:
            save_dti_inputs(conn, rcid, values, eng.get('reviewer_name','user'), loan_id=loan_id)
        result=compute_dti(values if submitted else saved, cfg)
        st.markdown("---"); st.subheader("Ability-to-repay results")
        m=st.columns(4)
        m[0].metric("Monthly gross income", f"${result['total_income']:,.0f}")
        m[1].metric("Front-end DTI", f"{result['front_end_dti']:.1f}%", help=f"Target ≤ {result['front_end_target']:.0f}%")
        m[2].metric("Back-end DTI", f"{result['back_end_dti']:.1f}%", help=f"Target ≤ {result['back_end_target']:.0f}%, max {result['back_end_max']:.0f}%")
        m[3].metric("Residual income", f"${result['residual_income']:,.0f}")
        if result.get('total_withholding'):
            n=st.columns(4)
            n[0].metric("Payroll withholding", f"${result['total_withholding']:,.0f}")
            n[1].metric("Net monthly income", f"${result['net_income']:,.0f}")
            n[2].metric("Net residual income", f"${result['net_residual_income']:,.0f}")
        st.markdown(f"**ATR assessment:** {status_badge(result['severity'] or 'Complete')} &nbsp; {result['assessment']}", unsafe_allow_html=True)

elif page=="Export":
    st.title("Export Center")
    cases=get_cases()
    if cases.empty: st.warning("No review cases available.")
    else:
        rcid=int(st.selectbox("Review case", cases.review_case_id, format_func=lambda x: f"{cases[cases.review_case_id==x].iloc[0].loan_id} - {cases[cases.review_case_id==x].iloc[0].borrower_name}"))
        override=st.text_input("Override reason (optional; logged if used)")
        if st.button("Generate Excel linesheet"):
            try: st.success(generate_excel_linesheet(conn, rcid, template, generated_by=eng.get('reviewer_name','user'), override_reason=override or None).file_path)
            except Exception as e: st.error(str(e))
        if st.button("Generate data mart CSV"): st.success(generate_data_mart_csv(conn, rcid, template, generated_by=eng.get('reviewer_name','user')).file_path)
        if st.button("Generate exception report CSV"): st.success(generate_exception_report_csv(conn).file_path)
        if st.button("Generate audit log CSV"): st.success(generate_audit_log_csv(conn).file_path)

elif page=="Audit":
    st.title("Audit Log")
    st.write("Append-only audit trail for key import, mapping, validation, review, exception, and export actions.")
    st.dataframe(pd.read_sql_query("SELECT * FROM audit_log ORDER BY audit_id DESC", conn), use_container_width=True)
conn.close()
