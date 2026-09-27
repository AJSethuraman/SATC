"""Worked examples for statistics.md — every number in that file comes from here.
Run: python3 statistics-examples.py   (needs numpy, scipy, scikit-learn; no network)"""
import numpy as np
from scipy import stats
from scipy.stats import norm, chi2, fisher_exact, chi2_contingency, false_discovery_control
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

np.set_printoptions(suppress=True)
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a)

# ------------------------------------------------------------------ 1. two-proportion z (Test 1 book)
say("== 1. Two-proportion z, Test 1 book ==")
def two_prop(x1, n1, x2, n2):
    p1, p2 = x1/n1, x2/n2
    pbar = (x1+x2)/(n1+n2)
    se = np.sqrt(pbar*(1-pbar)*(1/n1+1/n2))
    z = (p1-p2)/se
    return p1, p2, pbar, se, z, 2*norm.sf(abs(z))
for label, (x2, n2) in {"rest of band (Branch 600)": (50, 1000), "rest of book": (150, 3000)}.items():
    p1, p2, pbar, se, z, p = two_prop(150, 1000, x2, n2)
    say(f"  vs {label}: p1={p1:.4f} p2={p2:.4f} pooled={pbar:.4f} se={se:.6f} z={z:.3f} p={p:.2e}")

# ------------------------------------------------------------------ 2. Fisher exact (below the floor)
say("\n== 2. Fisher exact ==")
tbl = np.array([[4, 8], [14, 186]])   # pocket: 4 bad of 12; rest: 14 bad of 200
orr, pf = fisher_exact(tbl, alternative="two-sided")
p1, p2, pbar, se, z, pz = two_prop(4, 12, 14, 200)
say(f"  pocket 4/12 vs rest 14/200: Fisher two-sided p={pf:.4f}; two-proportion z would say z={z:.2f} p={pz:.4f}; expected bad in pocket at rest's rate = {12*14/200:.2f}")
# how the exact p is built: hypergeometric on the pocket's bad count
rv = stats.hypergeom(M=212, n=18, N=12)   # 212 loans, 18 bad in total, 12 drawn (the pocket)
probs = rv.pmf(np.arange(0, 13))
say(f"  hypergeometric probs of k bad in a 12-loan pocket when 18 of 212 are bad: " + ", ".join(f"{k}:{v:.4f}" for k, v in enumerate(probs)))
say(f"  P(4 or more) = {probs[4:].sum():.4f}; two-sided (all outcomes as or less likely than k=4) = {probs[probs <= probs[4]+1e-12].sum():.4f}")

# ------------------------------------------------------------------ 3. Mantel-Haenszel, CMH, Cochran's Q (two strata)
say("\n== 3. Mantel-Haenszel / CMH / Cochran's Q ==")
# each stratum: [[high_bad, high_good], [low_bad, low_good]]
strata = {"pocket A": np.array([[8, 92], [4, 96]]), "pocket B": np.array([[20, 180], [12, 188]])}
num = den = 0.0; sum_a = sum_E = sum_V = 0.0; logors = []; ws = []
for name, t in strata.items():
    a, b = t[0]; c, d = t[1]; n = t.sum()
    r1, r2 = a+b, c+d; c1, c2 = a+c, b+d
    num += a*d/n; den += b*c/n
    E = r1*c1/n; V = r1*r2*c1*c2/(n*n*(n-1))
    sum_a += a; sum_E += E; sum_V += V
    lor = np.log((a*d)/(b*c)); var = 1/a+1/b+1/c+1/d
    logors.append(lor); ws.append(1/var)
    say(f"  {name}: OR={a*d/(b*c):.3f}  a={a} E[a]={E:.3f} Var={V:.4f}  high rate {a/r1:.3f} low rate {c/r2:.3f}")
or_mh = num/den
cmh = (sum_a-sum_E)**2/sum_V
say(f"  OR_MH = {num:.4f}/{den:.4f} = {or_mh:.4f}")
say(f"  CMH = ({sum_a:.0f}-{sum_E:.4f})^2/{sum_V:.4f} = {cmh:.4f}  ->  p = {chi2.sf(cmh, 1):.4f}  (1 df, no continuity correction)")
logors, ws = np.array(logors), np.array(ws)
theta_bar = (ws*logors).sum()/ws.sum()
Q = (ws*(logors-theta_bar)**2).sum()
say(f"  Cochran's Q = {Q:.4f} on {len(ws)-1} df -> p = {chi2.sf(Q, len(ws)-1):.4f}  (pooled log OR {theta_bar:.4f} = OR {np.exp(theta_bar):.3f})")
# cross-check: logistic regression with a stratum dummy
X = []; y = []
for s, (name, t) in enumerate(strata.items()):
    for high, row in enumerate([t[1], t[0]]):     # low=0, high=1
        bad, good = row
        X += [[high, s]]*(bad+good); y += [1]*bad + [0]*good
