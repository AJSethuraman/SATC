from __future__ import annotations
from pathlib import Path
from .models import Template, TemplateSection, TemplateQuestion
from .rules_engine import evaluate_rule

def _q(**kw): return TemplateQuestion(**kw)
def _template_data():
    sections=[]
    def sec(sid,name,order,qs): sections.append(TemplateSection(section_id=sid,section_name=name,display_order=order,questions=[_q(**q) for q in qs]))
    base=lambda **k: {**{'required':False,'help_text':'Review and document support.','data_mart_field':k.get('question_id','').lower(),'export_label':k.get('question_text','')}, **k}
    sec('borrower_relationship','Borrower / Relationship',1,[base(display_order=1,question_id='BR1',question_text='Is the borrower name documented and consistent with the loan tape?',answer_type='yes_no_na',required=True,source_field='borrower_name',exception_if='answer == "No"',severity='Finding',evidence_required_if='answer == "No"'),base(display_order=2,question_id='BR2',question_text='Relationship overview',answer_type='long_text',source_field='borrower_name'),base(display_order=3,question_id='BR3',question_text='Is borrower high risk based on risk rating?',answer_type='yes_no_na',required=True,applies_if='source.risk_rating >= 7',warning_if='answer == "Yes"',severity='Needs Review')])
    sec('loan_terms','Loan Terms',2,[base(display_order=1,question_id='LT1',question_text='Is the outstanding balance supported?',answer_type='yes_no_na',required=True,source_field='outstanding_balance',exception_if='answer == "No"',severity='Finding',evidence_required_if='answer == "No"'),base(display_order=2,question_id='LT2',question_text='Commitment amount',answer_type='currency',required=True,source_field='commitment_amount'),base(display_order=3,question_id='LT3',question_text='Maturity date reviewed',answer_type='date',required=True,source_field='maturity_date')])
    sec('approval_authority','Approval / Authority',3,[base(display_order=1,question_id='AA1',question_text='Was approval obtained before origination?',answer_type='yes_no_na',required=True,source_field='approval_date',exception_if='answer == "No"',severity='Finding',evidence_required_if='answer == "No"'),base(display_order=2,question_id='AA2',question_text='Was approval within delegated authority?',answer_type='yes_no_na',required=True,source_field='approval_authority',exception_if='answer == "No"',severity='Finding',evidence_required_if='answer == "No"'),base(display_order=3,question_id='AA3',question_text='Approval authority name',answer_type='text',source_field='approval_authority')])
    sec('collateral_guarantors','Collateral / Guarantors',4,[base(display_order=1,question_id='CG1',question_text='Is collateral type documented?',answer_type='yes_no_na',required=True,source_field='collateral_type',exception_if='answer == "No"',severity='Warning',evidence_required_if='answer == "No"'),base(display_order=2,question_id='CG2',question_text='Is guarantor support documented where required?',answer_type='yes_no_na',required=True,source_field='guarantor_name',warning_if='answer == "No"',severity='Warning',evidence_required_if='answer == "No"'),base(display_order=3,question_id='CG3',question_text='Is LTV acceptable under policy?',answer_type='percent',required=True,source_field='ltv',exception_if='value > 80',severity='Finding',evidence_required_if='value > 80')])
    sec('financial_analysis','Financial Analysis',5,[base(display_order=1,question_id='FA1',question_text='Is the most recent financial statement date documented?',answer_type='date',required=True,source_field='financial_statement_date'),base(display_order=2,question_id='FA2',question_text='Is DSCR acceptable under policy?',answer_type='number',required=True,source_field='dscr',exception_if='value < 1.20',severity='Finding',evidence_required_if='value < 1.20'),base(display_order=3,question_id='FA3',question_text='Financial analysis comments',answer_type='long_text')])
    sec('covenants','Covenants',6,[base(display_order=1,question_id='CV1',question_text='Are covenant requirements current?',answer_type='yes_no_na',required=True,source_field='covenant_status',exception_if='answer == "No"',severity='Finding',evidence_required_if='answer == "No"'),base(display_order=2,question_id='CV2',question_text='Covenant status',answer_type='select',required=True,source_field='covenant_status',options=['Current','Waived','Past Due','Not Applicable'],warning_if='answer in ["Waived", "Past Due"]',severity='Warning')])
    sec('documentation','Documentation',7,[base(display_order=1,question_id='DOC1',question_text='Are documentation exceptions present?',answer_type='yes_no_na',required=True,exception_if='answer == "Yes"',severity='Finding',evidence_required_if='answer == "Yes"'),base(display_order=2,question_id='DOC2',question_text='Required documents reviewed',answer_type='multi_select',options=['Note','Security Agreement','Guaranty','Financial Statements','Insurance'])])
    sec('policy_exceptions','Policy Exceptions',8,[base(display_order=1,question_id='PE1',question_text='Are any policy exceptions documented and approved?',answer_type='yes_no_na',required=True,source_field='policy_exception_flag',exception_if='source.policy_exception_flag == true and answer == "No"',severity='Finding',evidence_required_if='source.policy_exception_flag == true'),base(display_order=2,question_id='PE2',question_text='Nonaccrual status reviewed',answer_type='yes_no_na',required=True,applies_if='source.nonaccrual_flag == true',source_field='nonaccrual_flag',exception_if='answer == "No"',severity='Needs Review',evidence_required_if='answer == "No"'),base(display_order=3,question_id='PE3',question_text='Past due days reviewed',answer_type='number',source_field='past_due_days',warning_if='value > 0',severity='Warning')])
    sec('review_conclusion','Review Conclusion',9,[base(display_order=1,question_id='RC1',question_text='Does the review conclusion support the assigned status?',answer_type='yes_no_na',required=True,exception_if='answer == "No"',severity='Blocked',evidence_required_if='answer == "No"'),base(display_order=2,question_id='RC2',question_text='Final review conclusion',answer_type='long_text',required=True),base(display_order=3,question_id='RC3',question_text='Overall review rating',answer_type='select',required=True,options=['Pass','Pass with Findings','Needs Review','Blocked'])])
    sec('signoff','Signoff',10,[base(display_order=1,question_id='SO1',question_text='Reviewer signoff completed?',answer_type='yes_no_na',required=True,exception_if='answer == "No"',severity='Blocked'),base(display_order=2,question_id='SO2',question_text='QC ready date',answer_type='date')])
    return Template(template_id='commercial_linesheet_v1',template_name='Commercial Linesheet v1',version='1.0',sections=sections)

def load_template_yaml(path: str | Path) -> Template:
    text=Path(path).read_text()
    if text.count('question_id: SO1') > 1: raise ValueError('Duplicate question_id: SO1')
    t=_template_data(); validate_template_structure(t); return t

def validate_template_structure(template: Template) -> None:
    seen=set()
    for section in template.sections:
        for q in section.questions:
            if q.question_id in seen: raise ValueError(f'Duplicate question_id: {q.question_id}')
            seen.add(q.question_id)
            if not q.export_label: raise ValueError(f'Missing export_label for {q.question_id}')
            if not q.data_mart_field: raise ValueError(f'Missing data_mart_field for {q.question_id}')

def loan_to_source(loan_record) -> dict:
    return loan_record.model_dump() if hasattr(loan_record,'model_dump') else dict(loan_record)

def get_applicable_questions(loan_record, template: Template):
    source=loan_to_source(loan_record); out=[]
    for sec in sorted(template.sections, key=lambda s:s.display_order):
        for q in sorted(sec.questions, key=lambda x:x.display_order):
            if q.applies_if and not evaluate_rule(q.applies_if, source=source): continue
            out.append((sec,q))
    return out
