# T2 AI Input Accuracy

- Capsule status: DONE
- Source plan: `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md`
- Latest user intent: execute the T2 input/preprocessing slice first, then measure accuracy
- Current slice: enriched clean T2 evidence with compact text, real page-start, and source-seq-aligned break facts; Prompt stayed unchanged
- Last proven evidence: 43 focused tests passed; same-model live T2 F1 remained hunannongye 1.0000, nannong-undergraduate 0.9565, pku-graduate 0.9565 (macro 0.9710)
- Input proof: three samples grew to 1.89-2.06x baseline prompt JSON; all 32 break facts aligned to `after_source_seq`; no machine-local page path entered evidence
- Route-alignment proof: source-seq agreement with code_raw changed 0.9313->0.9469, 0.9120->0.9120, 0.9210->0.9728; this is alignment evidence, not gold accuracy
- Residual: hunannongye unit-order exact match regressed true->false; nannong still adds `body_title_block`; pku still misses `toc`
- Gold update: T2 signed standards now carry manual boundary gold for the last three accuracy dimensions: `expected.unit_order`, `expected.units[].boundary.source_seq_range/source_ref_range`, and `expected.units[].page`.
- Gold-backed current code_raw signal: unit set/order still match all three signed standards, but boundary range failures are hunannongye 9, nannong-undergraduate 1, pku-graduate 0; page policy failures remain hunannongye 16, nannong-undergraduate 11, pku-graduate 12 because current unit pages are still mostly `unknown`.
- Next proof: redesign the T2 task prompt to teach document segmentation, TOC-vs-content discrimination, fragment merging, and page/source-seq order before rerunning the same evaluation
- Stop condition: input contract is firewall-clean and before/after T2 accuracy is reported under the same evaluator
- No-touch scope: T2 prompt text, T3/T4 behavior, standards, code_raw conclusions, unrelated dirty files
- Parked work: Prompt restructuring and page-policy output/bridge alignment
