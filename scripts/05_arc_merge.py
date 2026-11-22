# -*- coding: utf-8 -*-
"""ARC 结果合并（2026-11-05）：
读 ARC_output\0ARC_Chinese_Results.csv（file_id 命名 {Model}_Q{nn}_s{n}）→ r_id 并入可读性网格
→ _readability_rows_v1.1.csv（240 行，中英全指标）+ 可读性_ARC合并_v1.0.md（中文描述统计+Methods段）
仅描述统计；正式检验按方案 §3.5 待评分期统一执行。"""
import csv, os

ROOT = r"D:\桌面\论文\LLM+机器人手术\v2.0_升级工作区_2026-11-04"
OUTD = ROOT + r"\06_分析"
ARC = OUTD + r"\ARC_output\0ARC_Chinese_Results.csv"
GRID_IN = OUTD + r"\_readability_rows_v1.0.csv"
KEY = ROOT + r"\05_评分\_盲法随机化密钥_2026-11-04.csv"

rid_of = {}
for row in csv.DictReader(open(KEY, encoding="utf-8-sig")):
    rid_of[(row["model"], row["lang"], int(row["question"]), int(row["session"]))] = row["r_id"]

ARC_COLS = ["lexical_richness", "syntactic_richness",
            "semantic_accuracy_n", "semantic_accuracy_v", "semantic_accuracy_n_v",
            "semantic_accuracy_c", "semantic_richness_n", "semantic_clarity_n",
            "semantic_noise_n"]
ARC_CN = {"lexical_richness": "词法丰富度", "syntactic_richness": "句法丰富度",
          "semantic_accuracy_n": "语义准确性·名", "semantic_accuracy_v": "语义准确性·动",
          "semantic_accuracy_n_v": "语义准确性·名动", "semantic_accuracy_c": "语义准确性·内容词",
          "semantic_richness_n": "语义丰富度·名", "semantic_clarity_n": "语义清晰度·名",
          "semantic_noise_n": "语义噪声·名"}
PRIMARY = ["lexical_richness", "syntactic_richness", "semantic_accuracy_n_v"]

# ---- 读 ARC ----
arc = {}
for row in csv.DictReader(open(ARC, encoding="utf-8-sig")):
    fid = row["file_id"].strip()
    m = None
    for tag in ("ChatGPT", "DeepSeek"):
        if fid.startswith(tag + "_"):
            m = tag
            break
    assert m, fid
    qq, ss = fid[len(m) + 1:].split("_s")
    k = (m, "ZH", int(qq[1:]), int(ss))
    arc[k] = {c: float(row[c]) for c in ARC_COLS if row.get(c) not in (None, "", "nan")}
assert len(arc) == 120, len(arc)

# ---- 并入网格 ----
grid = list(csv.DictReader(open(GRID_IN, encoding="utf-8-sig")))
assert len(grid) == 240
n_filled = 0
for r in grid:
    k = (r["model"], r["lang"], int(r["question"]), int(r["session"]))
    vals = arc.get(k)
    if vals:
        n_filled += 1
        for c in ARC_COLS:
            r["arc_" + c] = ("%.4f" % vals[c]) if c in vals else ""
        r["note"] = "ARC已并入" if r["lang"] == "ZH" else r["note"]
    else:
        for c in ARC_COLS:
            r["arc_" + c] = ""
assert n_filled == 120, n_filled

