# T2 AI Input Accuracy

- Capsule status: UPDATED
- Source plan: `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md`
- Latest user intent: replace T2 keyword/dictionary prompt with workflow-based unit segmentation prompt, attach page images, then measure accuracy
- Current slice: T2 prompt no longer injects the unit alias dictionary; it now defines the segmentation workflow, unit standards, typical correct/incorrect criteria, input facts, and page-policy field meanings. T2 evidence also carries real page-image attachments via hidden `_attachment_path`.
- Last proven evidence: 43 focused tests passed; same-model live T2 F1 remained hunannongye 1.0000, nannong-undergraduate 0.9565, pku-graduate 0.9565 (macro 0.9710)
- 2026-07-20 workflow+visual Kimi evidence: nannong-undergraduate unit P/R/F1/order = 1.0000/1.0000/1.0000/true, source_seq accuracy 0.9914, boundary F1 0.9524; hunannongye unit P/R/F1/order = 1.0000/1.0000/1.0000/true, source_seq accuracy 0.9781, boundary F1 0.5333.
- Blocked proof: pku-graduate Kimi live run failed with provider 403 usage-limit error before a valid observation artifact was produced; do not count it as model accuracy.
- Input proof: three samples grew to 1.89-2.06x baseline prompt JSON; all 32 break facts aligned to `after_source_seq`; no machine-local page path entered evidence
- Route-alignment proof: source-seq agreement with code_raw changed 0.9313->0.9469, 0.9120->0.9120, 0.9210->0.9728; this is alignment evidence, not gold accuracy
- Residual: hunannongye unit-order exact match regressed true->false; nannong still adds `body_title_block`; pku still misses `toc`
- Gold update: T2 signed standards now carry manual boundary gold for the last three accuracy dimensions: `expected.unit_order`, `expected.units[].boundary.source_seq_range/source_ref_range`, and `expected.units[].page_policy`.
- Gold-backed current code_raw signal: unit set/order still match all three signed standards, but boundary range failures are hunannongye 9, nannong-undergraduate 1, pku-graduate 0; page policy failures should now be interpreted through `page_policy.start/scope`, not the removed old `page` block.
- Next proof: finish three-school live accuracy after Kimi quota recovers or rerun all three with a single alternate multimodal provider.
- Stop condition: input contract is firewall-clean and before/after T2 accuracy is reported under the same evaluator
- No-touch scope: standards, code_raw conclusions, unrelated dirty files
- Parked work: page-policy prompt calibration and lower-cost page-level visual summary cache
