# real-core-v0 Acceptance Guide

Last updated: 2026-06-16

## Purpose

This guide explains what must be accepted before the `real-core-v0` gate can
claim product-quality `PASS`.

Before reviewing individual evidence packages, read
`docs/human/school-template-acceptance-standards-and-plan.md`. It defines the
product boundary for school templates: the official school Word is a rule
source, the generated template is a tested output, and the final student Word is
the delivery artifact.

The review is not a runtime visual approval of generated DOCX files. The review
is a baseline trust step plus a deterministic evidence check: confirm that the
expected school templates, expected student content, expected placement plans,
render evidence, and required Word image evidence are correct enough to become
deterministic harness evidence.

## Current Blockers

`uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage`
currently returns `FAIL`. Word image evidence is present, but the current
generated outputs fail deterministic business acceptance.

| Blocker | What it means | Owner |
| --- | --- | --- |
| `missing_generated_template_gap_evidence` / `generated_template_gap_blocking` / `template_generation_element_missing` | The gate now requires `generated_template.docx`, `generated_template_tree.json`, and `template_gap_report.*`; current generated-template checks find deterministic gaps or missing evidence. | Engineering fixes template generation and OOXML gap checking against reviewed school facts. |
| historical `template_unit_tree_missing` / `template_instruction_paragraph_unclassified` | Existing checked-in reports were produced before the current source-fact parser and generated-template gap gate. They remain useful evidence of old failures but are not current pass proof. | Engineering regenerates reports after template/content/placement/render fixes. |
| `content_heading_semantics_unclassified` / `content_donor_front_matter_not_disposed` | Student content extraction still lacks enough semantic classification and source-format disposal. | Engineering fixes content extraction against reviewed student facts. |
| `placement_actions_collapsed_to_virtual_body_slot` | Placement still maps most content to the fallback body slot instead of target units/elements. | Engineering fixes placement against reviewed case expectations. |
| `render_template_instruction_text_leaked` / `render_append_only_insertion` | Rendered Word still leaks template instructions and appends student content after copied templates. | Engineering fixes rendering after template/content/placement gates are meaningful. |

## What You Need To Accept

### 1. Fixed Evidence Set

Confirm that `real-core-v0` is still exactly this set:

| Type | Ids |
| --- | --- |
| Schools | `hunannongye`, `nannong-undergraduate`, `pku-graduate` |
| Students | `real-student-001`, `real-student-002`, `real-student-003` |
| Render cases | All 3 x 3 school/student combinations listed in `standards/eval_profiles/real-core-v0/cases.yaml` |

If a school or student should be replaced, stop the acceptance review and treat
that as a scope change. Do not sign only part of the fixed profile and call the
full profile complete.

### 2. Full Source-Fact Review Packet

Review the full source-fact packet:

```text
docs/human/real-core-v0-review-packet.md
test_outputs/workbench/real-core-v0-baseline-review/review_packet.md
```

The packet embeds the complete human school-template review sources and student
content review sources. It is the review surface for source facts that later
become runnable baselines. The YAML drafts under
`test_outputs/workbench/real-core-v0-baseline-review/drafts/**` are not sufficient for human
approval by themselves; they are unsigned machine skeletons until engineering
normalizes the accepted source facts into them.

For each template contract, check:

- Required document units are present and ordered correctly.
- Unit elements, sub-elements, element order, same-paragraph relationships,
  keep-together constraints, and missing-content behavior are correct.
- Fixed school text is marked as fixed/template content.
- Fillable, generated, manual-only, optional, and template-default sections are
  classified correctly.
- Required style, layout, header/footer, page-number, table, figure, caption,
  and Word-field constraints match the school evidence.
- Ambiguous or unsupported school behavior is marked as blocking or parked, not
  silently guessed.

For each student content tree, check:

- All visible student content that should be preserved is represented.
- Donor-school or source-template material that should be ignored is marked as
  ignored.
- Title, metadata, abstracts, keywords, headings, body flow, figures, tables,
  formulas, references, appendices, acknowledgements, footnotes, comments, and
  textboxes are classified correctly.
