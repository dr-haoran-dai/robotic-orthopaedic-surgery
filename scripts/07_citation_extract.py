# -*- coding: utf-8 -*-
"""引文提取（2026-11-05）：
240 份回答中 ①行内超链接（锚文本=模型对文献的定性，URL=指向）——docx XML 级提取，含表格内；
②无出处行内断言（DeepSeek 式「一项研究显示…」）密度统计。
背景：全文无显式 References 区、无 DOI 字符串；ChatGPT 用超链接引证，DeepSeek 零链接。
输出：_citation_links.csv + _citation_claims_density.csv + 引文提取_报告_v1.0.md
"""
import csv, os, re
from collections import defaultdict
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

ROOT = r"D:\桌面\论文\LLM+机器人手术\v2.0_升级工作区_2026-11-04"
SRCS = [ROOT + r"\04_生成记录\采集_第一部分_ChatGPT中文_2026-11-04.docx",
        ROOT + r"\04_生成记录\采集_第二部分_ChatGPT英文_2026-11-04.docx",
        ROOT + r"\04_生成记录\采集_第三部分_DeepSeek中文_2026-11-04.docx",
        ROOT + r"\04_生成记录\采集_第四部分_DeepSeek英文_2026-11-04.docx"]
OUTD = ROOT + r"\06_分析"
os.makedirs(OUTD, exist_ok=True)

PART_RE = re.compile(r"^第([一二三四])部分｜(ChatGPT|DeepSeek)｜")
QH_RE = re.compile(r"^Q(\d+)\s*[｜|]")
SLOT_ZH = re.compile(r"^第([123])次")
SLOT_EN = re.compile(r"^Round ([123])\b")
PART_LANG = {"一": "ZH", "二": "EN", "三": "ZH", "四": "EN"}

# 无出处断言（研究提及）模式：中英
CLAIM_ZH = re.compile(r"(一项|一项[^。；\n]{0,12}|多中心|前瞻性|大型)[^。；\n]{0,30}(研究|试验|荟萃分析|meta分析|Meta分析|综述)(显示|表明|发现|证实|报告|提示|支持)")
CLAIM_EN = re.compile(r"(a|one|several|multiple|many|large)[\s\-][a-z]+\s+(study|studies|trial|trials|RCT|meta[- ]analysis|systematic review|cohort)(\s+(showed|found|demonstrated|reported|suggested|supported|concluded))?", re.I)

def classify(url):
    u = url.lower()
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(?:books/)?(?:\d+)", u)
    if "pubmed.ncbi.nlm.nih.gov" in u:
        pm = re.search(r"/(\d{6,9})/?$", url)
        return "pubmed", pm.group(1) if pm else ""
    if "pmc.ncbi.nlm.nih.gov" in u or u.startswith("https://www.ncbi.nlm.nih.gov/pmc"):
        pc = re.search(r"(?:PMC|articles/)(\d{5,9})", url, re.I)
        return "pmc", pc.group(1) if pc else ""
    if "doi.org" in u:
        dm = re.search(r"doi\.org/(10\.[^\s?#]+)", url)
        return "doi", dm.group(1).rstrip(").,；") if dm else ""
    if "clinicaltrials.gov" in u:
        nct = re.search(r"(NCT\d+)", url, re.I)
        return "registry", nct.group(1).upper() if nct else ""
    if "arxiv.org" in u:
        ax = re.search(r"(\d{4}\.\d{4,5})", url)
        return "preprint", ax.group(1) if ax else ""
    for dom, cls in [("aofoundation.org", "ao"), ("fda.gov", "fda"),
                     ("stryker.com", "manufacturer"), ("smithnephew.com", "manufacturer"),
                     ("zimmerbiomet.com", "manufacturer"), ("stryker", "manufacturer"),
                     ("orthofix", "manufacturer"), ("medtronic", "manufacturer")]:
        if dom in u:
            return cls, ""
    if any(k in u for k in ("nature.com", "wiley.com", "sciencedirect.com", "springer", "thelancet", "jamanetwork", "bmj.com", "oxfordacademic", "liebertpub", "amegroups", "tandfonline", "journals.lww.com", "mdpi.com", "sagepub.com", "thejns.org", "frontiersin.org")):
        return "journal-site", ""
    if any(k in u for k in ("nhc.gov.cn", "nice.org.uk", "aaos.org", "boa.ac.uk", "cns.org", "wfns", "sages.org", "aorn.org", "facs.org", "orthoinfo")):
        return "guideline", ""
    if any(k in u for k in ("gov.cn", "nmpa", "osha.gov", "iaea.org", "mee.gov.cn")):
        return "regulatory", ""
    return "other", ""

# ---- 提取 ----
links = []          # dict rows
answers_meta = {}   # (model,lang,q,sess) -> dict(links=0, claims=0, chars=0, has_ref_section=False)

def meta(mk):
    return answers_meta.setdefault(mk, dict(links=0, claims=0, chars=0))