with open(OUTD + r"\_readability_rows_v1.1.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(grid[0].keys()))
    w.writeheader(); w.writerows(grid)

# ---- 描述统计（ZH × 模型；只描述不检验） ----
def desc(vals):
    n = len(vals)
    mu = sum(vals) / n
    sd = (sum((x - mu) ** 2 for x in vals) / (n - 1)) ** .5
    s = sorted(vals)
    med = s[n // 2]
    return n, mu, sd, med, s[0], s[-1]

zh_desc = {}
for col in PRIMARY:
    zh_desc[col] = {}
    for m in ("ChatGPT", "DeepSeek"):
        vals = [v[col] for k, v in arc.items() if k[0] == m]
        zh_desc[col][m] = desc(vals)

# 全指标一览（模型间均差，描述性）
all_diff = []
for col in ARC_COLS:
    cg = [v[col] for k, v in arc.items() if k[0] == "ChatGPT"]
    ds = [v[col] for k, v in arc.items() if k[0] == "DeepSeek"]
    d = sum(cg) / 60 - sum(ds) / 60
    all_diff.append((col, sum(cg) / 60, sum(ds) / 60, d))

# ---- 报告 ----
L = []
L.append("# 可读性 · ARC 合并与中文描述统计 v1.0（2026-11-05）")
L.append("")
L.append("> 工具：AlphaReadabilityChinese 1.0（雷蕾、韦瑶瑜、刘康龙 2024，《外语与外语教学》46(1):83-93；上海外国语大学开发），本地批量运行于 `06_分析\\ARC_input_ZH\\`（120 份 UTF-8 txt，去 Markdown、剔平台免责行、表格行展平）。")
L.append("> 输出 9 项指标（词法/句法/语义三层），全部并入主网格 `_readability_rows_v1.1.csv`（240 行，中英全指标，r_id 可并评分网格）。")
L.append("")
L.append("## 一、预指定主要指标 · 描述统计（n=60/组，只描述不检验）")
L.append("")
L.append("| 指标 | 模型 | 均值±SD | 中位 | 范围 |")
L.append("|---|---|---|---|---|")
for col in PRIMARY:
    for m in ("ChatGPT", "DeepSeek"):
        n, mu, sd, med, lo, hi = zh_desc[col][m]
        L.append("| %s（%s） | %s | %.2f ± %.2f | %.2f | %.2f–%.2f |" % (ARC_CN[col], col, m, mu, sd, med, lo, hi))
L.append("")
L.append("## 二、全部 9 项指标 · 组均值一览（描述性）")
L.append("")
L.append("| 指标 | ChatGPT 均值 | DeepSeek 均值 | 差值（CG−DS） |")
L.append("|---|---|---|---|")
for col, cg, ds, d in all_diff:
    L.append("| %s（%s） | %.3f | %.3f | %+.3f |" % (ARC_CN[col], col, cg, ds, d))
L.append("")
L.append("> 指标方向说明：lexical/syntactic richness 与 semantic richness 数值越高文本越「丰富」（词法/句法/语义层面越复杂）；semantic accuracy 越高词义越常规可预期；semantic clarity 越高越清晰、noise 越高越噪杂。解读按 ARC 论文口径，模型间比较仅描述，不在此做推断。")
L.append("")
L.append("## 三、Methods 草稿（中文可读性，可直接并入 §2.x）")
L.append("")
L.append("> Chinese readability was assessed with AlphaReadabilityChinese v1.0 (Lei, Wei & Liu 2024, *Foreign Languages and Their Teaching* 46(1):83–93; developed at Shanghai International Studios University [sic — Shanghai International Studies University]), an open-source tool computing lexical, syntactic, and semantic indices for Chinese texts. Responses were exported as plain UTF-8 text with markdown markers removed, table rows flattened, and a fixed platform-generated disclaimer footer removed. Lexical richness, syntactic richness, and semantic accuracy (noun–verb) were pre-specified as the primary Chinese readability indices; all nine indices are reported. The tool was run locally in a single batch over all 120 Chinese responses, with identical preprocessing for both models.")
L.append("")
L.append("> （注意：上段 Universities 拼写以最终稿校对为准——正确为 Shanghai International Studies University。）")
L.append("")
L.append("## 四、溯源与复现")
L.append("")
L.append("- ARC 程序：`07_工具\\ARC\\AlphaReadabilityChinese\\AlphaReadabilityChinese.exe`（GitHub leileibama/AlphaReadabilityChinese，Windows 版 453MB，2024-03 构建）")
L.append("- 输入集：`ARC_input_ZH\\`（`_readability_batch.py` 生成，可重跑复现）")
L.append("- 原始输出：`ARC_output\\0ARC_Chinese_Results.csv`（工具原样产出，未改动）")
L.append("- 合并脚本：`_arc_merge.py`（本脚本，可重跑；网格升级为 `_readability_rows_v1.1.csv`）")
L.append("")
open(OUTD + r"\可读性_ARC合并_v1.0.md", "w", encoding="utf-8").write("\n".join(L))

print("merged:", n_filled, "/120 → _readability_rows_v1.1.csv")
for col in PRIMARY:
    for m in ("ChatGPT", "DeepSeek"):
        n, mu, sd, med, lo, hi = zh_desc[col][m]
        print("%-24s %s  %.2f±%.2f (med %.2f)" % (col, m, mu, sd, med))
print("report written")
