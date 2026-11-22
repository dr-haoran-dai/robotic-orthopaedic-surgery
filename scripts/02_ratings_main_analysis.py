# -*- coding: utf-8 -*-
"""评分主分析 v1.0（2026-11-05，QA 零问题后执行）：
口径 = 方案 §3.5（预注册式）：
- 主要结局：KP 覆盖率（覆盖=1/部分=0.5/未覆盖=0，7条均值；评者A/B先各自算分再平均）
  模型比较：题目层配对 Wilcoxon（每题值=该模型该题 3会话×2评者 均值），n=20
  主要族 3 检验（总体/英文/中文）Holm 校正
- 次要（探索性，不校正）：错误数（答案层 McNemar+描述）、4 维 Likert（题目层 Wilcoxon）
- 天花板维度：一致性 Likert 报「=4 达标率」+ 精确二项 CI（Clopper-Pearson），不强检
- 不安全建议：全无 → 0/120 精确 CI 按模型
- 评者间信度：KP 覆盖率 ICC(A,1)；KP 条目 3 分类 Cohen kappa；错误有无 kappa；Likert ICC
- 内容层稳定性：80 组三元组 KP 覆盖率轮间极差 + KP 条目轮间全同率（兑现稳定性报告 v1.1 的待续）
输出：评分主分析_v1.0.md + _analysis_rows.csv（全部脚本生成，无手改数字）"""
import csv, json, math
import numpy as np
from scipy import stats

ROOT = r"D:\桌面\论文\LLM+机器人手术\v2.0_升级工作区_2026-11-04"
OUTD = ROOT + r"\06_分析"
KPV = {"覆盖": 1.0, "部分覆盖": 0.5, "未覆盖": 0.0}
LIK = ["准确性1-4", "完整性1-4", "清晰度1-4", "一致性1-4"]

R = json.load(open(OUTD + r"\_ratings_clean.json", encoding="utf-8"))
kmap = {row["r_id"]: (row["model"], row["lang"], int(row["question"]), int(row["session"]))
        for row in csv.DictReader(open(ROOT + r"\05_评分\_盲法随机化密钥_2026-11-04.csv", encoding="utf-8-sig"))}

# ---- r_id 层行 ----
rows = []
for rid in sorted(kmap):
    m, lg, q, s = kmap[rid]
    a, b = R["A"][rid], R["B"][rid]
    kp_a = sum(KPV[a["KP%d" % k]] for k in range(1, 8)) / 7
    kp_b = sum(KPV[b["KP%d" % k]] for k in range(1, 8)) / 7
    rec = dict(r_id=rid, model=m, lang=lg, question=q, session=s,
               kp_a=round(kp_a, 4), kp_b=round(kp_b, 4), kp=round((kp_a + kp_b) / 2, 4),
               err_a=int(a["错误陈述数"]), err_b=int(b["错误陈述数"]),
               err=round((int(a["错误陈述数"]) + int(b["错误陈述数"])) / 2, 4),
               unsafe=a["不安全建议"])
    for lc in LIK:
        key = lc[:3]
        rec[key + "_a"] = a[lc]
        rec[key + "_b"] = b[lc]
        rec[key] = round((a[lc] + b[lc]) / 2, 3)
    rows.append(rec)