for path in SRCS:
    d = docx.Document(path)
    model = lang = q = sess = None
    cur = None

    def para_links(p, mk, ctx):
        got = []
        for h in p._p.findall(qn("w:hyperlink")):
            rid = h.get(qn("r:id"))
            if not rid:
                continue
            try:
                url = d.part.rels[rid].target_ref
            except KeyError:
                url = "UNRESOLVED"
            anchor = "".join(r.text or "" for r in h.findall(".//" + qn("w:t"))).strip()
            got.append((anchor, url))
        return got

    def handle_para(p):
        t = p.text.strip()
        mp = PART_RE.match(t)
        if mp and p.style.name.startswith("Heading 1"):
            nonlocal_cur[0] = None
            return ("PART", mp)
        mq = QH_RE.match(t)
        if p.style.name.startswith("Heading 2") and mq:
            return ("Q", int(mq.group(1)))
        ms = SLOT_ZH.match(t) or SLOT_EN.match(t)
        if ms:
            return ("SLOT", int(ms.group(1)))
        return ("BODY", t)

    nonlocal_cur = [None]
    pending = []
    for child in d.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, d)
            kind, val = handle_para(p)
            if kind == "PART":
                pending = []
                model, lang = val.group(2), PART_LANG[val.group(1)]
            elif kind == "Q":
                pending = []
                q = val; sess = None
            elif kind == "SLOT":
                sess = val
                nonlocal_cur[0] = (model, lang, q, sess)
            else:
                mk = nonlocal_cur[0]
                if mk is None or not val:
                    continue
                m = meta(mk)
                m["chars"] += len(val)
                for anchor, url in para_links(p, mk, val):
                    cls, ident = classify(url)
                    links.append(dict(model=mk[0], lang=mk[1], question=mk[2], session=mk[3],
                                      anchor=anchor, url=url, url_class=cls, ident=ident,
                                      in_table=0))
                    m["links"] += 1
                n_cl = len(CLAIM_ZH.findall(val)) if mk[1] == "ZH" else len(CLAIM_EN.findall(val))
                m["claims"] += n_cl
        elif child.tag == qn("w:tbl"):
            mk = nonlocal_cur[0]
            if mk is None:
                continue
            tb = Table(child, d)
            m = meta(mk)
            for row in tb.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for anchor, url in para_links(p, mk, p.text):
                            cls, ident = classify(url)
                            links.append(dict(model=mk[0], lang=mk[1], question=mk[2], session=mk[3],
                                              anchor=anchor, url=url, url_class=cls, ident=ident,
                                              in_table=1))
                            m["links"] += 1
                        t = p.text.strip()
                        if t:
                            m["chars"] += len(t)
                            m["claims"] += len(CLAIM_ZH.findall(t)) if mk[1] == "ZH" else len(CLAIM_EN.findall(t))

assert len(answers_meta) == 240, len(answers_meta)

# r_id 并入（盲法密钥）
key = {}
with open(ROOT + r"\05_评分\_盲法随机化密钥_2026-11-04.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        key[(row["model"], row["lang"], str(row["question"]), str(row["session"]))] = row["r_id"]
kcols = list(csv.DictReader(open(ROOT + r"\05_评分\_盲法随机化密钥_2026-11-04.csv", encoding="utf-8-sig")).fieldnames)
# 兼容密钥列名
sample = next(iter(key.items()))
for r in links:
    r["r_id"] = key.get((r["model"], r["lang"], str(r["question"]), str(r["session"])), "??")

with open(OUTD + r"\_citation_links.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["r_id", "model", "lang", "question", "session",
                                      "anchor", "url", "url_class", "ident", "in_table"])
    w.writeheader(); w.writerows(links)

dens = []
for mk, m in sorted(answers_meta.items()):
    dens.append(dict(r_id=key.get((mk[0], mk[1], str(mk[2]), str(mk[3])), "??"),
                     model=mk[0], lang=mk[1], question=mk[2], session=mk[3],
                     links=m["links"], claim_mentions=m["claims"], chars=m["chars"]))
with open(OUTD + r"\_citation_claims_density.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["r_id", "model", "lang", "question", "session",
                                      "links", "claim_mentions", "chars"])
    w.writeheader(); w.writerows(dens)

# ---- 报告 ----
uniq = {}
for r in links:
    uniq.setdefault(r["url"].rstrip("/"), []).append(r)
by_class = defaultdict(int)
for u, rs in uniq.items():
    by_class[rs[0]["url_class"]] += 1

per_answer_links = defaultdict(list)
for mk, m in answers_meta.items():
    per_answer_links[(mk[0], mk[1])].append(m["links"])
per_answer_claims = defaultdict(list)
for mk, m in answers_meta.items():
    per_answer_claims[(mk[0], mk[1])].append(m["claims"])

