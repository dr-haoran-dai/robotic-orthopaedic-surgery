# -*- coding: utf-8 -*-
"""探针：看几份回答的引文区格式（回答末尾 12 行），校准引文提取正则。"""
import re
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

ROOT = r"D:\桌面\论文\LLM+机器人手术\v2.0_升级工作区_2026-11-04"
SRCS = [ROOT + r"\04_生成记录\采集_第一部分_ChatGPT中文_2026-11-04.docx",
        ROOT + r"\04_生成记录\采集_第二部分_ChatGPT英文_2026-11-04.docx",
        ROOT + r"\04_生成记录\采集_第三部分_DeepSeek中文_2026-11-04.docx",
        ROOT + r"\04_生成记录\采集_第四部分_DeepSeek英文_2026-11-04.docx"]
PART_RE = re.compile(r"^第([一二三四])部分｜(ChatGPT|DeepSeek)｜")
QH_RE = re.compile(r"^Q(\d+)\s*[｜|]")
SLOT_ZH = re.compile(r"^第([123])次")
SLOT_EN = re.compile(r"^Round ([123])\b")
PART_LANG = {"一": "ZH", "二": "EN", "三": "ZH", "四": "EN"}
FOOTERS = ("本回答由 AI 生成", "（回答由 AI 生成")

answers = {}
model = lang = q = sess = None
buf = []

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
                    lines.append("｜".join(c for c in row if c))
        answers[(model, lang, q, sess)] = lines
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
                flush(); model, lang, q, sess = mp.group(2), PART_LANG[mp.group(1)], None, None; continue
            mq = QH_RE.match(t)
            if p.style.name.startswith("Heading 2") and mq:
                flush(); q, sess = int(mq.group(1)), None; continue
            ms = SLOT_ZH.match(t) or SLOT_EN.match(t)
            if ms:
                flush(); sess = int(ms.group(1)); continue
            if sess is not None and t:
                buf.append(("L", t))
        elif child.tag == qn("w:tbl") and sess is not None:
            tb = Table(child, d)
            buf.append(("T", [[c.text.strip() for c in r.cells] for r in tb.rows]))
flush()
assert len(answers) == 240, len(answers)

# 引文区标记的粗统计
mark_res = [r"^(references|bibliography)\s*[:：]?\s*$", r"^(参考文献|引用文献|参考资料|文献)\s*[:：]?\s*$"]
hits = {}
total_mark = 0
for key, lines in answers.items():
    for ln in lines:
        low = ln.strip().lower().rstrip("*# ")
        for pat in mark_res:
            if re.match(pat, low):
                hits[(key[0], key[1])] = hits.get((key[0], key[1]), 0) + 1
                total_mark += 1
print("显式引文区标记数（按模型·语言）:", hits, "合计", total_mark)

# 抽样看 8 份回答的末尾 12 行
for key in [("ChatGPT", "ZH", 1, 1), ("ChatGPT", "EN", 1, 1), ("DeepSeek", "ZH", 1, 1),
            ("DeepSeek", "EN", 1, 1), ("ChatGPT", "ZH", 15, 2), ("ChatGPT", "EN", 15, 2),
            ("DeepSeek", "ZH", 15, 2), ("DeepSeek", "EN", 15, 2)]:
    lines = answers[key]
    print("=" * 70)
    print(key, "共", len(lines), "行；末尾 12 行：")
    for ln in lines[-12:]:
        print("  |", ln[:110])
