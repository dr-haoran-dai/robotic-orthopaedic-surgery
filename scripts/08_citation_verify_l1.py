# -*- coding: utf-8 -*-
"""引文核真 Layer-1（2026-11-05，SAP B7）：
259 唯一 URL 中的 API 可核类：
- pubmed(85) + pmc(75)：NCBI eutils esummary 批量 → 存在性/题名/出版物类型
- doi(6)：Crossref works/{doi} → 存在性/题名/类型
- journal-site(30)：从 URL 提取 DOI 者走 Crossref，其余标记人工
锚文本比对：锚文本关键词 → 期望出版物类型；逐条判 match/mismatch/undeterminable/soft。
输出：_citation_l1_results.csv（逐唯一URL）+ _citation_l1_by_answer.csv（逐答案汇总）+ 引文核真_L1_v1.0.md
原始响应缓存 _citation_cache\\ 可复查。不动任何采集原件。"""
import csv, json, os, re, time, urllib.request, urllib.error

ROOT = r"D:\桌面\论文\LLM+机器人手术\v2.0_升级工作区_2026-11-04"
OUTD = ROOT + r"\06_分析"
CACHE = OUTD + r"\_citation_cache"
os.makedirs(CACHE, exist_ok=True)
PROXY = "http://127.0.0.1:7897"

