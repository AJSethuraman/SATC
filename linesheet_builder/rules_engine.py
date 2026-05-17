from __future__ import annotations
import ast, operator
from types import SimpleNamespace

OPS = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda a,b: a in b, ast.NotIn: lambda a,b: a not in b}
BOOL = {"true": True, "false": False, "none": None}

class UnsafeRuleError(ValueError): pass

def _blank(v): return v is None or str(v).strip() == ""

def _val(node, ctx):
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.List): return [_val(x, ctx) for x in node.elts]
    if isinstance(node, ast.Tuple): return tuple(_val(x, ctx) for x in node.elts)
    if isinstance(node, ast.Name):
        if node.id.lower() in BOOL: return BOOL[node.id.lower()]
        if node.id in ctx: return ctx[node.id]
        raise UnsafeRuleError(f"Unknown name {node.id}")
    if isinstance(node, ast.Attribute):
        base = _val(node.value, ctx)
        if isinstance(base, dict): return base.get(node.attr)
        return getattr(base, node.attr, None)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return not _val(node.operand, ctx)
    if isinstance(node, ast.BoolOp):
        vals = [_val(v, ctx) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Compare):
        left = _val(node.left, ctx)
        for op, comp in zip(node.ops, node.comparators):
            right = _val(comp, ctx)
            try: ok = OPS[type(op)](left, right)
            except (TypeError, ValueError): ok = False
            if not ok: return False
            left = right
        return True
    raise UnsafeRuleError(f"Unsupported expression: {ast.dump(node)}")

def evaluate_rule(expr: str | None, *, answer=None, value=None, source=None, required=False) -> bool:
    if not expr: return False
    if expr.strip().lower() == "required answer is blank": return bool(required and _blank(answer))
    tree = ast.parse(expr, mode="eval")
    for n in ast.walk(tree):
        if isinstance(n, (ast.Call, ast.Import, ast.ImportFrom, ast.Lambda, ast.Subscript, ast.BinOp, ast.Assign, ast.NamedExpr)):
            raise UnsafeRuleError("Unsafe or unsupported rule syntax")
    src = source or {}
    ctx = {"answer": answer, "value": value, "source": src if isinstance(src, dict) else SimpleNamespace(**src)}
    return bool(_val(tree.body, ctx))

def determine_question_status(question, answer=None, source=None):
    value = answer
    if question.source_field and (answer is None or str(answer).strip() == "") and source:
        value = source.get(question.source_field)
    try:
        if value not in (None, ""): value = float(value)
    except (TypeError, ValueError): pass
    exception = evaluate_rule(question.exception_if, answer=answer, value=value, source=source or {}, required=question.required)
    warning = evaluate_rule(question.warning_if, answer=answer, value=value, source=source or {}, required=question.required)
    evidence = evaluate_rule(question.evidence_required_if, answer=answer, value=value, source=source or {}, required=question.required)
    if exception: return {"status": "Exception", "severity": question.severity, "exception_flag": True, "evidence_required": evidence}
    if warning: return {"status": "Warning", "severity": question.severity or "Warning", "exception_flag": False, "evidence_required": evidence}
    return {"status": "Complete" if answer not in (None, "") else "Incomplete", "severity": None, "exception_flag": False, "evidence_required": evidence}
