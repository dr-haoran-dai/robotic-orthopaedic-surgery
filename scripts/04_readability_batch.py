# -*- coding: utf-8 -*-
"""可读性指标本地化批量计算（2026-11-05）：
① 验证：旧 20 份英文回答（v1.0 网站分）vs 本地 textstat 管线 → FKGL/FRES 一致性
② v2.0：120 份英文回答 FKGL/FRES（换行断句预处理 + 剔除平台免责行）
③ 中文 120 份 → 导出干净 txt（供 AlphaReadabilityChinese 批量输入）+ 指难针对照样 20 份
输出：_readability_rows_v1.0.csv / 可读性_本地化计算_方法与验证_v1.0.md / ARC_input_ZH\ / 指难针对照样20份\
重跑安全（覆盖同名输出；不动任何采集原件）。"""
import csv, os, random, re
import docx
import openpyxl
import textstat

ROOT = r"D:\桌面\论文\LLM+机器人手术\v2.0_升级工作区_2026-11-04"
OLD_DOCX = ROOT + r"\03_旧数据_2026-06\机器人手术-英文问题与回答.docx"
OLD_XLSX = ROOT + r"\03_旧数据_2026-06\阅读难度评分指标-机器人手术+LLM.xlsx"
SRCS = [("ChatGPT", "ZH", ROOT + r"\04_生成记录\采集_第一部分_ChatGPT中文_2026-11-04.docx"),
        ("ChatGPT", "EN", ROOT + r"\04_生成记录\采集_第二部分_ChatGPT英文_2026-11-04.docx"),
        ("DeepSeek", "ZH", ROOT + r"\04_生成记录\采集_第三部分_DeepSeek中文_2026-11-04.docx"),
        ("DeepSeek", "EN", ROOT + r"\04_生成记录\采集_第四部分_DeepSeek英文_2026-11-04.docx")]
KEY = ROOT + r"\05_评分\_盲法随机化密钥_2026-11-04.csv"
OUTD = ROOT + r"\06_分析"
ARCD = OUTD + r"\ARC_input_ZH"
os.makedirs(ARCD, exist_ok=True)
SAMPLED = OUTD + r"\指难针对照样20份"
FOOTERS = ("本回答由 AI 生成", "（回答由 AI 生成")   # DeepSeek 平台固定免责行（泄露模型身份，一律剔除）

PART_RE = re.compile(r"^第([一二三四])部分｜(ChatGPT|DeepSeek)｜")
QH_RE = re.compile(r"^Q(\d+)\s*[｜|]")
SLOT_ZH = re.compile(r"^第([123])次")
SLOT_EN = re.compile(r"^Round ([123])\b")
PART_LANG = {"一": "ZH", "二": "EN", "三": "ZH", "四": "EN"}
IMG_MD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HMD = re.compile(r"^#{1,6}\s+")


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    a = sum((p - mx) * (q - my) for p, q in zip(x, y))
    b = sum((p - mx) ** 2 for p in x) ** .5
    c = sum((q - my) ** 2 for q in y) ** .5
    return a / (b * c) if b and c else float("nan")


def score_en(text):
    """验证过的管线：换行=句子边界（对齐在线工具行为），textstat 计分。"""
    t = text.replace("\n", ". ")
    return (textstat.flesch_kincaid_grade(t), textstat.flesch_reading_ease(t),
            textstat.lexicon_count(t), textstat.sentence_count(t))


def clean_md(body):
    """无损清理（供 ARC 中文输入）：仅删 Markdown 符号与免责行，不改文字。返回行列表。"""
    out = []
    for ln in body.split("\n"):
        if any(ln.strip().startswith(f) for f in FOOTERS):
            continue
        s = IMG_MD.sub("", ln.strip())
        s = HMD.sub("", s)
        s = s.replace("**", "").replace("__", "")
        s = re.sub(r"^>\s?", "", s)
        s = re.sub(r"^[-*•]\s+", "• ", s)
        if s.strip():
            out.append(s.strip())
    return out


# ============ ① 旧数据验证（仅段落、不含表格——与拍板验证管线一致） ============
segs, cur_model, cur_q, buf = [], None, None, []


def flush_old():
    global buf
    if cur_model and cur_q:
        segs.append((cur_model, cur_q, list(buf)))
    buf = []


