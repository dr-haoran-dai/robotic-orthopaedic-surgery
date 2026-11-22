# -*- coding: utf-8 -*-
"""探针2：挖四份采集docx答案区内的超链接（锚文本+目标URL）+ DOI/引文行全文扫描。"""
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

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'），。；<>]+")
CITLINE_RE = re.compile(r"^(?:\[\d{1,2}\]|\d{1,2}[.、．])\s*\S")   # 编号引文行
ETAL_RE = re.compile(r"[A-Z][a-zà-ÿ]+\s+[A-Z][a-zà-ÿ]+.*?(?:et al\.?|20\d{2})", re.S)

stats = {}          # (model,lang) -> dict
samples = []        # (model,lang,q,sess, anchor, url)
doi_hits = []       # (model,lang,q,sess, doi, context)
citline_hits = []   # (model,lang,q,sess, line)

def S(mk):
    return stats.setdefault(mk, dict(links=0, answers_with_links=0, dois=0, citlines=0))

for path in SRCS:
    d = docx.Document(path)
    model = lang = q = sess = None
    in_slot = False
    slot_links = 0
    def flush():
        global slot_links
        if q and sess:
            st = S((model, lang))
            st["links"] += slot_links
            if slot_links:
                st["answers_with_links"] += 1
        slot_links = 0
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
                # 本段内超链接
                for h in p._p.findall(qn("w:hyperlink")):
                    rid = h.get(qn("r:id"))
                    if not rid:
                        continue  # 内部锚点
                    try:
                        url = d.part.rels[rid].target_ref
                    except KeyError:
                        url = "??"
                    anchors = [r.text or "" for r in h.findall(".//" + qn("w:t"))]
                    anchor = "".join(anchors).strip()
                    slot_links += 1
                    if len(samples) < 30:
                        samples.append((model, lang, q, sess, anchor[:40], url[:100]))
                # DOI
                for m in DOI_RE.finditer(t):
                    doi_hits.append((model, lang, q, sess, m.group(0)[:60]))
                # 编号引文行
                if CITLINE_RE.match(t):
                    citline_hits.append((model, lang, q, sess, t[:80]))
        elif child.tag == qn("w:tbl") and sess is not None:
            tb = Table(child, d)
            for r in tb.rows:
                for c in r.cells:
                    for m in DOI_RE.finditer(c.text):
                        doi_hits.append((model, lang, q, sess, m.group(0)[:60]))
    flush()

print("== 超链接统计（答案区内） ==")
for mk, st in sorted(stats.items()):
    print(mk, st)
print("\n== 超链接样例（前30） ==")
for s in samples:
    print(" | ".join(str(x) for x in s))
print("\n== DOI 出现次数 ==", len(doi_hits))
for x in doi_hits[:15]:
    print(x)
print("\n== 疑似编号引文行 ==", len(citline_hits))
for x in citline_hits[:15]:
    print(x)
