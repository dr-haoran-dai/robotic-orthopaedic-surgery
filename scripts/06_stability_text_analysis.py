# -*- coding: utf-8 -*-
"""三轮一致性·文本层分析（v1.1，2026-11-05）：
每题×每模型×每语言的 3 次回答 → 长度、两两词汇重叠（Jaccard）、分带。
中文=字符二元组集；英文=小写词元集。剔除 DeepSeek 固定免责行；表格内容计入（行级展平）。
v1.1 变更：①解析改为 body 顺序（段落+表格）——v1.0 漏读 122 个表格；②免责行模式修正
（v1.0 写的「（回答由 AI 生成」实际匹配 0 次，正确串为「本回答由 AI 生成」，共 100 行）。
输出：06_分析\三轮一致性_文本层_v1.1.md + _stability_text_rows.csv（覆盖）"""
import csv, os, re
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
FOOTERS = ("本回答由 AI 生成", "（回答由 AI 生成")

# ---- 解析（body 顺序：段落+表格） ----
answers = {}
model = lang = q = sess = None
buf = []  # ("L", 段文本) | ("T", [[单元格,...],...])

def flush():
    global buf
    if q and sess and model and lang:
        lines = []
        for k, v in buf:
            if k == "L":
                if any(v.strip().startswith(f) for f in FOOTERS):
                    continue
                lines.append(v)
            else:
                for row in v:
                    lines.append(" ".join(c for c in row if c))
        answers[(model, lang, q, sess)] = " ".join(ln for ln in lines if ln.strip()).strip()
    buf = []

for path in SRCS:
    flush()
    model = lang = q = sess = None
    d = docx.Document(path)
    for child in d.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, d)
            t = p.text.strip()
            mp = PART_RE.match(t)
            if mp and p.style.name.startswith("Heading 1"):
                flush()
                model, lang, q, sess = mp.group(2), PART_LANG[mp.group(1)], None, None
                continue
            mq = QH_RE.match(t)
            if p.style.name.startswith("Heading 2") and mq:
                flush()
                q, sess = int(mq.group(1)), None
                continue
            ms = SLOT_ZH.match(t) or SLOT_EN.match(t)
            if ms:
                flush()
                sess = int(ms.group(1))
                continue
            if sess is not None and t:
                buf.append(("L", t))
        elif child.tag == qn("w:tbl") and sess is not None:
            tb = Table(child, d)
            buf.append(("T", [[c.text.strip() for c in r.cells] for r in tb.rows]))
flush()
assert len(answers) == 240, len(answers)

# ---- 指标 ----
def clean(text, lg):
    if lg == "ZH":
        t = re.sub(r"[\s\d\W]+", "", text, flags=re.UNICODE)
        return set(t[i:i+2] for i in range(len(t) - 1)), len(re.sub(r"\s", "", text))
    else:
        toks = re.findall(r"[a-z0-9]+", text.lower())
        return set(toks), len(toks)

def jac(a, b):
    return len(a & b) / len(a | b) if (a or b) else 1.0

def band(v):
    return "高（近乎复写）" if v >= 0.60 else ("中（措辞部分重合）" if v >= 0.35 else "低（措辞大异）")

rows = []
for qn in range(1, 21):
    for mdl in ("ChatGPT", "DeepSeek"):
        for lg in ("ZH", "EN"):
            tri = {}
            for s in (1, 2, 3):
                body = answers.get((mdl, lg, qn, s), "")
                tri[s] = clean(body, lg)
            lens = [tri[s][1] for s in (1, 2, 3)]
            sets = [tri[s][0] for s in (1, 2, 3)]
            j12, j13, j23 = jac(sets[0], sets[1]), jac(sets[0], sets[2]), jac(sets[1], sets[2])
            mean_j = (j12 + j13 + j23) / 3
            mean_len = sum(lens) / 3
            cv = (max(lens) - min(lens)) / mean_len if mean_len else 0
            rows.append(dict(q=qn, model=mdl, lang=lg,
                             len1=lens[0], len2=lens[1], len3=lens[2],
                             j12=round(j12, 3), j13=round(j13, 3), j23=round(j23, 3),
                             mean_j=round(mean_j, 3), relspread=round(cv, 3),
                             band=band(mean_j)))