- Unsupported or ambiguous visible objects are explicitly recorded instead of
  disappearing.

For each render plan, check:

- Every student content id has exactly one disposition.
- Target school units, unit elements, and sub-elements are correct.
- Fixed template content is preserved.
- Student content is not placed into fixed-only or manual-only elements.
- Generated fields, missing-content policy, unsupported content, and ask-user
  items are represented as expected.

### 3. Review Metadata

Each signed baseline must include this metadata:

```yaml
review_metadata:
  reviewed_by: <person or role>
  review_source: <input review file or acceptance note>
  source_docx_sha256: sha256:<hex>
  change_reason: initial real-core-v0 baseline
  auto_update_allowed: false
```

Acceptance means the reviewer agrees that current code output did not create or
auto-update the expected facts. If code output was used only as a drafting aid,
the reviewer still owns the final expected facts.

### 4. Word Image Evidence

For every e2e case in `real-core-v0`, there must be one evidence package:

```text
test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/evidence/word_image_evidence.json
test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/evidence/page-*.png
```

The rendered DOCX must exist at:

```text
test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/final.docx
```

The manifest must bind the exported images to that rendered `final.docx` and
record:

- `case_id`, `school_id`, and `student_id`.
- `final_docx_sha256`.
- Microsoft Word application name, version, platform, and export method.
- Positive `page_count` and matching `exported_image_count`.
- One image entry per page with path and SHA-256 hash.
- `export_status: exported`.
- `open_repair_warnings: []`, unless a real warning occurred.

This evidence proves that Word could open and paginate the rendered DOCX into a
stable page-image set. It does not let a human or AI override a deterministic
`FAIL` or `UNKNOWN`.

The local exporter is:

```bash
uv run python scripts/export_real_core_word_evidence.py
```

It requires the nine rendered `final.docx` files to already exist; it does not
create or substitute rendered outputs. Word image evidence must be regenerated
after the nine real `final.docx` files are regenerated by a corrected renderer.

## What Not To Accept

Do not sign any of these as passing evidence:

- "Looks good" notes without baseline dimensions.
- Screenshots or images that are not bound to a `final.docx` hash.
- Current code output copied directly into expected baselines without review.
- Missing comparator modes for required dimensions.
- Any `auto_update_allowed: true` baseline.
- A partial subset of the nine render cases presented as full `real-core-v0`.
- Manual edits to `final.docx` after render.
- AI or Codex visual judgment as final status authority.

## Acceptance Response Template

Use this shape when replying with approval or requested changes:

```text
real-core-v0 acceptance review

Fixed evidence set:
- accepted as listed in standards/eval_profiles/real-core-v0/cases.yaml

Reviewer:
- reviewed_by: <name or role>
- review_source: <file path or this acceptance note>

Accepted baseline groups:
- template contracts: accepted / changes requested
- student content trees: accepted / changes requested
- render plans: accepted / changes requested
- render feature snapshots: accepted / not ready yet
- Word image evidence packages: accepted / not ready yet

Required changes:
- <file path or case id>: <dimension/content that must change>

Approval boundary:
- auto_update_allowed must remain false
- runtime human review is not allowed as a pass/fail gate
- AI may diagnose but may not decide final status
```

## After Acceptance

After the accepted facts are clear, engineering has already completed the first
three evidence-binding steps for the current packet. The current work is to make
steps 4 and 5 pass for business correctness:

1. Move approved school baselines into `standards/schools/<school_id>/v1/`.
2. Move approved profile baselines into
   `standards/eval_profiles/real-core-v0/expected/`.
3. Attach Word image evidence packages under `test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/evidence/`.
4. Fix the four deterministic business stages so template/content/placement/render
   findings are cleared without weakening standards.
5. Rerun:

   ```bash
   uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
   ```

The goal is not to force an immediate `PASS`. A valid result may still be
`FAIL` when the output violates a known standard, or `UNKNOWN` if a required
comparator, artifact normalizer, or deterministic visual oracle is missing. The
important difference is that remaining findings should point to implementation
or verifier gaps, not unsigned baseline evidence.
