# Data and analysis repository

**Study:** *Coverage, accuracy and citation traceability of ChatGPT and DeepSeek answers to robotic orthopaedic surgery questions: a bilingual expert audit*

This repository hosts the de-identified data and analysis code for the study above, as described in the manuscript's "Availability of data and materials" statement. It contains:

- all 240 anonymised AI responses in their corrected final form (two responses were corrected after collection; see *Correction history* below);
- the 480 original independent per-item ratings from both blinded raters (as submitted, never overwritten);
- the post-review clinical-adjudication layer: the 20 flagged error candidates, the third-surgeon decisions (7 counted factual-error events, 9 wording-only, 3 rejected, 1 unresolved), the 25 key-point interpretation records, and per-response adjudicated counts;
- the merged analysis dataset (key-point coverage, ratings, error counts), readability metrics (FKGL/FRES; ARC for Chinese), and corrected text/content-stability metrics;
- the citation-audit datasets and the citation-verification cache (API responses backing every automated verification verdict);
- all analysis scripts, in pipeline order, plus the post-review recompute scripts that produced the final numbers;
- the pre-specified statistical analysis plan (Chinese original).

**Not included, by design:** the blinding key that maps booklet IDs (R001–R240) to model/language/session cells. It is referenced by file name in some scripts but its contents were never distributed and remain with the corresponding author. Post-adjudication working forms carrying the adjudicator's signature images, and the raw collection documents (which display model/platform labels and the collector's interface), are likewise withheld; every number they contain appears in the manuscript, its Additional files, or the datasets here.

## Correction history

Two response texts were corrected after collection and after the original independent ratings, which were preserved unchanged (no back-writing):

- one response was corrected on 2026-11-11 (third correction round for its question), with a hash-chained correction log retained by the authors;
- one response (R207) was replaced on 2026-11-19 with its recovered original session text; the raters' original forms (which contained flag entries made on the earlier text) were preserved as submitted, and the discrepancy was resolved through the documented adjudication layer rather than by rescoring.

All analysis files here are the corrected (post-R207) versions generated from the canonical data snapshot dated 2026-11-19.

## Directory layout

```
data/
  question_bank/   20-question bank, per-question key-point reference standards
                   (pre-locked before any generation), the 140 locked key points
                   as machine-readable CSV, and the post-review evidence-source
                   registry (E1–E26) backing the per-key-point evidence audits
  responses/       Corrected anonymised responses, 240 JSON lines
                   (r_id, model, lang, question, session, text)
  ratings/         Original independent ratings: 480-row consolidated file
                   (both raters) and the two per-rater submissions as exported
                   from the frozen rating workbooks (Chinese column names)
  analysis/        Corrected merged per-response analysis rows (key-point
                   coverage, error counts, both raters), full and derived
                   readability rows (FKGL/FRES/ARC metrics)
  stability/       Corrected per-triplet content and text stability
                   (one row per question x model x language cell; 80 rows)
  adjudication/    Post-review clinical adjudication: 20 candidate events with
                   third-surgeon decisions and rationales, per-response
                   adjudicated counts, exploratory question-level comparisons,
                   receipt/counts record, and the 25 key-point interpretation
                   records
  citations/       Extracted hyperlink inventory, per-answer citation-layer
                   results, verification verdicts for all 259 unique URL
                   strings, claim-density counts
  citation_cache/  Raw API responses (Crossref / Europe PMC) backing the
                   automated verdicts
scripts/           Original analysis pipeline, numbered in execution order
  phase2/          Post-review recompute and correction scripts (final numbers,
                   R207 integration, ARC merge, corrected figure rendering),
                   with a dependency register
docs/              Pre-specified statistical analysis plan (Chinese)
```

## Pipeline order

Original pipeline (data collection → primary analysis):

1. `scripts/01_ratings_intake_qa.py` – intake checks on the two filled rating workbooks
2. `scripts/02_ratings_main_analysis.py` – primary and secondary outcome analysis (coverage, dimension ratings, error/safety counts, reliability)
3. `scripts/03_stats_full_pack.py` – full inferential statistics (t/Wilcoxon, mixed models, Spearman, McNemar, Holm)
4. `scripts/04_readability_batch.py` – textstat readability (FKGL, FRES)
5. `scripts/05_arc_merge.py` – AlphaReadabilityChinese metrics merge (Chinese responses)
6. `scripts/06_stability_text_analysis.py` – within-cell text stability (Jaccard, coverage range)
7. `scripts/07_citation_extract.py` – hyperlink extraction from the 240 responses
8. `scripts/08_citation_verify_l1.py` – Layer-1 citation verification (Crossref/Europe PMC APIs)
9. `scripts/09_probe_hyperlinks.py` – hyperlink probing
10. `scripts/10_probe_ref_tails.py` – reference-tail probing used in the fabrication audit