L = []
L.append("# 引文提取报告 v1.0（2026-11-05）")
L.append("")
L.append("> 240 份回答全文扫描：**无显式 References/参考文献区、无 DOI 字符串、无编号引文列表**（「1．/2．」编号行均为小节标题）。模型的引证行为只有两种形态：")
L.append("> ① **行内超链接**（ChatGPT）：锚文本即模型对文献的定性断言（如「随机对照试验」），URL 藏于 docx 超链接关系，`p.text` 不可见——本提取为 XML 级（含表格内）；")
L.append("> ② **无出处行内断言**（DeepSeek 为主，ChatGPT 亦有）：「一项前瞻性研究显示…」式研究提及，无链接不可溯源。")
L.append("")
L.append("## 一、行内超链接总览")
L.append("")
L.append("| 模型·语言 | 带链接回答数 | 链接总数 | 每份均数 |")
L.append("|---|---|---|---|")
for mk in [("ChatGPT", "ZH"), ("ChatGPT", "EN"), ("DeepSeek", "ZH"), ("DeepSeek", "EN")]:
    lst = per_answer_links[mk]
    n_with = sum(1 for x in lst if x)
    tot = sum(lst)
    L.append("| %s · %s | %d/60 | %d | %.1f |" % (mk[0], mk[1], n_with, tot, tot / 60))
L.append("")
L.append("**DeepSeek 两个语言组合计 0 个链接。**")
L.append("")
L.append("## 二、链接目标分类（去重后 %d 个唯一 URL）" % len(uniq))
L.append("")
L.append("| 类别 | 唯一 URL 数 | 审计方式 |")
L.append("|---|---|---|")
aud = {"pubmed": "PMID → eutils 取题录+出版物类型，比对锚文本定性",
       "pmc": "PMCID → 同上（PMC 题录）",
       "doi": "DOI → Crossref 元数据",
       "journal-site": "期刊站直达，抓题名核对（Crossref 可补题录）",
       "registry": "ClinicalTrials.gov NCT 号 → 注册库元数据",
       "preprint": "arXiv 号 → 元数据（非同行评审，计入来源层级判定）",
       "guideline": "指南/学会官网（NHC/NICE/AAOS/BOA/CNS 等，核可达性+主题相符）",
       "regulatory": "监管/政府文件（NMPA/OSHA/IAEA 等，核可达性）",
       "ao": "AO Surgery Reference 技术页（非文献，核可达性+主题相符）",
       "fda": "FDA 注册/K 号文件（灰色文献，核可达性）",
       "manufacturer": "厂家资料（核可达性，属宣传性来源将计入「引用不当」判定材料）",
       "other": "逐条人工归类"}
for cls, n in sorted(by_class.items(), key=lambda x: -x[1]):
    L.append("| %s | %d | %s |" % (cls, n, aud.get(cls, "人工")))
L.append("")
L.append("## 三、无出处断言密度（研究提及/千字，描述性）")
L.append("")
L.append("| 模型·语言 | 每份「研究提及」均数 | 千字密度 |")
L.append("|---|---|---|")
for mk in [("ChatGPT", "ZH"), ("ChatGPT", "EN"), ("DeepSeek", "ZH"), ("DeepSeek", "EN")]:
    cl = per_answer_claims[mk]
    chs = [answers_meta[(mk[0], mk[1], q, s)]["chars"] for (m2, l2, q, s) in answers_meta if (m2, l2) == mk]
    tc, th = sum(cl), sum(chs) / 1000
    L.append("| %s · %s | %.1f | %.2f |" % (mk[0], mk[1], sum(cl) / 60, tc / th if th else 0))
L.append("")
L.append("> 正则口径为保守下限（只抓「研究/试验/study/trial + 显示/showed」组合）；DeepSeek 的具体数字型断言（如「1.23° vs 2.89°」）单独抽查溯源。")
L.append("")
L.append("## 四、审计下一步（Layer 1 链接核真）")
L.append("")
L.append("1. 唯一 URL 去重后按类别批量核验：PubMed/PMC 走 eutils（题名/期刊/年/出版物类型），DOI 走 Crossref；")
L.append("2. 核验两问：**链接是否有效指向真实存在的文献**；**锚文本定性是否与题录相符**（「随机对照试验」↔出版物类型含 RCT——不符即「张冠李戴」）；")
L.append("3. 无链接断言：按题抽样溯源（DeepSeek 数字型断言重点），无可溯源出处者在评分表标注供评者判「引用不当」；")
L.append("4. 产出：`_citation_links.csv`（%d 行）为逐链接审计底表；`_citation_claims_density.csv`（240 行）并入主网格。" % len(links))
L.append("")
L.append("## 五、限制")
L.append("")
L.append("- 超链接关系为 Word 粘贴保真结果；若粘贴过程丢链接（锚文本在、关系丢失），本方法计为无链接——保守估计；")
L.append("- 断言正则为保守下限，密度比较仅作描述；")
L.append("- 采集原件未做任何改动。")
L.append("")
open(OUTD + r"\引文提取_报告_v1.0.md", "w", encoding="utf-8").write("\n".join(L))
print("links:", len(links), "unique URLs:", len(uniq))
print("by class:", dict(by_class))
for mk in [("ChatGPT", "ZH"), ("ChatGPT", "EN"), ("DeepSeek", "ZH"), ("DeepSeek", "EN")]:
    lst = per_answer_links[mk]
    print(mk, "with-links answers:", sum(1 for x in lst if x), "total links:", sum(lst))