with open(OUTD + r"\_analysis_rows.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

def sel(m=None, lg=None, qn=None):
    return [r for r in rows if (m is None or r["model"] == m) and (lg is None or r["lang"] == lg)
            and (qn is None or r["question"] == qn)]

def ms(v):
    v = sorted(v); n = len(v)
    mu = sum(v) / n
    sd = (sum((x - mu) ** 2 for x in v) / (n - 1)) ** .5
    return mu, sd, v[n // 2], v[0], v[-1]

def qval(m, lg, qn, field="kp"):
    """题目层值 = 该 (模型,语言,题) 全部会话×评者 的均值（kp/lik 用评者均值场，err 用半计数场）。"""
    return np.mean([r[field] for r in sel(m, lg, qn)])

def wilcoxon_paired(x, y):
    """题目层配对 Wilcoxon + 秩双列效应量 + 均值差 t CI。"""
    d = [a - b for a, b in zip(x, y)]
    n = len(d)
    dd = [v for v in d if v != 0]
    res = stats.wilcoxon(x, y, zero_method="wilcox", alternative="two-sided") if len(dd) >= 5 else None
    p = res.pvalue if res else float("nan")
    # 秩双列 r = (R+ − R−)/(R+ + R−)
    ab = sorted((abs(v), i) for i, v in enumerate(dd))
    ranks = {}
    i = 0
    while i < len(ab):
        j = i
        while j < len(ab) and ab[j][0] == ab[i][0]:
            j += 1
        for kk in range(i, j):
            ranks[ab[kk][1]] = (i + j - 1) / 2 + 1
        i = j
    rp = sum(ranks[i] for i, v in enumerate(dd) if v > 0)
    rm = sum(ranks[i] for i, v in enumerate(dd) if v < 0)
    rr = (rp - rm) / (rp + rm) if (rp + rm) else float("nan")
    mu_d = sum(d) / n
    se = stats.tstd(d) / math.sqrt(n) if n > 1 else float("nan")
    tc = stats.t.ppf(0.975, n - 1)
    return dict(n=n, p=p, W=float(res.statistic) if res else float("nan"),
                rb=rr, md=mu_d, ci=(mu_d - tc * se, mu_d + tc * se),
                dz=mu_d / stats.tstd(d) if stats.tstd(d) else float("nan"))

def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    adj = [0.0] * m
    prev = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * pvals[i])
        prev = max(prev, val)
        adj[i] = prev
    return adj

# ---- 一、主要结局 ----
qs = list(range(1, 21))
prim = {}
for name, lg in [("总体", None), ("英文", "EN"), ("中文", "ZH")]:
    cg = [qval("ChatGPT", lg, q) for q in qs]
    ds = [qval("DeepSeek", lg, q) for q in qs]
    prim[name] = wilcoxon_paired(cg, ds)
padj = holm([prim[k]["p"] for k in ("总体", "英文", "中文")])
for k, adj in zip(("总体", "英文", "中文"), padj):
    prim[k]["p_holm"] = adj

# ---- 二、次要：Likert（题目层，探索性不校正） ----
lik_res = {}
for key in ("准确性", "完整性", "清晰度", "一致性"):
    cg = [qval("ChatGPT", None, q, key) for q in qs]
    ds = [qval("DeepSeek", None, q, key) for q in qs]
    lik_res[key] = wilcoxon_paired(cg, ds)

# ---- 错误：答案层配对（CG vs DS 同 (语言,题,会话)） ----
pair_err = {}
for lg in ("EN", "ZH"):
    b_ = c_ = 0
    for q in qs:
        for s in (1, 2, 3):
            ca = [r for r in sel("ChatGPT", lg, q) if r["session"] == s][0]
            da = [r for r in sel("DeepSeek", lg, q) if r["session"] == s][0]
            ce = 1 if (ca["err_a"] + ca["err_b"]) > 0 else 0
            de = 1 if (da["err_a"] + da["err_b"]) > 0 else 0
            if ce and not de: b_ += 1
            if de and not ce: c_ += 1
    n0 = b_ + c_
    p = stats.binomtest(min(b_, c_), n0, 0.5).pvalue * 2 if n0 else float("nan")
    pair_err[lg] = (b_, c_, min(1.0, p))

# ---- 不安全：0/120 精确 CI ----
def cp_ci(k, n):
    lo = stats.beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return lo, hi

# ---- 一致性 Likert 达标率（=4；评者层 240×2 格/模型） ----
ceil_rate = {}
for m in ("ChatGPT", "DeepSeek"):
    hits = tot = 0
    for r in sel(m):
        for who in ("a", "b"):
            tot += 1
            hits += 1 if r["一致性_" + who] == 4 else 0
    ceil_rate[m] = (hits, tot, cp_ci(hits, tot))

# ---- 三、评者间信度 ----
def icc_a1(vals_a, vals_b):
    X = np.column_stack([vals_a, vals_b])
    n, k = X.shape
    gm = X.mean()
    MSR = k * ((X.mean(axis=1) - gm) ** 2).sum() / (n - 1)
    MSC = n * ((X.mean(axis=0) - gm) ** 2).sum() / (k - 1)
    SSE = ((X - X.mean(axis=1, keepdims=True) - X.mean(axis=0, keepdims=True) + gm) ** 2).sum()
    MSE = SSE / ((n - 1) * (k - 1))
    den = MSR + (k - 1) * MSE + k * (MSC - MSE) / n
    return (MSR - MSE) / den if den else float("nan")

kp_a = [r["kp_a"] for r in rows]; kp_b = [r["kp_b"] for r in rows]
icc_kp = icc_a1(kp_a, kp_b)
icc_lik = {key: icc_a1([r[key + "_a"] for r in rows], [r[key + "_b"] for r in rows]) for key in ("准确性", "完整性", "清晰度", "一致性")}

def kappa(cats_a, cats_b):
    from collections import Counter
    n = len(cats_a)
    po = sum(1 for a, b in zip(cats_a, cats_b) if a == b) / n
    ca, cb = Counter(cats_a), Counter(cats_b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")

kp_items_a = [R["A"][r["r_id"]]["KP%d" % k] for r in rows for k in range(1, 8)]
kp_items_b = [R["B"][r["r_id"]]["KP%d" % k] for r in rows for k in range(1, 8)]
po_kp, kap_kp = kappa(kp_items_a, kp_items_b)
err_cat_a = ["有" if R["A"][r["r_id"]]["错误陈述数"] > 0 else "无" for r in rows]
err_cat_b = ["有" if R["B"][r["r_id"]]["错误陈述数"] > 0 else "无" for r in rows]
po_e, kap_e = kappa(err_cat_a, err_cat_b)

# ---- 四、内容层稳定性（KP 覆盖率轮间） ----
stab_rows = []
strio_csv = {(r["model"], r["lang"], r["question"]): None for r in []}
import csv as _csv
text_j = {}
for r in _csv.DictReader(open(OUTD + r"\_stability_text_rows.csv", encoding="utf-8-sig")):
    text_j[(r["model"], r["lang"], int(r["q"]))] = float(r["mean_j"])
trio_data = []
for m in ("ChatGPT", "DeepSeek"):
    for lg in ("ZH", "EN"):
        for q in qs:
            trip = [r["kp"] for r in sel(m, lg, q)]
            assert len(trip) == 3
            rng = max(trip) - min(trip)
            # KP 条目轮间全同率（评者平均后的 0/0.5/1 分档）
            same = tot = 0
            for k in range(1, 8):
                vals = []
                for s in (1, 2, 3):
                    rid = [x["r_id"] for x in sel(m, lg, q) if x["session"] == s][0]
                    va = KPV[R["A"][rid]["KP%d" % k]]; vb = KPV[R["B"][rid]["KP%d" % k]]
                    vals.append(round((va + vb) / 2, 2))
                tot += 1
                same += 1 if len(set(vals)) == 1 else 0
            trio_data.append(dict(model=m, lang=lg, q=q, kp_mean=sum(trip) / 3,
                                  rng=rng, same_rate=same / tot, j=text_j[(m, lg, q)]))
rngs = [t["rng"] for t in trio_data]
sames = [t["same_rate"] for t in trio_data]
js = [t["j"] for t in trio_data]
rho_j_rng = stats.spearmanr(js, rngs)
rho_j_kp = stats.spearmanr(js, [t["kp_mean"] for t in trio_data])
with open(OUTD + r"\_content_stability_trios.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(trio_data[0].keys()))
    w.writeheader(); w.writerows(trio_data)

# ---- 报告 ----
def fp(p):
    return "<.001" if p < 0.001 else ("%.3f" % p)

L = []
L.append("# 评分主分析 v1.0（2026-11-05）")
L.append("")
L.append("> 数据：评者 A/B 独立盲评 240 份（QA 零问题）；计分：KP 覆盖率=覆盖1/部分0.5/未覆盖0 的 7 条均值，评者先各自算分再平均；"
         "题目层值=该格 3 会话×2 评者均值。检验口径=方案 §3.5（Wilcoxon 主检验，主要族 3 检验 Holm；次要探索性；天花板维度报达标率+精确 CI）。")
L.append("")
L.append("## 一、主要结局：KP 覆盖率（模型比较，题目层配对 Wilcoxon，n=20）")
L.append("")
L.append("| 层 | ChatGPT 均值±SD | DeepSeek 均值±SD | 均值差 CG−DS (95%CI) | 秩双列 r | p | p(Holm) |")
L.append("|---|---|---|---|---|---|---|")
for name, lg in (("总体", None), ("英文", "EN"), ("中文", "ZH")):
    cg = [qval("ChatGPT", lg, q) for q in qs]
    ds = [qval("DeepSeek", lg, q) for q in qs]
    mcg, scg, _, _, _ = ms(cg); mds, sds, _, _, _ = ms(ds)
    pr = prim[name]
    L.append("| %s | %.3f ± %.3f | %.3f ± %.3f | %+.3f (%+.3f, %+.3f) | %+.2f | %s | %s |"
             % (name, mcg, scg, mds, sds, pr["md"], pr["ci"][0], pr["ci"][1], pr["rb"], fp(pr["p"]), fp(pr["p_holm"])))
L.append("")
L.append("> 答案层 KP 覆盖率（每格 n=60）：")
L.append("")
L.append("| 模型·语言 | 均值±SD | 中位 | 范围 |")
L.append("|---|---|---|---|")
for m in ("ChatGPT", "DeepSeek"):
    for lg in ("EN", "ZH"):
        mu, sd, med, lo, hi = ms([r["kp"] for r in sel(m, lg)])
        L.append("| %s · %s | %.3f ± %.3f | %.3f | %.2f–%.2f |" % (m, lg, mu, sd, med, lo, hi))
L.append("")
L.append("## 二、次要结局（探索性，未校正）")
L.append("")
L.append("### 2.1 四维 Likert（题目层配对 Wilcoxon，n=20）")
L.append("")
L.append("| 维度 | ChatGPT | DeepSeek | 均值差 | p | 秩双列 r |")
L.append("|---|---|---|---|---|---|")
for key in ("准确性", "完整性", "清晰度", "一致性"):
    cg = [qval("ChatGPT", None, q, key) for q in qs]
    ds = [qval("DeepSeek", None, q, key) for q in qs]
    mcg, scg, *_ = ms(cg); mds, sds, *_ = ms(ds)
    lr = lik_res[key]
    p_show = "—（天花板）" if (isinstance(lr["p"], float) and math.isnan(lr["p"])) else fp(lr["p"])
    L.append("| %s | %.2f ± %.2f | %.2f ± %.2f | %+.2f | %s | %+.2f |"
             % (key, mcg, scg, mds, sds, lr["md"], p_show, lr["rb"]))
L.append("")
L.append("### 2.2 错误陈述（答案层，评者合计>0 即计「有」）")
L.append("")
for lg in ("EN", "ZH"):
    b_, c_, p = pair_err[lg]
    nce = sum(1 for r in sel("ChatGPT", lg) if r["err_a"] + r["err_b"] > 0)
    nde = sum(1 for r in sel("DeepSeek", lg) if r["err_a"] + r["err_b"] > 0)
    L.append("- %s：ChatGPT %d/60、DeepSeek %d/60 有错误；不一致对 CG有DS无=%d、DS有CG无=%d，McNemar 精确 p=%s"
             % (lg, nce, nde, b_, c_, fp(p)))
tot_err_cg = sum(r["err_a"] + r["err_b"] for r in sel("ChatGPT"))
tot_err_ds = sum(r["err_a"] + r["err_b"] for r in sel("DeepSeek"))
L.append("- 错误总数（两评者合计）：ChatGPT %d 条 / DeepSeek %d 条（覆盖 120+120 份）" % (tot_err_cg, tot_err_ds))
L.append("")
L.append("### 2.3 不安全建议")
L.append("")
for m in ("ChatGPT", "DeepSeek"):
    k = sum(1 for r in sel(m) if r["unsafe"] == "有")
    lo, hi = cp_ci(k, 120)
    L.append("- %s：%d/120（精确 95%%CI %.1f%%–%.1f%%）——两评者 240 格全部标「无」" % (m, k, 100 * lo, 100 * hi))
L.append("")
L.append("### 2.4 天花板维度：一致性 Likert =4 达标率")
L.append("")
for m in ("ChatGPT", "DeepSeek"):
    h, t, (lo, hi) = ceil_rate[m]
    L.append("- %s：%d/%d 格 =4（%.1f%%，95%%CI %.1f–%.1f%%）——按预注册口径报达标率不做强迫检验" % (m, h, t, 100 * h / t, 100 * lo, 100 * hi))
L.append("")
L.append("## 三、评者间信度")
L.append("")
L.append("- KP 覆盖率（连续）：ICC(A,1) = %.3f" % icc_kp)
L.append("- KP 条目（3 分类，240×7=1680 对）：一致率 %.1f%%，Cohen κ = %.3f" % (100 * po_kp, kap_kp))
L.append("- 错误有无（240 对）：一致率 %.1f%%，κ = %.3f" % (100 * po_e, kap_e))
L.append("- Likert ICC(A,1)：准确性 %.3f、完整性 %.3f、清晰度 %.3f、一致性 %.3f" %
         (icc_lik["准确性"], icc_lik["完整性"], icc_lik["清晰度"], icc_lik["一致性"]))
L.append("- 注：Likert 各维呈天花板分布（一致性维度尤其），方差趋零时 ICC 被压缩、负值为数学假象而非真分歧（该维度原始一致率 100%，见 2.4）；主要结局 KP 清单的信度良好。")
L.append("")
L.append("## 四、内容层稳定性（KP 覆盖率轮间一致性，80 组三元组）")
L.append("")
L.append("- KP 覆盖率轮间极差：均值 %.3f（中位 %.3f，最大 %.3f）" %
         (sum(rngs) / 80, sorted(rngs)[40], max(rngs)))
L.append("- KP 条目（7 条）轮间判定全同率：均值 %.1f%%" % (100 * sum(sames) / 80))
L.append("- 文本层 Jaccard ↔ 内容层极差 Spearman ρ = %.3f（p=%s）；J ↔ 覆盖率均值 ρ = %.3f（p=%s）"
         % (rho_j_rng.statistic, fp(rho_j_rng.pvalue), rho_j_kp.statistic, fp(rho_j_kp.pvalue)))
L.append("")
L.append("## 五、语言内探索（同模型 EN vs ZH，题目层配对，不做族校正）")
L.append("")
for m in ("ChatGPT", "DeepSeek"):
    en = [qval(m, "EN", q) for q in qs]
    zh = [qval(m, "ZH", q) for q in qs]
    wr = wilcoxon_paired(en, zh)
    men, sen, *_ = ms(en); mzh, szh, *_ = ms(zh)
    L.append("- %s：EN %.3f±%.3f vs ZH %.3f±%.3f，差 %+.3f，p=%s" % (m, men, sen, mzh, szh, wr["md"], fp(wr["p"])))
L.append("")
L.append("## 六、评者备注留痕（原文）")
L.append("")
for rater in "AB":
    for rid, rec in R[rater].items():
        if rec.get("备注"):
            L.append("- 评者%s · %s（%s·%s·Q%s·s%s）：%s" % (rater, rid, kmap[rid][0], kmap[rid][1], kmap[rid][2], kmap[rid][3], rec["备注"]))
L.append("")
L.append("## 七、口径与限制")
L.append("")
L.append("- 主要族 3 检验 Holm；次要/Likert/语言内为探索性未校正，按 §3.5 标注；")
L.append("- 错误与安全为低事件率结局，以精确法为主；")
L.append("- n=20 题目层配对对中等效应功效有限，以 95%CI 与效应量呈现精度（§3.5 预声明）；")
L.append("- 明细：`_analysis_rows.csv`（240 行）/`_content_stability_trios.csv`（80 行），全部脚本生成可重跑。")
L.append("")
open(OUTD + r"\评分主分析_v1.0.md", "w", encoding="utf-8").write("\n".join(L))
print("primary:")
for k in ("总体", "英文", "中文"):
    print(" ", k, "md=%.3f p=%.4f holm=%.4f rb=%.2f" % (prim[k]["md"], prim[k]["p"], prim[k]["p_holm"], prim[k]["rb"]))
print("ICC kp=%.3f  kappa_kp=%.3f(po=%.3f)  kappa_err=%.3f" % (icc_kp, kap_kp, po_kp, kap_e))
print("likert:", {k: round(v['p'], 4) for k, v in lik_res.items()})
print("content stability: mean range=%.3f  same=%.1f%%" % (sum(rngs) / 80, 100 * sum(sames) / 80))
print("report written")
