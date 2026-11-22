# -*- coding: utf-8 -*-
"""评分入库质检（2026-11-05）：
评者A/B 已填表 → 完整性（240×2）/取值域（KP三选、错误数≥0、安全无有、Likert1-4）/
题号与盲法密钥一致性 / 分布总览（KP/错误/安全/Likert）。
只质检不统计——推断检验待 QA 通过后按 §3.5 管线执行。"""
import csv
from collections import Counter
import openpyxl

ROOT = r"D:\桌面\论文\LLM+机器人手术\v2.0_升级工作区_2026-11-04"
FILES = {"A": ROOT + r"\05_评分\评分表_评者A_v1.1_已填.xlsx",
         "B": ROOT + r"\05_评分\评分表_评者B_v1.1_已填.xlsx"}
KEY = ROOT + r"\05_评分\_盲法随机化密钥_2026-11-04.csv"

# 密钥：r_id → (model, lang, question)
kmap = {}
for row in csv.DictReader(open(KEY, encoding="utf-8-sig")):
    kmap[row["r_id"]] = (row["model"], row["lang"], int(row["question"]))

KP_VALS = {"覆盖", "部分覆盖", "未覆盖"}
LIK_COLS = ["准确性1-4", "完整性1-4", "清晰度1-4", "一致性1-4"]

data = {}
issues = []
for rater, path in FILES.items():
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["评分"]
    hdr = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    col = {h: i + 1 for i, h in enumerate(hdr)}
    rows = []
    seen = set()
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(row=r, column=col["回答编号"]).value
        if rid is None:
            continue
        rid = str(rid).strip()
        seen.add(rid)
        rec = {"r_id": rid, "题号": ws.cell(row=r, column=col["题号"]).value}
        for k in range(1, 8):
            rec["KP%d" % k] = ws.cell(row=r, column=col["KP%d" % k]).value
        rec["错误陈述数"] = ws.cell(row=r, column=col["错误陈述数"]).value
        rec["错误简述"] = ws.cell(row=r, column=col["错误简述（最多3条，分号隔开）"]).value
        rec["不安全建议"] = ws.cell(row=r, column=col["不安全建议"]).value
        rec["不安全简述"] = ws.cell(row=r, column=col["不安全内容简述"]).value
        for lc in LIK_COLS:
            rec[lc] = ws.cell(row=r, column=col[lc]).value
        rec["备注"] = ws.cell(row=r, column=col["备注"]).value
        rows.append(rec)
    data[rater] = rows

    # --- 质检 ---
    exp = set("R%03d" % i for i in range(1, 241))
    for rid in sorted(exp - seen):
        issues.append("[%s] 缺行 %s" % (rater, rid))
    for rid in sorted(seen - exp):
        issues.append("[%s] 多出/异常编号 %s" % (rater, rid))
    for rec in rows:
        rid = rec["r_id"]
        # 题号一致
        kq = kmap.get(rid)
        if kq is None:
            issues.append("[%s] %s 不在密钥中" % (rater, rid))
            continue
        if str(rec["题号"]).strip().lstrip("Qq") != str(kq[2]):
            issues.append("[%s] %s 题号不符：表=%s 密钥=Q%d" % (rater, rid, rec["题号"], kq[2]))
        # KP 取值
        for k in range(1, 8):
            v = rec["KP%d" % k]
            if v not in KP_VALS:
                issues.append("[%s] %s KP%d 非法值 %r" % (rater, rid, k, v))
        # 错误数
        e = rec["错误陈述数"]
        if not isinstance(e, (int, float)) or e < 0 or e != int(e):
            issues.append("[%s] %s 错误数非法 %r" % (rater, rid, e))
        # 安全
        if rec["不安全建议"] not in ("无", "有"):
            issues.append("[%s] %s 不安全建议非法 %r" % (rater, rid, rec["不安全建议"]))
        elif rec["不安全建议"] == "有" and not rec["不安全简述"]:
            issues.append("[%s] %s 标不安全但无简述" % (rater, rid))
        # Likert
        for lc in LIK_COLS:
            v = rec[lc]
            if v not in (1, 2, 3, 4):
                issues.append("[%s] %s %s 非法值 %r" % (rater, rid, lc, v))

print("行数：A=%d B=%d（应各240）" % (len(data["A"]), len(data["B"])))
print("质检问题数：", len(issues))
for s in issues[:30]:
    print(" ", s)

# --- 分布总览 ---
for rater in "AB":
    rows = data[rater]
    kp_pool = Counter()
    for rec in rows:
        for k in range(1, 8):
            kp_pool[rec["KP%d" % k]] += 1
    tot = sum(kp_pool.values())
    errs = [int(rec["错误陈述数"]) for rec in rows]
    uns = Counter(rec["不安全建议"] for rec in rows)
    lik = {lc: Counter(rec[lc] for rec in rows) for lc in LIK_COLS}
    print("\n[%s] KP分布: " % rater + "、".join("%s %d (%.1f%%)" % (k, v, 100 * v / tot) for k, v in kp_pool.items()))
    print("[%s] 错误数: 0分=%d  >0=%d  合计错误=%d  最大=%d" %
          (rater, sum(1 for e in errs if e == 0), sum(1 for e in errs if e > 0), sum(errs), max(errs)))
    print("[%s] 不安全: %s" % (rater, dict(uns)))
    for lc in LIK_COLS:
        print("[%s] %s: %s  均值 %.2f" % (rater, lc, dict(sorted(lik[lc].items())),
              sum(k * v for k, v in lik[lc].items()) / 240))
    notes = [rec["备注"] for rec in rows if rec["备注"]]
    if notes:
        print("[%s] 备注 %d 条，样例: %s" % (rater, len(notes), notes[:3]))

# 简存质检通过的干净数据（供统计管线）
import json
out = {r: {rec["r_id"]: {k: v for k, v in rec.items() if k != "r_id"} for rec in rows} for r, rows in data.items()}
json.dump(out, open(ROOT + r"\06_分析\_ratings_clean.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("\n→ _ratings_clean.json 已存（质检未通过项见上，若0问题即可进统计）")