Post-review correction/recompute stage (produced the final published numbers; see `scripts/phase2/DEPENDENCY_REGISTER.json`):

- `phase2/prepare_text_metrics.py`, `phase2/recompute_phase2_core.py`, `phase2/complete_phase2_tables.py` – corrected recomputation of core results and tables
- `phase2/merge_validated_ARC.py` – merge of the re-run AlphaReadabilityChinese outputs
- `phase2/integrate_R207_adjudication.py`, `phase2/stage_R207.py` – integration of the R207 correction and the adjudication layer
- `phase2/render_figure2_v2.py`, `phase2/render_figure2_corrected.py` – corrected Figure 2 rendering

Dependencies: Python 3.11 with `pandas`, `numpy`, `scipy`, `openpyxl`, `python-docx`, `textstat`; [AlphaReadabilityChinese](https://github.com/leileibama/AlphaReadabilityChinese) 1.0 for Chinese readability. Scripts contain absolute paths from the authors' environment (`ROOT` constants); adjust `ROOT` to this repository's location to re-run. The phase2 scripts preserve the original source dependencies (see the dependency register) and are provided as the authoritative record of how the final numbers were produced.

## Data dictionary (main files)

`data/ratings/ratings_independent_480.csv` — one row per rater x response (480 rows), the original independent ratings consolidated: `sample_id` (S001–S240), `model`, `lang` (ZH/EN), `question`, `session`, `rater` (A/B), `kp1`–`kp7` (key-point verdicts: 2 = covered, 1 = partially covered, 0 = not covered), `err` (erroneous-statement count), `unsafe`, and the four 1–4 Likert dimensions (accuracy, completeness, clarity, consistency; 4 best).

`data/ratings/ratings_rater[AB]_per-item.csv` — the same ratings as submitted by each rater, exported from the frozen rating workbooks (Chinese column names retained verbatim: 回答编号, 题号, KP1–KP7 with 覆盖/部分覆盖/未覆盖, 错误陈述数, 不安全建议, 准确性/完整性/清晰度/一致性 1-4).

`data/analysis/analysis_rows_R207_corrected.csv` — one row per response (240) with both raters and the values used in the paper: `r_id`, `model`, `lang`, `question`, `session`; `kp_a`/`kp_b`/`kp` (key-point coverage fraction per rater and rater-mean); `err_a`/`err_b`/`err`; `unsafe`; the four Likert dimensions per rater and rater-mean.

`data/analysis/readability_full_240.csv` — per-response readability detail (`fkgl`, `fres`, word/sentence counts, `footer_removed` flag, ARC metrics for Chinese responses). `readability_derived_240.csv` — the derived metrics file used in analysis joins.

`data/stability/content_and_text_stability_corrected.csv` — one row per question x model x language triplet (80 rows): `kp_mean`, `range` (content-layer coverage range), `same_rate`, `mean_j` (mean pairwise text Jaccard).

`data/adjudication/adjudicated_events_20.csv` — the 20 post-review error candidates: `event_id`, `r_id`, cell identifiers, `decision` (支持原标记 / wording-only / rejected / unresolved), `counted_factual_error`, `unresolved`, `rationale` (Chinese), provenance fields (`source_ids`, dates, source workbook SHA-256). `responses_after_R207.csv` — per-response adjudicated counts; `question_comparisons_after_R207.csv` — exploratory question-level comparisons; `keypoint_interpretations_25_signed_record.csv` — the 25 third-adjudicator key-point interpretations with decision and signed-record status (signature images withheld; see MANIFEST).

`data/citations/citation_l1_results.csv` — one row per unique URL with the Layer-1 verification verdict (`exists`: yes / yes-broken-path / no/unresolved/manual-pending). Manual-pending URLs (n = 103) are listed in full in the manuscript's Additional file 5.

## Provenance and integrity

Every file here is a byte-identical copy (or, for the rater CSVs, a direct sheet export) of the authors' frozen working files, restaged 2026-11-22 from the canonical data snapshot dated 2026-11-19. The file-by-file provenance list is in [`MANIFEST.md`](MANIFEST.md). The rating-workbook exports and all citation datasets are hash-identical to the earlier (2026-11-06) staging, confirming those layers never changed.

## Licence and citation

Released to support peer review and reproducibility. A licence and citation entry will be added upon publication; until then, please cite the manuscript. Questions via the journal's correspondence route.