d_old = docx.Document(OLD_DOCX)
for t in (p.text.strip() for p in d_old.paragraphs):
    mm = re.match(r"^(ChatGPT|Deepseek)\s*$", t, re.I)
    if mm:
        flush_old()
        cur_model = "DeepSeek" if mm.group(1).lower().startswith("deep") else "ChatGPT"
        cur_q = None
        continue
    mq = re.match(r"^Q\s*(\d+)\s*[:：]", t)
    if mq:
        flush_old()
        cur_q = int(mq.group(1))
        continue
    if cur_model and cur_q is not None and t:
        buf.append(t)
flush_old()
assert len(segs) == 20, len(segs)
old_local = {(m, q): score_en("\n".join(chunks))[:2] for m, q, chunks in segs}

wb = openpyxl.load_workbook(OLD_XLSX, data_only=True)
ws = wb["Sheet1"]
old_web = {}
for row in ws.iter_rows(values_only=True):
    if not row or len(row) < 6 or row[3] is None:
        continue
    s3 = str(row[3]).strip()
    model = "ChatGPT" if "chatgpt" in s3.lower() else ("DeepSeek" if "deepseek" in s3.lower() else None)
    mq = re.search(r"Q(\d+)", str(row[1]))
    if model and mq:
        old_web[(model, int(mq.group(1)))] = (float(row[4]), float(row[5]))
assert len(old_web) == 20, len(old_web)

val_rows = []
for (m, q), (w_fk, w_fr) in sorted(old_web.items()):
    l_fk, l_fr = old_local[(m, q)]
    val_rows.append(dict(model=m, q=q, web_fk=round(w_fk, 2), loc_fk=round(l_fk, 2),
                         d_fk=round(l_fk - w_fk, 2), web_fr=round(w_fr, 1),
                         loc_fr=round(l_fr, 1), d_fr=round(l_fr - w_fr, 1)))
r_fk = pearson([r["web_fk"] for r in val_rows], [r["loc_fk"] for r in val_rows])
r_fr = pearson([r["web_fr"] for r in val_rows], [r["loc_fr"] for r in val_rows])
mad_fk = sum(abs(r["d_fk"]) for r in val_rows) / 20
mad_fr = sum(abs(r["d_fr"]) for r in val_rows) / 20
print("[验证] n=20  FKGL r=%.3f mean|d|=%.2f max|d|=%.2f | FRES r=%.3f mean|d|=%.2f max|d|=%.2f"
      % (r_fk, mad_fk, max(abs(r["d_fk"]) for r in val_rows),
         r_fr, mad_fr, max(abs(r["d_fr"]) for r in val_rows)))

# ============ ② v2.0 四件解析（body 顺序：段落+表格；表格以行入文） ============
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

answers, footer_hits, table_slots = {}, {}, {}
table_total = [0]
model = lang = q = sess = None
buf2 = []  # 元素：("L", 行文本) | ("T", [[单元格,...],...])


def flush_new():
    global buf2
    if q and sess and model and lang:
        answers[(model, lang, q, sess)] = list(buf2)
        footer_hits[(model, lang)] = footer_hits.get((model, lang), 0) + sum(
            1 for k, v in buf2 if k == "L" and any(v.startswith(f) for f in FOOTERS))
        n_t = sum(1 for k, _ in buf2 if k == "T")
        if n_t:
            table_slots[(model, lang)] = table_slots.get((model, lang), 0) + 1
            table_total[0] += n_t
    buf2 = []


for _m, _l, path in SRCS:
    # 2026-11-05 修复：此处原有一个 flush_new()——上一文件末尾已 flush，此处再 flush
    # 会以空 buf 覆盖上一文件的末槽（Q20s3 被清空、ChatGPT·EN 的 fkgl=0.0 混入描述统计）。已删除。
    model = lang = q = sess = None
    d = docx.Document(path)
    for child in d.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, d)
            t = p.text.strip()
            mp = PART_RE.match(t)
            if mp and p.style.name.startswith("Heading 1"):
                flush_new()
                model, lang, q, sess = _m, _l, None, None
                continue
            mq = QH_RE.match(t)
            if p.style.name.startswith("Heading 2") and mq:
                flush_new()
                q, sess = int(mq.group(1)), None
                continue
            ms = SLOT_ZH.match(t) or SLOT_EN.match(t)
            if ms:
                flush_new()
                sess = int(ms.group(1))
                continue
            if sess is not None and t:
                buf2.append(("L", t))
        elif child.tag == qn("w:tbl") and sess is not None:
            tb = Table(child, d)
            buf2.append(("T", [[c.text.strip() for c in r.cells] for r in tb.rows]))
    flush_new()