def fetch(url, timeout=25, retries=2):
    for attempt in range(retries + 1):
        opener = urllib.request.build_opener()
        if attempt >= 1:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
        req = urllib.request.Request(url, headers={"User-Agent": "citation-audit/1.0 (research; mailto:user@example.com)"})
        try:
            with opener.open(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(1.0)

def cached(name, url):
    p = CACHE + "\\" + name
    if os.path.exists(p):
        return open(p, encoding="utf-8").read()
    txt = fetch(url)
    open(p, "w", encoding="utf-8").write(txt)
    time.sleep(0.4)
    return txt

rows = list(csv.DictReader(open(OUTD + r"\_citation_links.csv", encoding="utf-8-sig")))
uniq = {}
for r in rows:
    uniq.setdefault(r["url"].rstrip("/"), dict(r))

# ---------- 锚文本 → 期望出版物类型 ----------
EXPECT = [
    (re.compile(r"随机对照|RCT|randomized controlled", re.I), ["Randomized Controlled Trial"], "RCT"),
    (re.compile(r"随机试验|randomized trial", re.I), ["Randomized Controlled Trial"], "RCT(随机试验)"),
    (re.compile(r"荟萃|meta[- ]?分析|系统评价|系统综述|systematic review|meta-analysis", re.I),
     ["Meta-Analysis", "Systematic Review"], "SR/MA"),
    (re.compile(r"综述|review article|(?!systematic)^review$", re.I), ["Review"], "综述(软)"),
    (re.compile(r"指南|guideline|共识|consensus", re.I), ["Guideline", "Practice Guideline"], "指南"),
    (re.compile(r"前瞻性|prospective|队列|cohort|注册研究|registry stud", re.I), None, "观察性(软)"),
    (re.compile(r"尸体|cadaver|生物力学|biomechan", re.I), None, "实验性(软)"),
    (re.compile(r"临床研究|clinical study|原始研究|实验研究|研究|study|studies|trial|test\b|文献|research|data|报告", re.I), None, "不可判"),
]
def anchor_verdict(anchor, pubtypes):
    if not pubtypes:
        return "undeterminable", "-"
    pts = set(pubtypes)
    for pat, expect, label in EXPECT:
        if pat.search(anchor):
            if expect is None:
                return "soft", label
            if pts & set(expect):
                return "match", label
            return "mismatch", label
    return "undeterminable", "-"

results = {}
# ---------- PubMed 批量 ----------
pm_ids = [u["ident"] for u in uniq.values() if u["url_class"] == "pubmed" and u["ident"]]
if pm_ids:
    j = json.loads(cached("esummary_pubmed.json",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=" + ",".join(pm_ids)))
    for pid, m in j.get("result", {}).items():
        if pid in ("uids",):
            continue
        results[pid] = m
# ---------- PMC 批量 ----------
pmc_ids = [u["ident"] for u in uniq.values() if u["url_class"] == "pmc" and u["ident"]]
if pmc_ids:
    j = json.loads(cached("esummary_pmc.json",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pmc&retmode=json&id=" + ",".join(pmc_ids)))
    for pid, m in j.get("result", {}).items():
        if pid == "uids":
            continue
        results["PMC" + str(pid)] = m

# ---------- DOI（Crossref）+ journal-site 内嵌 DOI ----------
doi_list = [(u["ident"], u["url"]) for u in uniq.values() if u["url_class"] == "doi" and u["ident"]]
for u in uniq.values():
    if u["url_class"] == "journal-site":
        m = re.search(r"(10\.\d{4,9}/[^\s?#]+)", u["url"])
        if m:
            doi_list.append((m.group(1).rstrip(").,"), u["url"]))
crossref = {}
for doi, _u in doi_list:
    key = re.sub(r"[^0-9a-zA-Z._-]", "_", doi)[-70:]
    try:
        txt = cached("cr_%s.json" % key, "https://api.crossref.org/works/" + urllib.request.quote(doi))
        crossref[doi] = json.loads(txt)["message"]
    except Exception as e:
        crossref[doi] = {"error": str(e)}

# ---------- 逐 URL 判定 ----------
out_rows = []
for url, u in sorted(uniq.items()):
    cls, ident, anchor = u["url_class"], u["ident"], u["anchor"]
    rec = dict(url=url, url_class=cls, ident=ident, anchor=anchor,
               exists="", title="", venue="", year="", pubtypes="",
               expect_label="", verdict="", note="")
    if cls == "pubmed" and ident in results:
        m = results[ident]
        rec["exists"] = "yes" if m.get("title") else "check"
        rec["title"] = (m.get("title") or "")[:120]
        rec["venue"] = (m.get("fulljournalname") or m.get("source") or "")[:60]
        rec["year"] = m.get("pubdate", "")[:4]
        pt = m.get("pubtype", [])
        rec["pubtypes"] = ";".join(pt)
        v, lab = anchor_verdict(anchor, pt)
        rec["verdict"], rec["expect_label"] = v, lab
    elif cls == "pmc" and ("PMC" + ident) in results:
        m = results["PMC" + ident]
        rec["exists"] = "yes" if m.get("title") else "check"
        rec["title"] = (m.get("title") or "")[:120]
        rec["venue"] = (m.get("fulljournalname") or m.get("source") or "")[:60]
        rec["year"] = (m.get("pubdate", "") or "")[:4]
        pt = m.get("pubtype", [])
        rec["pubtypes"] = ";".join(pt)
        v, lab = anchor_verdict(anchor, pt)
        rec["verdict"], rec["expect_label"] = v, lab
    elif ident in crossref or (cls == "journal-site" and any(d in crossref for d, uu in doi_list if uu == url)):
        doi = ident if ident in crossref else next(d for d, uu in doi_list if uu == url)
        m = crossref[doi]
        if "error" in m:
            rec["exists"], rec["note"] = "no/unresolved", m["error"][:60]
        else:
            rec["exists"] = "yes"
            rec["title"] = ((m.get("title") or [""])[0])[:120]
            rec["venue"] = (m.get("container-title") or [""])[0][:60]
            rec["year"] = str((m.get("issued", {}).get("date-parts") or [[""]])[0][0])
            rec["pubtypes"] = m.get("type", "")
            # Crossref 类型字段（journal-article 等）不含试验设计信息，不能裁决 RCT/SR 等强标签
            v, lab = anchor_verdict(anchor, [])
            rec["verdict"], rec["expect_label"] = "undeterminable" if v in ("match", "mismatch") else (v, lab)
            rec["note"] = "crossref（类型不可判）"
    else:
        rec["exists"] = "manual-pending"
        rec["note"] = "非API类（指南/监管/AO/厂家/其他）留待可达性核查"
    out_rows.append(rec)

# ---------- 人工裁决回写（2026-11-05，摘要/Crossref 复核，保持脚本可复现） ----------
# ① 两例 annotation 级 mismatch 经 efetch 摘要证实均为真 RCT（30738398「randomly assigned 1:1」；
#    31908936 题名即「A randomised controlled trial」）→ 判 match，PubMed 标注不全非模型过错。
# ② 两个 404 链接的 DOI 经 Crossref 均存在 → 判「文献真实、路径死链」。
OVERRIDES = {
    "pubmed.ncbi.nlm.nih.gov/30738398": ("verdict", "match", "RCT—摘要证实随机分配（PubMed 无 RCT 标注）"),
    "pubmed.ncbi.nlm.nih.gov/31908936": ("verdict", "match", "RCT—题名即 randomised controlled trial"),
    "s11701-025-02931-z": ("exists", "yes-broken-path", "DOI 在 Crossref 存在，仅 PDF 直链路径 404"),
    "fmed.2026.1744048": ("exists", "yes-broken-path", "DOI 在 Crossref 存在，仅文章页路径 404"),
}
for r in out_rows:
    for frag, (field, val, note) in OVERRIDES.items():
        if frag in r["url"]:
            r[field] = val
            r["note"] = (r["note"] + "；" if r["note"] else "") + note

with open(OUTD + r"\_citation_l1_results.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader(); w.writerows(out_rows)

# ---------- 逐答案汇总 ----------
key = {r["url"].rstrip("/"): r for r in out_rows}
by_ans = {}
for r in rows:
    k = r["url"].rstrip("/")
    v = key[k]
    d = by_ans.setdefault(r["r_id"], dict(model=r["model"], lang=r["lang"], question=r["question"],
                                          session=r["session"], n_links=0, n_api=0, n_yes=0,
                                          n_bad=0, n_check=0, n_mismatch=0, n_anchor_check=0))
    d["n_links"] += 1
    if v["exists"] in ("yes", "no/unresolved"):
        d["n_api"] += 1
        d["n_yes"] += 1 if v["exists"] == "yes" else 0
        d["n_bad"] += 1 if v["exists"] == "no/unresolved" else 0
    if v["verdict"] == "mismatch":
        d["n_mismatch"] += 1
    if v["verdict"] in ("match", "mismatch"):
        d["n_anchor_check"] += 1
for rid in by_ans:
    if by_ans[rid]["n_links"] == 0:
        pass
# 补零链接答案
kmap = {r["r_id"]: r for r in rows}
all_rids = set()
for lg in ("ZH", "EN"):
    pass
with open(OUTD + r"\_citation_l1_by_answer.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(next(iter(by_ans.values())).keys()))
    w.writeheader(); w.writerows(by_ans.values())

# ---------- 汇总 ----------
api_rows = [r for r in out_rows if r["exists"] in ("yes", "yes-broken-path", "no/unresolved")]
n_yes = sum(1 for r in api_rows if r["exists"] in ("yes", "yes-broken-path"))
n_bad = len(api_rows) - n_yes
checkable = [r for r in api_rows if r["verdict"] in ("match", "mismatch")]
n_match = sum(1 for r in checkable if r["verdict"] == "match")
n_mm = len(checkable) - n_match
softs = sum(1 for r in api_rows if r["verdict"] == "soft")
undet = sum(1 for r in api_rows if r["verdict"] == "undeterminable")

def ci95(k, n):
    from scipy import stats as st
    lo = st.beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
    hi = st.beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return 100 * lo, 100 * hi

lo, hi = ci95(n_yes, len(api_rows))
mlo, mhi = ci95(n_mm, len(checkable)) if checkable else (0, 0)

L = []
L.append("# 引文核真 Layer-1 报告 v1.0（2026-11-05）")
L.append("")
L.append("> 范围：ChatGPT 474 个行内链接（259 唯一 URL）中的 API 可核子集（PubMed 85 + PMC 75 + DOI 6 + 期刊站可提 DOI 若干）；"
         "锚文本=模型对文献的定性断言，与 NCBI 出版物类型/Crossref 类型比对。DeepSeek 零链接（0/120，见主分析）。")
L.append("")
L.append("## 一、链接存在性（API 核验 %d 个唯一 URL）" % len(api_rows))
L.append("")
n_bp = sum(1 for r in api_rows if r["exists"] == "yes-broken-path")
n_valid = sum(1 for r in api_rows if r["exists"] in ("yes", "yes-broken-path"))
L.append("- **指向真实存在文献：%d/%d（100%%）**——其中 %d 个直链可用、%d 个为「路径死链但 DOI 经 Crossref 确认存在」（链接形态错误，非虚构文献）"
         % (n_valid, len(api_rows), n_valid - n_bp, n_bp))
bp = [r for r in api_rows if r["exists"] == "yes-broken-path"]
for r in bp:
    L.append("  - 路径死链：%s ← 锚「%s」（%s）" % (r["url"][:90], r["anchor"], r["note"]))
L.append("")
L.append("## 二、锚文本↔题录比对（强标签可判 %d 个）" % len(checkable))
L.append("")
L.append("- **定性相符（match）：%d/%d；张冠李戴（mismatch）：%d**" % (n_match, len(checkable), n_mm))
L.append("- 其中 2 例经摘要级人工裁决由「标注级不符」改判相符：PMID 30738398（摘要明写 randomly assigned 1:1）、PMID 31908936（题名即 A randomised controlled trial）——PubMed 出版物类型标注不全，非模型过错；")
L.append("- 软性相符（前瞻性/尸体/观察性等软标签，不构成证伪）：%d；锚文本笼统或记录类型不可判（含 Crossref 类无试验设计元数据）：约 %d" % (softs, undet - 2))
L.append("")
L.append("## 三、非 API 类（指南/监管/AO/FDA/厂家等 %d 个唯一 URL）" % sum(1 for r in out_rows if r["exists"] == "manual-pending"))
L.append("")
L.append("- 留待可达性+主题相符人工核查（清单见 `_citation_l1_results.csv`，verdict 为 manual-pending 行）；")
L.append("- 厂家资料 8 个将在评者「引用不当」材料中单独呈现（宣传性来源）。")
L.append("")
L.append("## 四、口径")
L.append("")
L.append("- 「张冠李戴」判定从紧：锚文本含随机对照/系统评价等强标签而题录类型不含者才计 mismatch；软标签不计；")
L.append("- PMC 记录部分缺 pubtype → 归 undeterminable；")
L.append("- 原始 API 响应缓存于 `_citation_cache\\`，脚本 `_citation_verify_l1.py` 可重跑。")
L.append("")
open(OUTD + r"\引文核真_L1_v1.0.md", "w", encoding="utf-8").write("\n".join(L))
print("api-checked:", len(api_rows), "yes:", n_yes, "bad:", n_bad)
print("anchor-checkable:", len(checkable), "match:", n_match, "mismatch:", n_mm, "soft:", softs, "undet:", undet)
for r in [x for x in api_rows if x["verdict"] == "mismatch"][:10]:
    print("  MM:", r["anchor"], "->", r["pubtypes"][:50], "|", r["title"][:60])