X, y = np.array(X, float), np.array(y)
m = LogisticRegression(C=1e12, max_iter=10000).fit(X, y)
say(f"  cross-check: logistic regression with stratum dummy gives OR = {np.exp(m.coef_[0][0]):.4f}")
# actual vs expected pooled (the split's O/E)
say(f"  actual vs expected (O/E) for the high halves: O={sum_a:.0f} E={sum_E:.3f} O/E={sum_a/sum_E:.3f}")

# ------------------------------------------------------------------ 4. Benjamini-Hochberg
say("\n== 4. Benjamini-Hochberg ==")
p = np.array([0.001, 0.008, 0.02, 0.04, 0.30])
adj = false_discovery_control(p, method="bh")
say(f"  raw:      {p}")
say(f"  step-up thresholds (i/m)*0.05: {np.arange(1,6)/5*0.05}")
say(f"  adjusted: {adj}   -> called real at 5%: {(adj <= 0.05).sum()} of 5")

# ------------------------------------------------------------------ 5. power / MDE at the floor
say("\n== 5. Smallest gap a pocket at the floor can show ==")
def power(p1, n1, p2, n2, alpha=0.05):
    pbar = (n1*p1+n2*p2)/(n1+n2)
    se0 = np.sqrt(pbar*(1-pbar)*(1/n1+1/n2))
    se1 = np.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
    zc = norm.ppf(1-alpha/2)
    return norm.cdf((abs(p1-p2) - zc*se0)/se1)
def mde(n1, p2, n2, target=0.80):
    lo, hi = p2, 0.999
    for _ in range(100):
        mid = (lo+hi)/2
        if power(mid, n1, p2, n2) < target: lo = mid
        else: hi = mid
    return hi
book = 0.0713; n1 = 71; n2 = 8000-71
say(f"  pocket of {n1} at book rate {book:.4f}: expected bad = {n1*book:.2f}")
m80 = mde(n1, book, n2)
say(f"  smallest rate caught 4 times in 5 (80% power, 95% two-sided): {m80:.4f} = {m80/book:.2f}x the rest")
# significance-only line: the rate that just reaches z=1.96
lo, hi = book, 0.999
for _ in range(100):
    mid = (lo+hi)/2
    if two_prop(mid*n1, n1, book*n2, n2)[4] < 1.96: lo = mid
    else: hi = mid
say(f"  smallest rate that clears luck at all (z=1.96, 50% power): {hi:.4f} = {hi/book:.2f}x")
for n1 in (71, 140, 280):
    say(f"  n={n1} (expected {n1*book:.1f}): MDE at 80% power = {mde(n1, book, n2)/book:.2f}x")

# ------------------------------------------------------------------ 6. permutation test on a dollar rate
say("\n== 6. Permutation test, GCO per booked dollar ==")
rng = np.random.default_rng(7)
bal_p = rng.lognormal(np.log(20000), 0.5, 40); bal_r = rng.lognormal(np.log(20000), 0.5, 400)
gco_p = np.where(rng.random(40) < 0.15, bal_p*rng.uniform(0.3, 0.8, 40), 0.0)
gco_r = np.where(rng.random(400) < 0.07, bal_r*rng.uniform(0.3, 0.8, 400), 0.0)
rate = lambda g, b: g.sum()/b.sum()
obs = rate(gco_p, bal_p) - rate(gco_r, bal_r)
g_all, b_all = np.concatenate([gco_p, gco_r]), np.concatenate([bal_p, bal_r])
B = 10000; hits = 0
idx = np.arange(len(g_all))
for _ in range(B):
    rng.shuffle(idx)
    d = rate(g_all[idx[:40]], b_all[idx[:40]]) - rate(g_all[idx[40:]], b_all[idx[40:]])
    hits += abs(d) >= abs(obs)
say(f"  pocket GCO/$ = {rate(gco_p, bal_p):.4f}, rest = {rate(gco_r, bal_r):.4f}, gap = {obs:+.4f}")
say(f"  shuffles with a gap at least this big: {hits} of {B} -> p = ({hits}+1)/({B}+1) = {(hits+1)/(B+1):.4f}")

# ------------------------------------------------------------------ 7. K-group CMH: general association and trend
say("\n== 7. K-group CMH ==")
def gmh(tables, scores=None):
    """tables: list of K x 2 arrays [bad, good] per bin. Returns (Q_general, df, Q_trend)."""
    K = tables[0].shape[0]
    d = np.zeros(K-1); V = np.zeros((K-1, K-1)); T = 0.0; VT = 0.0
    for t in tables:
        R = t.sum(1); C = t.sum(0); N = t.sum()
        E = R*C[0]/N
        d += (t[:-1, 0] - E[:-1])
        f = C[0]*C[1]/(N*N*(N-1))
        V += f*(N*np.diag(R[:-1]) - np.outer(R[:-1], R[:-1]))
        if scores is not None:
            s = np.asarray(scores, float)
            T += (s*(t[:, 0]-E)).sum()
            VT += f*(N*(s*s*R).sum() - (s*R).sum()**2)
    Qg = d @ np.linalg.solve(V, d)
    Qt = T*T/VT if scores is not None else None
    return Qg, K-1, Qt