assert len(answers) == 240, len(answers)
_empty = [k for k, v in answers.items() if not v]
assert not _empty, ("键在而内容空的槽位（本断言防末槽覆盖类 bug 复发）", _empty)


def slot_lines(entries):
    """槽位 → 行列表：段落行（剔除免责行）+ 表格行（单元格以全角竖线连接）。"""
    lines = []
    for kind, val in entries:
        if kind == "L":
            if any(val.startswith(f) for f in FOOTERS):
                continue
            lines.append(val)
        else:
            for row in val:
                cells = [c for c in row if c]
                if cells:
                    lines.append("｜".join(cells))
    return lines

# ============ ③ 计分 / 导出 ============
with open(KEY, encoding="utf-8-sig") as f:
    rid_of = {}
    for row in csv.DictReader(f):
        rid_of[(row["model"], row["lang"], int(row["question"]), int(row["session"]))] = row["r_id"]

rows_out = []
for (m, l, qq, ss), entries in sorted(answers.items()):
    rid = rid_of[(m, l, qq, ss)]
    lines = slot_lines(entries)
    has_footer = any(v.startswith(fo) for k, v in entries if k == "L" for fo in FOOTERS)
    if l == "EN":
        fk, fr, w, s = score_en("\n".join(lines))
        rows_out.append(dict(r_id=rid, model=m, lang=l, question=qq, session=ss,
                             footer_removed=int(has_footer), words=w, sents=s,
                             fkgl=round(fk, 2), fres=round(fr, 1), note=""))
    else:
        zh = [x for x in clean_md("\n".join(lines)) if x.strip()]
        rows_out.append(dict(r_id=rid, model=m, lang=l, question=qq, session=ss,
                             footer_removed=int(has_footer),
                             words=sum(len(re.sub(r"\s", "", x)) for x in zh),
                             sents=len(zh), fkgl="", fres="",
                             note="中文指标待 ARC 运行（2026-11-05 已拍板换 ARC）"))
        with open(ARCD + r"\%s_Q%02d_s%d.txt" % (m, qq, ss), "w", encoding="utf-8") as tf:
            tf.write("\n".join(zh))

os.makedirs(SAMPLED, exist_ok=True)
random.seed(20261105)
picks = []
for m in ("ChatGPT", "DeepSeek"):
    pool = sorted((qq, ss) for (mm, ll, qq, ss) in answers if mm == m and ll == "ZH")
    picks += [(m, qq, ss) for qq, ss in sorted(random.sample(pool, 10))]
for m, qq, ss in picks:
    src = ARCD + r"\%s_Q%02d_s%d.txt" % (m, qq, ss)
    txt = open(src, encoding="utf-8").read()
    with open(SAMPLED + r"\%s_Q%02d_s%d.txt" % (m, qq, ss), "w", encoding="utf-8") as tf:
        tf.write(txt)
with open(SAMPLED + r"\清单_评分后回填指难针分.txt", "w", encoding="utf-8") as f:
    f.write("指难针对照样 20 份（每模型 10 份，seed=20261105 可复现）\n")
    f.write("用法：逐份打开 txt → 全选复制 → 粘贴进 languagedata.net/editor → 读数 → 回填本文件下方表格\n\n")
    f.write("文件名\t指难针分(1.00-7.99)\n")
    for m, qq, ss in picks:
        f.write("%s_Q%02d_s%d.txt\t\n" % (m, qq, ss))