with open(OUTD + r"\_stability_text_rows.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

def agg(pred):
    sel = [r for r in rows if pred(r)]
    n = len(sel)
    return (n, sum(r["mean_j"] for r in sel) / n if n else 0,
            sum(r["relspread"] for r in sel) / n if n else 0)

summary = {}
for mdl in ("ChatGPT", "DeepSeek"):
    for lg in ("ZH", "EN"):
        summary[(mdl, lg)] = agg(lambda r, m=mdl, l=lg: r["model"] == m and r["lang"] == l)
summary[("ChatGPT", "ALL")] = agg(lambda r: r["model"] == "ChatGPT")
summary[("DeepSeek", "ALL")] = agg(lambda r: r["model"] == "DeepSeek")
summary[("ALL", "ZH")] = agg(lambda r: r["lang"] == "ZH")
summary[("ALL", "EN")] = agg(lambda r: r["lang"] == "EN")
overall = agg(lambda r: True)
bands = {}
for r in rows:
    bands[r["band"]] = bands.get(r["band"], 0) + 1

srt = sorted(rows, key=lambda r: r["mean_j"])
top3 = srt[:3]
hi3 = srt[-3:]

L = []
L.append("# 三轮一致性 · 文本层分析 v1.1（2026-11-05）")
L.append("")
L.append("> 数据：240 份（20 题 × 2 模型 × 2 语言 × 3 次独立新会话，同日采集）。")
L.append("> 指标：中文=字符二元组集合的 Jaccard 重叠；英文=小写词元集合的 Jaccard 重叠；已剔除 DeepSeek 固定免责行（100 行，v1.0 模式写错未生效，本版修正）；表格内容已计入（122 个表格行级展平，v1.0 漏读）。长度=中文字符数/英文词数。相对极差=(最长−最短)/均值。")
L.append("> 分带（描述性）：≥0.60 高（近乎复写）；0.35–0.60 中（同构异辞）；<0.35 低（实质分歧）。")
L.append("> **口径注意**：这是**文本层**一致性（词汇重叠），不等于**内容层**一致性（要点覆盖/结论是否一致）——后者待评者评分后补算。")
L.append("")
L.append("## 总览")
L.append("")
L.append("| 分组 | 三元组数 | 平均两两 Jaccard | 平均相对极差 |")
L.append("|---|---|---|---|")
for (mdl, lg), (n, mj, cv) in summary.items():
    L.append("| %s · %s | %d | %.3f | %.3f |" % (mdl, lg, n, mj, cv))
L.append("| **全体** | %d | **%.3f** | %.3f |" % overall)
L.append("")
L.append("**核心读数：80 组三元组中，达到「近乎复写」（J≥0.60）的为 %d 组**——即同题、同模型、同日三个新会话没有一次产出措辞层面近乎相同的回答。" % bands.get("高（近乎复写）", 0))
L.append("")
L.append("分带分布：" + "、".join("%s %d 组（%.0f%%）" % (k, v, 100 * v / len(rows)) for k, v in bands.items()))
L.append("")
L.append("## 最不稳定的三组（差异最大）")
L.append("")
for r in top3:
    L.append("- Q%d · %s · %s：均值 %.3f（%s）；三轮长度 %s/%s/%s" %
             (r["q"], r["model"], r["lang"], r["mean_j"], r["band"], r["len1"], r["len2"], r["len3"]))
L.append("")
L.append("## 最稳定的三组（最接近复写）")
L.append("")
for r in hi3:
    L.append("- Q%d · %s · %s：均值 %.3f（%s）；三轮长度 %s/%s/%s" %
             (r["q"], r["model"], r["lang"], r["mean_j"], r["band"], r["len1"], r["len2"], r["len3"]))
L.append("")
L.append("## 每题明细（80 组）")
L.append("")
L.append("| 题 | 模型 | 语言 | 长度1 | 长度2 | 长度3 | J12 | J13 | J23 | 均值 | 相对极差 | 分带 |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    L.append("| Q%d | %s | %s | %s | %s | %s | %.2f | %.2f | %.2f | %.2f | %.2f | %s |" %
             (r["q"], r["model"], r["lang"], r["len1"], r["len2"], r["len3"],
              r["j12"], r["j13"], r["j23"], r["mean_j"], r["relspread"], r["band"]))
L.append("")
L.append("## 待续（评分回收后）")
L.append("- 内容层一致性：同一题三轮的要点覆盖一致率（如按评者逐轮 KP 勾选算 kappa/一致比例）")
L.append("- 错误数与安全性指标的轮间方差")
L.append("- 明细数据：`_stability_text_rows.csv`（统计脚本直接读）")

open(OUTD + r"\三轮一致性_文本层_v1.1.md", "w", encoding="utf-8").write("\n".join(L))
print("report written;", len(rows), "trios")
print("overall mean J = %.3f" % overall[1])
for (m, l), (n, mj, cv) in summary.items():
    print("%s·%s: n=%d meanJ=%.3f spread=%.3f" % (m, l, n, mj, cv))
print("bands:", bands)
print("lowest:", [(r["q"], r["model"], r["lang"], r["mean_j"]) for r in top3])
print("highest:", [(r["q"], r["model"], r["lang"], r["mean_j"]) for r in hi3])
