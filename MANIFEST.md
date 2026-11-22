# MANIFEST — file provenance (v1.0 restage)

Restaged 2026-11-22 by `_restage_github_v1_0.py` (re-runnable; leak scan asserted 0 hits;
row-count and adjudication-count assertions built in). This restage supersedes the 2026-11-06
staging: it draws on the canonical corrected data snapshot dated 2026-11-19 (`00_当前有效数据/`,
`CURRENT_STATE.json`) so that every public file matches the v1.0 manuscript. Sources live in the
authors' private workspace; every file below is a byte-identical copy unless noted "export".

| Repo path | Source (original file) | Notes |
|---|---|---|
| data/question_bank/question_bank_20items_zh.md | 02_题库与蓝图/20题题库_v0.1_2026-11-04.md | working doc, verbatim |
| data/question_bank/key_points_reference_standard_zh.md | 02_题库与蓝图/逐题key_points参考标准模板_v0.1.md | pre-locked standards |
| data/question_bank/key_points_140_locked_zh.csv | 00_当前有效数据/02_当前分析输入/key_points_140_locked_zh.csv | 140 locked key points, machine-readable |
| data/question_bank/key_points_140_postreview_evidence.csv | 00_当前有效数据/02_当前分析输入/key_points_140_postreview_evidence.csv | post-review evidence-source registry (E1–E26: verified titles, DOIs/PMIDs, reading scope) backing the per-key-point evidence audits |
| data/responses/responses_corrected_240.jsonl | 00_当前有效数据/02_当前分析输入/responses_corrected_240.jsonl | corrected final response texts (240) |
| data/ratings/ratings_independent_480.csv | 00_当前有效数据/02_当前分析输入/ratings_independent_480.csv | original independent ratings, both raters, as submitted |
| data/ratings/ratings_raterA_per-item.csv | 05_评分/评分表_评者A_v1.1_已填.xlsx | export of "评分" sheet only; the Chinese "说明" instruction sheet is withheld (contains organiser name) |
| data/ratings/ratings_raterB_per-item.csv | 05_评分/评分表_评者B_v1.1_已填.xlsx | export of "评分" sheet only |
| data/analysis/analysis_rows_R207_corrected.csv | 00_当前有效数据/02_当前分析输入/analysis_rows_R207_corrected.csv | corrected merged per-response rows |
| data/analysis/readability_full_240.csv | 00_当前有效数据/02_当前分析输入/readability_full_240.csv | full per-response readability detail |
| data/analysis/readability_derived_240.csv | 00_当前有效数据/02_当前分析输入/readability_derived_240.csv | derived readability metrics |
| data/stability/content_and_text_stability_corrected.csv | 00_当前有效数据/03_当前结果/CONTENT_AND_TEXT_STABILITY_CORRECTED.csv | corrected per-triplet stability (80 rows) |
| data/adjudication/adjudicated_events_20.csv | 00_当前有效数据/03_当前结果/临床裁决/adjudicated_events_20.csv | 20 candidates with third-surgeon decisions (7 counted / 9 wording / 3 rejected / 1 unresolved) |
| data/adjudication/responses_after_R207.csv | 00_当前有效数据/03_当前结果/临床裁决/responses_after_R207.csv | per-response adjudicated counts |
| data/adjudication/question_comparisons_after_R207.csv | 00_当前有效数据/03_当前结果/临床裁决/question_comparisons_after_R207.csv | exploratory question-level comparisons |
| data/adjudication/RECEIPT_AND_COUNTS.json | 00_当前有效数据/03_当前结果/临床裁决/RECEIPT_AND_COUNTS.json | receipt and layer counts (26 flags / 25 adjusted-form / 7 counted; three layers never mixed) |
| data/adjudication/keypoint_interpretations_25_signed_record.csv | 00_当前有效数据/02_当前分析输入/keypoint_interpretations_25_signed_record.csv | 25 interpretations; signature images withheld (signed record dated 2026-11-19 retained in source workbook) |
| data/citations/citation_links.csv | 06_分析/_citation_links.csv | 474 links / 259 unique URLs; hash-identical to 2026-11-06 staging |
| data/citations/citation_l1_by_answer.csv | 06_分析/_citation_l1_by_answer.csv | per-answer roll-up; hash-identical to 2026-11-06 staging |
| data/citations/citation_l1_results.csv | 06_分析/_citation_l1_results.csv | 259 verdicts: 156 API-verified, 103 manual-pending; hash-identical to 2026-11-06 staging |
| data/citations/citation_claims_density.csv | 06_分析/_citation_claims_density.csv | assertion-density counts; hash-identical to 2026-11-06 staging |
| data/citation_cache/*.json | 06_分析/_citation_cache/ | raw API responses backing verdicts |
| docs/statistical_analysis_plan_zh.md | 01_方案/统计分析计划_终版_2026-11-05.md | pre-specified SAP (Chinese original of the translated Additional file 4) |
| scripts/01…10_*.py | 06_分析/_*.py | renamed with pipeline-order prefixes; content untouched |
| scripts/phase2/*.py (8) + DEPENDENCY_REGISTER.json | 00_当前有效数据/05_脚本登记/原工作脚本快照/ | post-review correction/recompute scripts, registry verbatim; one documented redaction: path strings naming the third adjudicator inside `integrate_R207_adjudication.py` replaced with "第三裁决人" (byte-level string substitution only; logic untouched; the referenced signature-bearing workbook is itself excluded) |

## Deliberately excluded

| Excluded | Reason |
|---|---|
| 05_评分/_盲法随机化密钥_2026-11-04.csv | blinding key — never distributed (Availability statement: "excluding the blinding key") |
| 05_评分/_make_rating_package.py, _build_anonymized_booklet.py | packaging scripts that read/generate the key permutation; publishing them would let the key be reconstructed |
| 05_评分/发老师/ (instruction sheet, rating-methods memo) | rater-facing logistics; contains organiser name |
| 04_生成记录/ (raw collection docx, screenshots) | raw responses carry model/platform labels; Availability promises the *anonymised* responses; screenshots show collector's platform UI |
| 03_旧数据_2026-06/ | superseded June 2026 pilot material |
| responses_anonymised_R001-R240.docx (the 2026-11-06 staging's response booklet) | superseded: pre-dates the 2026-11-11 and 2026-11-19 response-text corrections; replaced by data/responses/responses_corrected_240.jsonl |
| _ratings_clean.json, _analysis_rows.csv, _readability_rows_v1.1.csv, _stability_text_rows.csv, _content_stability_trios.csv | superseded pre-correction analysis intermediates; replaced by the corrected files staged above |
| 00_当前有效数据/01_来源与证据/已收裁决与裁决后调整表/*.xlsx | adjudication working forms with adjudicator signature images; numbers appear in the adjudication CSVs and the manuscript's Additional files |
| 06_分析/*.md frozen reports (评分主分析/统计结果包/引文核真/可读性/三轮一致性) | internal Chinese analysis outputs; all numbers they contain appear in the manuscript and Additional files; regenerable via scripts |
| 07_工具/ARC* | third-party tool; linked in README instead |
| 00_当前有效数据/verify_current_data.py | internal QA verifier wired to the private directory layout |

## Pending before public push

- [ ] publication of the manuscript (the Availability statement deposits the repository upon publication)
- [ ] licence choice (README placeholder)
- [ ] citation entry once the paper has a DOI
- [ ] supervisor sign-off on docs/statistical_analysis_plan_zh.md (carried over from the 2026-11-06 staging)
- [ ] re-run `_restage_github_v1_0.py` if any frozen source changes before the push