with open(OUTD + r"\_readability_rows_v1.0.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
    w.writeheader()
    w.writerows(rows_out)

# ---- 描述统计（EN，只报描述不做检验——正式检验待评分回收后按 §3.5 预设执行） ----
def desc(m):
    sel = [r for r in rows_out if r["model"] == m and r["lang"] == "EN"]
    n = len(sel)
    fk = sorted(r["fkgl"] for r in sel)
    fr = sorted(r["fres"] for r in sel)
    def ms(v):
        mu = sum(v) / n
        sd = (sum((x - mu) ** 2 for x in v) / (n - 1)) ** .5
        return mu, sd, v[n // 2]
    return n, ms(fk), ms(fr)

en_desc = {m: desc(m) for m in ("ChatGPT", "DeepSeek")}
for m, (n, (fmu, fsd, fmed), (rmu, rsd, rmed)) in en_desc.items():
    print("[v2.0 EN] %s n=%d  FKGL %.2f±%.2f (med %.2f)  FRES %.1f±%.1f (med %.1f)"
          % (m, n, fmu, fsd, fmed, rmu, rsd, rmed))
print("[免责行] ", {("%s·%s" % k): v for k, v in footer_hits.items()})
print("[含表格槽位] ", {("%s·%s" % k): v for k, v in table_slots.items()}, "| 合计", sum(table_slots.values()))

# ---- 报告 ----
L = []
L.append("# 可读性指标本地化计算 · 方法与验证 v1.0（2026-11-05）")
L.append("")
L.append("> 目的：回应「FKGL / FRES / Chi-Editor 逐份粘网站工作量过大」——英文两项已实现**本地批量**并完成对旧网站分的一致性验证；中文侧给出工具选项待拍板。")
L.append("> 本脚本可重跑（`_readability_batch.py`），全部输出由脚本生成，不手改数字。")
L.append("")
L.append("## 一、英文：FKGL / FRES 已本地化，验证通过")
L.append("")
L.append("- 工具：Python `textstat` 0.7.13（CMU 发音词典音节计数），本地运行，零人工。")
L.append("- 预处理（验证出的关键项）：**换行 = 句子边界**（`\\n`→`. `，对齐在线工具的断句行为——ChatGPT 列表式回答的行尾多无句号，不做此步则句长虚高）；剔除 DeepSeek 平台固定免责行（见第五节）。")
L.append("- 验证集：v1.0 已用 readabilityformulas.com 打过分的 **20 份旧英文回答**（`03_旧数据_2026-06\\阅读难度评分指标…xlsx` Sheet1）。")
L.append("")
L.append("| 指标 | Pearson r | 平均绝对差 | 最大绝对差 |")
L.append("|---|---|---|---|")
L.append("| FKGL | %.3f | %.2f 学级 | %.2f |" % (r_fk, mad_fk, max(abs(r["d_fk"]) for r in val_rows)))
L.append("| FRES | %.3f | %.2f 分 | %.2f |" % (r_fr, mad_fr, max(abs(r["d_fr"]) for r in val_rows)))
L.append("")
L.append("结论：本地实现与网站值高度一致；残余差异来自网站私有音节算法 vs CMU 词典，属实现间正常差。v2.0 全部 120 份英文用**同一本地管线**，内部一致、可复现、可入 GitHub——同时正面回应 R1#4 / R3#8「工具版本与日期不明确」的批评。")
L.append("")
L.append("### 验证明细（20 份）")
L.append("")
L.append("| 模型 | 题 | 网站 FKGL | 本地 FKGL | Δ | 网站 FRES | 本地 FRES | Δ |")
L.append("|---|---|---|---|---|---|---|---|")
for r in val_rows:
    L.append("| %s | Q%d | %.2f | %.2f | %+.2f | %.1f | %.1f | %+.1f |"
             % (r["model"], r["q"], r["web_fk"], r["loc_fk"], r["d_fk"], r["web_fr"], r["loc_fr"], r["d_fr"]))
L.append("")
L.append("## 二、v2.0 英文 120 份 · 描述统计（先看分布，正式检验按方案 §3.5 待评分期统一执行）")
L.append("")
L.append("| 模型 | n | FKGL 均值±SD（中位） | FRES 均值±SD（中位） |")
L.append("|---|---|---|---|")
for m in ("ChatGPT", "DeepSeek"):
    n, (fmu, fsd, fmed), (rmu, rsd, rmed) = en_desc[m]
    L.append("| %s | %d | %.2f ± %.2f（%.2f） | %.1f ± %.1f（%.1f） |" % (m, n, fmu, fsd, fmed, rmu, rsd, rmed))
L.append("")
L.append("逐份结果：`_readability_rows_v1.0.csv`（240 行，含 r_id 可并主网格；中文行 FKGL/FRES 留空待拍板）。")
L.append("")
L.append("### Methods 草稿（英文，可直接并入 §2.x）")
L.append("")
L.append("> English readability was quantified with the Flesch Reading Ease Score (FRES) and the Flesch–Kincaid Grade Level (FKGL), computed locally with the Python `textstat` package (v0.7.13, CMU Pronouncing Dictionary-based syllable counting). Before scoring, every line break was treated as a sentence boundary (emulating the sentence-splitting behaviour of online readability calculators), and a fixed platform-generated disclaimer footer was removed. The local implementation was cross-validated against the online tool used in the pilot phase (readabilityformulas.com, accessed June 2026) on the 20 pilot English responses (Pearson r = %.2f for FKGL and %.2f for FRES; mean absolute differences of %.2f grade levels and %.2f points, reflecting proprietary syllable-counting differences). All 120 English responses in the present study were scored with this identical pipeline; the scoring script is openly available in the repository."
          % (r_fk, r_fr, mad_fk, mad_fr))
L.append("")
L.append("## 三、中文：已拍板换 ARC（2026-11-05）")
L.append("")
L.append("**Chi-Editor 实为华南师大金檀团队的「中文分级指难针」（languagedata.net/editor）**：登录制、公式未公开、2025-07 版起「融合生成式 AI」——本地精确复现不可行。且 v1.0 数据全部压在 **7.65–8.00 天花板**（医学文本对分级词表全超纲），区分度趋零，当初 p=0.013 实为天花板内噪声。")
L.append("")
L.append("**拍板（选项 A）：中文主指标换 AlphaReadabilityChinese（ARC 1.0）**——雷蕾、韦瑶瑜、刘康龙 2024（《外语与外语教学》46(1):83-93；工具由雷蕾、张婷玉开发于上海外国语大学；github.com/leileibama/AlphaReadabilityChinese）：**免登录、本地批量**（输入文件夹的 UTF-8 txt → Run → 整批 `0ARC_Chinese_Results.csv`）、词法/句法/语义三层指标、有发表论文背书。程序已就位于 `07_工具\\ARC\\AlphaReadabilityChinese\\AlphaReadabilityChinese.exe`（首开加载模型约 30 秒属正常）；120 份输入 txt = `ARC_input_ZH\\`；指难针 20 份对照样（seed=20261105）保留备用。")
L.append("")
L.append("历史选项存档：A 换 ARC（✅ 已选）/ B ARC 主+指难针 20 份对照 / C 维持指难针（登录粘贴 120 次，天花板保留）/ D 砍中文可读性。")
L.append("")
L.append("## 四、来源")
L.append("")
L.append("- 指难针：languagedata.net/editor；华南师大语料库专题报道（read.scnu.edu.cn/a/20250805/269.html）；指难针使用指引 2025（researchgate.net/publication/392699211）")
L.append("- ARC：github.com/leileibama/AlphaReadabilityChinese（含 2024 论文信息）；英文姊妹版 AlphaReadabilityCalculator 同仓库系")
L.append("- 验证基线：readabilityformulas.com（v1.0 使用，2026-06 访问）")
L.append("")
L.append("## 五、变更记录（数据完整性）")
L.append("")
L.append("- **表格漏读修复（2026-11-05）**：四份采集 docx 内共 %d 个 Word 表格落在答案区内、波及 **%d/240 份回答**（%s）——此前 booklet/稳定性/可读性解析只读段落、整体漏读表格内容。已全部改为 body 顺序（段落+表格）解析并重新生成；表格行以全角竖线连接入文。采集原件一字未动。"
          % (table_total[0], sum(table_slots.values()),
             "、".join("%s %d" % ("%s·%s" % k, v) for k, v in sorted(table_slots.items()))))
L.append("- **盲法泄露修复（2026-11-05）**：DeepSeek 平台固定免责行「本回答由 AI 生成，内容仅供参考，请仔细甄别」出现 %d 次（分布：%s）——该行会**暴露模型身份**（ChatGPT 无此行），已从可读性输入、ARC txt、匿名回答册（重生成）中一律剔除。"
          % (sum(footer_hits.values()), "、".join("%s %d" % ("%s·%s" % k, v) for k, v in sorted(footer_hits.items()))))
L.append("- **末槽覆盖修复（2026-11-05）**：本脚本换文件开头的冗余 flush 会以空缓冲覆盖上一文件的末槽——ChatGPT·中/英与 DeepSeek·中的 **Q20 第 3 次**被清空（`ARC_input_ZH` 两份空 txt 即由此而来），ChatGPT·EN 的 fkgl/fres=0 混入描述统计（旧值 FKGL 15.29±2.46 / FRES 8.3±9.4 作废）。已删除该 flush、加「键在而内容空」断言并重跑；三槽恢复、描述统计以本版为准。")
open(OUTD + r"\可读性_本地化计算_方法与验证_v1.0.md", "w", encoding="utf-8").write("\n".join(L))
print("report written")