# single stratum check against Pearson chi-square: Q_GMH = (N-1)/N * X^2
t1 = np.array([[12, 88], [30, 370], [45, 455], [40, 360], [25, 75]], float)   # 5 ratio bins
Qg, df, Qt = gmh([t1], scores=[1, 2, 3, 4, 5])
X2 = chi2_contingency(t1, correction=False)[0]; N = t1.sum()
say(f"  one stratum: Q_general = {Qg:.4f}, (N-1)/N * Pearson X^2 = {(N-1)/N*X2:.4f}  (identity holds)")
say(f"  rates by bin: {np.round(t1[:,0]/t1.sum(1), 3)}; general p = {chi2.sf(Qg, df):.4f} on {df} df; trend p = {chi2.sf(Qt, 1):.4f} on 1 df")
# two strata, U-shape: general says yes, trend says no
t2 = np.array([[10, 90], [15, 385], [20, 480], [15, 385], [12, 88]], float)
Qg, df, Qt = gmh([t1, t2], scores=[1, 2, 3, 4, 5])
say(f"  two strata (U-shape planted): general Q = {Qg:.3f} p = {chi2.sf(Qg, df):.4f}; trend Q = {Qt:.3f} p = {chi2.sf(Qt, 1):.4f}")

# ------------------------------------------------------------------ 8. logistic regression: LR test for the bin block; rule scoring; AUC identity
say("\n== 8. Regression block test, rule scoring, AUC ==")
# the same synthetic books as scout-vs-measure.py, regenerated here
def make_book(n, seed):
    rng = np.random.default_rng(seed)
    fico = np.clip(rng.normal(680, 50, n), 500, 850)
    log_size = rng.normal(np.log(40000), 0.6, n)
    ratio = np.exp(rng.normal(-0.7, 0.8, n))
    noise1, noise2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    logit = np.log(0.05/0.95) - 0.02*(fico-680) + np.log(3)*(ratio > 2.0) + np.log(2)*(ratio < 0.1)
    bad = rng.random(n) < 1/(1+np.exp(-logit))
    return np.column_stack([fico, log_size, ratio, noise1, noise2]), bad.astype(int)
Xdev, ydev = make_book(40000, 2223); Xhol, yhol = make_book(15000, 2024)
edges = [0.1, 0.25, 0.5, 1.0, 2.0]
def design(X, with_bins):
    cols = [X[:, 0], X[:, 1]]
    if with_bins:
        b = np.digitize(X[:, 2], edges)
        cols += [(b == k).astype(float) for k in range(6) if k != 2]
    return np.column_stack(cols)
def loglik(X, y):
    m = LogisticRegression(C=1e12, max_iter=10000).fit(X, y)
    p = m.predict_proba(X)[:, 1]
    return (y*np.log(p) + (1-y)*np.log(1-p)).sum()
l0, l1 = loglik(design(Xdev, False), ydev), loglik(design(Xdev, True), ydev)
lr = 2*(l1-l0)
say(f"  likelihood-ratio test for the 5 bin dummies (development): 2*({l1:.2f} - {l0:.2f}) = {lr:.2f} on 5 df -> p = {chi2.sf(lr, 5):.2e}")
# rule scoring on the holdout
r = Xhol[:, 2]
for name, flag in {"ratio >= 2": r >= 2, "ratio >= 2 or < 0.1": (r >= 2) | (r < 0.1)}.items():
    fr = flag.mean(); cap = yhol[flag].sum()/yhol.sum(); lift = yhol[flag].mean()/yhol.mean()
    say(f"  rule '{name}': flag rate {fr:.2%} ({flag.sum():,} loans), captures {yhol[flag].sum()} of {yhol.sum()} bad = {cap:.1%}, lift = {yhol[flag].mean():.3%}/{yhol.mean():.3%} = {lift:.2f}x")
# AUC identity: probability a random bad outranks a random good
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier(n_estimators=400, min_samples_leaf=40, random_state=7, n_jobs=-1).fit(Xdev[:28000], ydev[:28000])
s = rf.predict_proba(Xhol)[:, 1]
auc = roc_auc_score(yhol, s)
rng = np.random.default_rng(1)
bad_s, good_s = s[yhol == 1], s[yhol == 0]
pairs = 200000
bi, gi = rng.integers(0, len(bad_s), pairs), rng.integers(0, len(good_s), pairs)
pr = (bad_s[bi] > good_s[gi]).mean() + 0.5*(bad_s[bi] == good_s[gi]).mean()
say(f"  holdout AUC = {auc:.4f}; share of random (bad, good) pairs where the bad loan scores higher = {pr:.4f}; Gini = 2*AUC-1 = {2*auc-1:.3f}")
# calibration by score band
q = np.quantile(s, [0.2, 0.4, 0.6, 0.8]); band = np.digitize(s, q)
say("  calibration by score band (holdout): predicted vs actual bad rate")
for k in range(5):
    say(f"    band {k+1}: predicted {s[band==k].mean():.3%}  actual {yhol[band==k].mean():.3%}  ({(band==k).sum():,} loans)")

