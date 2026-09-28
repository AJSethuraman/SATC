"""
One synthetic book, one planted effect the two methods see differently.

Plant: bad odds x3 when income/sales > 2 (way over) and x2 when < 0.1 (income
a sliver of sales). Nothing in between. FICO matters as usual. Two noise columns.

Then: (1) plain logistic regression with the ratio as a number,
      (2) random forest -> importance ranking + partial dependence (the shape),
      (3) logistic regression with the ratio BINNED where the shape bends
          (the cube's approach), fitted on development, confirmed on holdout.
"""
import numpy as np
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance, partial_dependence
from sklearn.metrics import roc_auc_score

def make_book(n, seed):
    rng = np.random.default_rng(seed)
    fico = np.clip(rng.normal(680, 50, n), 500, 850)
    log_size = rng.normal(np.log(40000), 0.6, n)
    ratio = np.exp(rng.normal(-0.7, 0.8, n))      # median ~0.50; ~4% above 2; ~2% below 0.1
    noise1, noise2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    logit = np.log(0.05/0.95) - 0.02*(fico-680) + np.log(3)*(ratio > 2.0) + np.log(2)*(ratio < 0.1)
    bad = rng.random(n) < 1/(1+np.exp(-logit))
    X = np.column_stack([fico, log_size, ratio, noise1, noise2])
    return X, bad.astype(int)

names = ["FICO", "log loan size", "income/sales", "noise A", "noise B"]
Xdev, ydev = make_book(40000, 2223)   # "2022-2023"
Xhol, yhol = make_book(15000, 2024)   # "2024"
print(f"development: {len(ydev):,} loans, {ydev.sum():,} bad ({ydev.mean():.2%})")
print(f"holdout:     {len(yhol):,} loans, {yhol.sum():,} bad ({yhol.mean():.2%})")
print(f"share of dev loans with ratio > 2: {(Xdev[:,2]>2).mean():.1%}; < 0.1: {(Xdev[:,2]<0.1).mean():.1%}")

def wald(X, y):
    """Unpenalised logistic fit; standard errors from the information matrix."""
    m = LogisticRegression(C=1e12, max_iter=10000).fit(X, y)
    beta = np.concatenate([m.intercept_, m.coef_[0]])
    X1 = np.column_stack([np.ones(len(X)), X])
    p = 1/(1+np.exp(-(X1 @ beta)))
    H = (X1 * (p*(1-p))[:, None]).T @ X1
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    z = beta/se
    return beta, se, z, 2*norm.sf(np.abs(z))

# ---------- (1) regression with the ratio as a number ----------
print("\n(1) Logistic regression, ratio entered as log(income/sales) — development set")
Xr = Xdev.copy(); Xr[:, 2] = np.log(Xr[:, 2])
beta, se, z, p = wald(Xr, ydev)
for i, nm in enumerate(names, start=1):
    print(f"   {nm:14s} coef {beta[i]:+.4f}  z {z[i]:+6.2f}  p {p[i]:.3g}")

# ---------- (2) random forest: ranking + shape ----------
print("\n(2) Random forest — development set")
rf = RandomForestClassifier(n_estimators=400, min_samples_leaf=40, random_state=7, n_jobs=-1)
cut = 28000
rf.fit(Xdev[:cut], ydev[:cut])
pi = permutation_importance(rf, Xdev[cut:], ydev[cut:], scoring="roc_auc", n_repeats=10, random_state=7, n_jobs=-1)
order = np.argsort(-pi.importances_mean)
print("   importance (drop in AUC when the column is scrambled):")
for i in order:
    print(f"      {names[i]:14s} {pi.importances_mean[i]:+.4f}")
grid = np.array([0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0])
pd_ = partial_dependence(rf, Xdev[:cut], features=[2], custom_values={2: grid}, kind="average")
print("   partial dependence on income/sales (model's bad rate holding everything else at its actual values):")
for g, v in zip(grid, pd_["average"][0]):
    print(f"      ratio {g:4.2f}: {v:.2%}")

# ---------- (3) binned regression: pre-specified from the shape, confirmed on holdout ----------
edges = [0.1, 0.25, 0.5, 1.0, 2.0]                     # written down after looking at (2)
labels = ["< 0.10", "0.10-0.25", "0.25-0.50", "0.50-1.00", "1.00-2.00", ">= 2.00"]
ref = 2                                               # 0.25-0.50 holds the median: the normal case
def binned_design(X):
    b = np.digitize(X[:, 2], edges)
    dummies = np.column_stack([(b == k).astype(float) for k in range(len(labels)) if k != ref])
    return np.column_stack([X[:, 0], X[:, 1], dummies]), b
def report(X, y, title):
    Xb, b = binned_design(X)
    beta, se, z, p = wald(Xb, y)
    print(f"\n(3) {title}")
    print("   bin          loans   bad   odds ratio vs 0.25-0.50   95% interval      luck alone")
    j = 3
    for k, lab in enumerate(labels):
        n_k, bad_k = (b == k).sum(), y[b == k].sum()
        if k == ref:
            print(f"   {lab:11s} {n_k:6,d} {bad_k:5,d}   1.00 (reference)")
            continue
        lo, hi = np.exp(beta[j] - 1.96*se[j]), np.exp(beta[j] + 1.96*se[j])
        print(f"   {lab:11s} {n_k:6,d} {bad_k:5,d}   {np.exp(beta[j]):.2f}                     {lo:.2f} - {hi:.2f}      {p[j]:.3g}")
        j += 1
report(Xdev, ydev, "Binned logistic regression — development set (where the bins were chosen)")
report(Xhol, yhol, "Same bins, same test, untouched — HOLDOUT (the evidence)")

# ---------- the second holdout check: does the frozen model rank the 2024 bad loans? ----------
print("\nFrozen forest (built on development only) scored on holdout: AUC = "
      f"{roc_auc_score(yhol, rf.predict_proba(Xhol)[:,1]):.3f}   (0.5 = coin flip)")
