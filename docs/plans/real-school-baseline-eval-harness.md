# Real School Baseline Eval Harness Plan

Date: 2026-06-14
Owner: Product + Engineering
Status: Partially implemented; Wave 0 harness infrastructure shipped, signed
baselines and Word evidence still blocking full `real-core-v0`
Last reviewed: 2026-06-14

## Purpose

This plan defines how DocFit will turn three real school templates and three
real student documents into executable eval-harness baselines.

The product question is not "can the code generate a DOCX?" The product
question is:

> Given fixed source evidence and signed baselines, can DocFit deterministically
> prove whether each stage output matches the expected school-template,
> student-content, placement, and render contract?

AI may diagnose structured failures, but AI does not decide `PASS`, `FAIL`, or
`UNKNOWN`.

## Current Repo Facts

- `SPEC.md` is the canonical product spec for stage boundaries, gate states,
  reports, and AI RCA limits.
- `inputs/README.md` is the current catalog of raw school templates, raw student
  documents, and human review evidence.
- Current runnable signed standard coverage is only `demo-school/v1`.
- Real school evidence exists under `inputs/**`, but it is source evidence only.
  It has not yet been normalized into runnable `standards/schools/**`
  contracts.
- The shared alignment note
  `inputs/shared-template-recognition-alignment-review.txt` already defines the
  core domain model: `unit -> element -> sub-element`.

## Zoom-Out Map

Control plane:

- `src/docfit/cli/`: public `docfit eval ...` and `docfit convert` entry
  points.
- `src/docfit/harness/`: standards loading, profile/case registry, status,
  coverage, reports, issue clusters, and audit helpers.
- `src/docfit/convert/`: orchestration across verified stage artifacts.

Stage plane:

- `src/docfit/stages/template_parse/`: school template to template artifact.
- `src/docfit/stages/content_extract/`: student DOCX to visible content ledger
  and student content artifact.
- `src/docfit/stages/placement/`: template artifact plus student content
  artifact to placement plan.
- `src/docfit/stages/render/`: placement plan plus template assets to final
  DOCX, render manifest, and feature snapshot.

Evidence and baseline plane:

- `inputs/**`: raw DOCX/DOC files and human review evidence.
- `standards/schools/**`: runnable signed school standards only.
- `standards/eval_profiles/**`: profile-level expected artifacts, fixed cases,
  and real evidence baselines.
- `reports/**`: generated proof from eval runs.

AI RCA plane:

- Issue clusters and diagnosis packets are downstream of deterministic
  findings.
- AI can suggest likely generic code defects and regression tests.
- AI cannot judge final status, update baselines, or create school-specific core
  branches.

## Eng-Review Recommendation

Interactive engineering review questioning was not used in this default coding
mode. This section applies the same review frame in prose.

Architecture fit:

- The strongest seam is `baseline -> actual artifact -> comparator -> finding`.
  This keeps school knowledge in signed baselines, not in stage implementation.
- `real-core-v0` should not replace `bootstrap-core`. Bootstrap proves harness
  mechanics; real-core proves product evidence against fixed real files.
- Stage 4 must remain a renderer. If it changes placement decisions, the
  pipeline has lost its verified chain.
- Comparator policy should be data-driven by signed dimensions. The code can
  dispatch by comparator mode, but the baseline owns what is required.

Data flow:

```text
inputs source evidence
  -> signed template unit contracts
  -> signed student content tree goldens
  -> selected case registry
  -> aligned render plan goldens
  -> stage artifacts
  -> normalized feature snapshots
  -> dimensional comparators
  -> findings / issue clusters
  -> AI RCA advisory
```

Public contract / boundary:

- `standards/schools/**` contains signed runnable school standards.
- `standards/eval_profiles/real-core-v0/**` contains profile cases and expected
  artifacts for this fixed real evidence loop.
- `inputs/**` remains source evidence, not executable standard.
- Reports may summarize human review, but reports are not allowed to mutate or
  redefine the baseline.

Accepted seam:

- Add real-school proof through baseline schemas, signed expected artifacts,
  profile registry, comparators, and stage verifiers.
- Do not start by improving visual formatting or adding school-specific core
  code branches.

Rejected alternatives:

- Compare whole DOCX binaries: rejected because OOXML packaging and generated
  fields make byte-level diff noisy and not semantically aligned.
- Let AI inspect final DOCX and judge quality: rejected because it violates the
  harness-first contract.
- Generate goldens from current code output: rejected because it turns bugs into
  signed expectations.
- Put real-school source evidence directly under `standards/schools/**` before
  signing: rejected because it makes non-runnable evidence look runnable.
- Make all 3 x 3 combinations silently required without naming them as the
  explicit profile target: rejected because unsigned scope causes false PASS
  claims.

## Accepted Decisions

1. The current development/eval phase fixes the sample set:
   - Three real school template inputs.
   - Three real student document inputs.
   - Nine school/student render combinations for Stage 3 and Stage 4.
2. Human-reviewed source evidence is the reference of truth for initial
   baselines. Current code output must not be used to generate or auto-update
   expected baselines.
3. Generated DOCX quality is judged by structured dimensions, not by whole-file
   binary diff or AI visual impression.
4. The same hierarchy must drive template recognition, student content
   recognition, placement synthesis, and render verification:

   ```text
   document unit -> unit element -> sub-element / nested unit
   ```

5. `UNKNOWN` remains blocking. If a dimension cannot be read, compared, or
   trusted, the result is not promoted to `PASS`.
6. The plan designs the organized current prototype contract at `HEAD`; it does
   not preserve migrated legacy surfaces by default.
7. Word-rendered page images are required evidence for every `real-core-v0`
   render case, but their scope is deliberately narrow: they supplement blind
   spots that structural DOCX/OOXML checks cannot prove. They must not duplicate
   content, placement, style, hash, or manifest checks that are already covered
   by deterministic verifiers.
8. `human_review_evidence` is baseline provenance, not a runtime human review
   step. Once the eval flow runs, no person is expected to inspect the output to
   decide the current run status.

## Fixed Evidence Set

### School Templates

| School id | Template input | Human review evidence |
| --- | --- | --- |
| `hunannongye` | `inputs/school-hunannongye-requirement.docx` | `inputs/school-hunannongye-template-review.txt` |
| `nannong-undergraduate` | `inputs/school-nannong-undergraduate-template.docx` | `inputs/school-nannong-undergraduate-template-review.txt` |
| `pku-graduate` | `inputs/school-pku-graduate-template.docx` | `inputs/school-pku-graduate-template-review.txt` |

### Student Documents

| Student id | Source input | Human review evidence |
| --- | --- | --- |
| `real-student-001` | `inputs/real-student-001-source.docx` | `inputs/real-student-001-content-review.md` |
| `real-student-002` | `inputs/real-student-002-source.docx` | `inputs/real-student-002-content-review.md` |
| `real-student-003` | `inputs/real-student-003-source.docx` | `inputs/real-student-003-content-review.md` |

## Baseline Model

The executable standard is not one file. It is a small set of signed,
versioned, machine-readable baselines derived from the fixed evidence set.

### 1. Template Unit Contract

One per school template version.

It answers:

- What document units exist?
- What is the unit order?
- Which units are required, template-default, generated, manual-only, or
  optional?
- Which elements exist inside each unit?
- What is the element order?
- Which text is fixed school-template text?
- Which elements are fillable from student content or metadata?
- Which elements are generated by Word fields or system logic?
- What styles, paragraph rules, numbering rules, headers, footers, page-number
  rules, and section-decision rules are required?
- What same-page, keep-together, floating-object, table, figure, caption, and
  hidden-structure constraints must be preserved?
- What happens when student content is missing?

Candidate path:

```text
standards/schools/<school_id>/v1/template_unit_contract.yaml
```

### 2. Student Content Tree Golden

One per fixed student document.

It answers:

- Which visible user content exists?
- Which donor-school or source-template pages must be ignored?
- What is the title and metadata recognized from the source?
- What are the Chinese and English abstracts and keywords?
- What is the body heading tree?
- What is the ordered body flow?
- Which figures, tables, formulas, references, appendices, acknowledgements,
  footnotes, and other visible objects exist?
- What source references and content hashes bind each expected node to the
  source DOCX?
- Which content is unsupported, ambiguous, or manual-review only?

Candidate path:

```text
standards/eval_profiles/real-core-v0/expected/student_content_trees/<student_id>.yaml
```

### 3. Aligned Render Plan Golden

One per signed school/student render case. `real-core-v0` contains nine render
cases.

It answers:

- For each template unit, what source fills it?
- For each student content node, where is it placed or how is it resolved?
- Which fixed school-template content is preserved?
- Which generated fields are produced?
- Which default template modules are preserved even when the student source has
  no matching content?
- Which manual-only units are carried forward without automatic filling?
- Which missing content creates placeholders, comments, or blocking review?
- Which content is explicitly unsupported or ask-user?

Candidate path:

```text
standards/eval_profiles/real-core-v0/expected/render_plans/<case_id>.yaml
```

### 4. Render Feature Snapshot Golden

One per render case once the expected render features have been derived from
reviewed baseline evidence and locked for harness use.

It answers:

- What structural features must be present in the final DOCX?
- Which content hashes prove rendered visible content coverage?
- Which fixed text, generated fields, headers, footers, page-number rules,
  styles, numbering, captions, and object relationships must be present?
- Which layout dimensions are machine-verifiable now?
- Which visual blind-spot dimensions remain `UNKNOWN` until a deterministic
  visual checker exists?

Candidate path:

```text
standards/eval_profiles/real-core-v0/expected/render_feature_snapshots/<case_id>.json
```

## Stable Identity Rules

Every executable baseline must use stable ids. The comparator cannot reliably
match expected and actual nodes by visible text alone.

Required id families:

| Id family | Example | Owner |
| --- | --- | --- |
| Template unit id | `abstract_cn` | Template Unit Contract |
| Template element id | `abstract_cn.keyword_label` | Template Unit Contract |
| Student content id | `student001.body.flow.019.table` | Student Content Tree Golden |
| Render plan action id | `case_pku_001.place.table_019` | Aligned Render Plan Golden |
| Evidence ref | `inputs/real-student-001-content-review.md#table-1` | Baseline author |
| Output feature ref | `word/document.xml:p[42]` | Feature snapshot extractor |

Rules:

- Stable ids are signed baseline identity, not implementation-local indexes.
- Content hashes prove text/object coverage, but hashes do not replace semantic
  ids.
- A changed baseline id is a standard change and requires review.

## Baseline Review Metadata

"Signed" in this plan means reviewed and locked for harness use. It is not a
legal signature and does not require cryptographic signing in the prototype.

Every real baseline should record:

```yaml
reviewed_by: <person or role>
review_source: <human review file or evidence packet>
source_docx_sha256: <hash of the raw DOCX/DOC input>
change_reason: <why this baseline exists or changed>
auto_update_allowed: false
```

This metadata explains who confirmed the baseline, which review file or evidence
packet it came from, which source file hash it binds to, why it exists or
changed, and that it cannot be auto-updated from current code output.

## Human Review Evidence Scope

`human_review_evidence` means reviewed source evidence used to create or change
baselines. It is not a runtime checker, not a Codex visual judgment, and not a
manual approval step during normal eval.

Its job is to answer:

> Why is this expected baseline trusted?

It does not answer:

> Did this generated DOCX pass?

Allowed baseline-time evidence:

- Source review files under `inputs/**`, such as school template reviews,
  student content reviews, and the shared alignment review.
- Baseline review metadata that binds a machine-readable baseline to the raw
  input hash and the human review source.
- Approved school exception evidence, when a school-specific behavior is
  intentionally allowed.
- Human review notes for adding or changing a signed visual blind-spot
  dimension, such as "this fixed statement page must remain visually intact."

Runtime boundary:

- The eval run does not pause for a human to inspect the generated DOCX.
- The harness may check that required `human_review_evidence` exists and is
  hash-bound to the baseline.
- The harness may not use `human_review_evidence` to override an actual runtime
  artifact mismatch.
- If a required actual-output dimension has no deterministic verifier or
  configured oracle, the run returns `UNKNOWN` for that dimension.

Not allowed as final gate evidence:

- Codex visual inspection by itself.
- Unversioned screenshots without output DOCX hash and Word export metadata.
- "Looks good" notes that do not reference baseline dimensions.
- Current code output used as the source of a baseline.
- Manual edits to `final.docx` after rendering.

Status rules:

- Missing required baseline review evidence returns `UNKNOWN` during standards
  audit or baseline loading.
- Runtime mismatches are decided by deterministic comparators/oracles, not by
  asking a human during the run.
- AI visual findings remain advisory and can create issue clusters or RCA
  suggestions, but they cannot change `summary.status`.
- Reports must separate baseline provenance, machine-verified runtime evidence,
  and AI-advisory findings.

## Four-Stage Acceptance

### Stage 1: Template Recognition

Reference baseline:

```text
Template Unit Contract
```

Actual artifact:

```text
Template Artifact / extracted template unit tree
```

Required comparison dimensions:

- Unit presence.
- Unit order.
- Unit status: `required`, `template_default`, `manual_only`, `generated`,
  `optional`.
- Unit source policy and fill policy.
- Unit page behavior: page break, section requirement, header/footer, page
  number profile.
- Element presence and element order.
- Fixed text preservation.
- Fillable/manual/generated element policy.
- Style dimensions: font family, size, bold/italic, alignment, indentation,
  spacing, line spacing, outline level, direct formatting where required.
- Relationship dimensions: same paragraph, inline element, table-internal,
  header/footer, Word field, object anchor.
- Layout constraints: keep-together, keep-with-next, fixed template-page
  integrity, figure-caption/table-caption grouping.
- Hidden/OOXML structure constraints when the review marks them blocking:
  fields, bookmarks, content controls, drawings, signature lines, relationships.

Pass/fail semantics:

- `PASS`: all required template dimensions are extracted and match the signed
  contract within explicit tolerance.
- `FAIL`: the signed contract is present and the extractor can read the
  dimension, but actual output violates a required dimension.
- `UNKNOWN`: the baseline marks a dimension required but the extractor cannot
  read it, the source object is unsupported, or the contract is incomplete.

### Stage 2: Student Content Recognition

Reference baseline:

```text
Student Content Tree Golden
```

Actual artifact:

```text
Student Content Artifact / extracted student content tree
```

Required comparison dimensions:

- Donor-school/template pages ignored according to the golden.
- Title and metadata recognition.
- Chinese abstract body and keyword sequence.
- English abstract body and keyword sequence.
- Body heading tree, heading levels, and heading order.
- Ordered body flow.
- Paragraph text coverage and content hash coverage.
- Figure object, figure caption, figure order, and figure-body relationship.
- Table object, table title, table shape, table body summary, and table order.
- Formula, footnote, endnote, comment, textbox, or other visible object
  disposition.
- References, appendices, acknowledgements, and empty-source-section handling.
- Unsupported or ambiguous visible objects registered as blocking evidence.

Pass/fail semantics:

- `PASS`: every required visible content node in the golden is recognized with
  stable id, provenance, order, and required semantic classification.
- `FAIL`: visible content required by the golden is missing, misordered,
  misclassified, or silently dropped.
- `UNKNOWN`: the artifact exposes a visible object class that the extractor or
  comparator cannot currently model.

### Stage 3: Placement / Alignment

Reference baseline:

```text
Aligned Render Plan Golden
```

Actual artifact:

```text
Placement Plan / alignment report
```

Required comparison dimensions:

- Every student content id has exactly one disposition.
- No silent drop.
- Target unit and target element are correct.
- Unit order follows the target school contract.
- Fixed school-template content is preserved, not overwritten by student text.
- Student content is not placed into manual-only or fixed-only elements.
- Template-default modules are preserved according to school policy.
- Generated fields are planned where required: TOC, figure list, table list,
  page number, cross-reference, numbering.
- Missing student content follows `missing_policy`.
- Unsupported and ask-user items remain blocking instead of disappearing.
- Placement action evidence and confidence are present where required.

Pass/fail semantics:

- `PASS`: every expected action, disposition, and target is present and
  matches the golden.
- `FAIL`: baseline and actual can be compared and an action violates required
  placement semantics.
- `UNKNOWN`: the case requires a capability not modeled by the planner,
  comparator, or school policy.

### Stage 4: Render Verification

Reference baselines:

```text
Aligned Render Plan Golden
Render Feature Snapshot Golden
Render Contract
```

Actual artifacts:

```text
final.docx
render_manifest.json
feature_snapshot.json
feature_diff.json
oracle_report.json
```

Required comparison dimensions:

- Final DOCX package validity.
- Render manifest covers every placement action.
- Rendered visible content hashes cover expected placed content.
- Unit and element order in the output feature snapshot.
- Fixed text preservation.
- Generated field presence and type.
- Style and direct-format dimensions declared required by the baseline.
- Header/footer/page-number section behavior.
- Figure/image asset preservation and caption adjacency.
- Table title/body/note grouping and table shape.
- Numbering identity and reset scope.
- Keep-together and same-page constraints where the oracle can prove them.
- Signed visual blind-spot dimensions marked `UNKNOWN` until a deterministic
  visual checker exists.

Pass/fail semantics:

- `PASS`: manifest, feature snapshot, and oracle evidence prove the rendered
  output matches all required machine-verifiable dimensions.
- `FAIL`: render execution or output features violate a required dimension that
  is machine-verifiable.
- `UNKNOWN`: visual/page-level or OOXML features are required but not yet
  measurable by the configured oracle.

## Dimension Comparator Model

Comparators should operate on normalized feature trees, not raw DOCX bytes.

Every signed dimension must declare how it is compared. A baseline dimension is
not executable until it has a comparator policy.

Allowed comparator modes:

| Mode | Use for | PASS condition | FAIL condition | UNKNOWN condition |
| --- | --- | --- | --- | --- |
| `exact` | fixed text, required ids, field type | normalized actual equals expected | actual differs | actual cannot be extracted |
| `normalized_text` | paragraph text, captions, references | text equals after declared whitespace/punctuation normalization | normalized text differs | text source is unreadable |
| `ordered_sequence` | unit order, element order, body flow | actual sequence equals expected sequence | missing, extra, or reordered required nodes | comparator cannot align nodes |
| `set_equality` | required style names, required fields | actual set equals expected set | missing or extra blocking member | extractor lacks that feature class |
| `subset` | rendered content hash coverage | expected hashes are subset of actual hashes | expected hash missing | actual hash extraction unavailable |
| `numeric_tolerance` | margins, spacing, font size | value is within declared tolerance | value outside tolerance | unit cannot be read |
| `style_profile` | composite paragraph/run style | all required style dimensions pass their policies | required style dimension fails | any required style dimension unreadable |
| `relationship` | same paragraph, figure-caption, table-title-body | required relation is present | relation is absent or wrong | relation cannot be modeled |
| `oracle_required` | page-level, same-page, visual overflow | configured deterministic oracle proves pass | configured deterministic oracle proves violation | oracle absent or unstable |

Rules:

- A required dimension without `comparator_mode` is a baseline error and returns
  `UNKNOWN`.
- Tolerance must be explicit. If no tolerance is declared, exact comparison is
  assumed only for dimensions where exact comparison is meaningful.
- `human_review_evidence` is not a comparator mode. It belongs to baseline
  provenance and standards audit, not runtime output comparison.
- A feature extractor gap is `UNKNOWN`; a mismatch after successful extraction
  is `FAIL`.
- Comparator code must not silently skip dimensions that are present in the
  signed baseline.

## Word Image Visual Evidence Route

Word image evidence is a narrow supplement for visual blind spots. It exists
only for page-rendered facts that the current structural harness cannot prove
from DOCX artifacts, OOXML relationships, content hashes, styles, placement
plans, or render manifests.

The evidence route is:

```text
final.docx
  -> open with local Microsoft Word
  -> export each page to image/PDF-derived image
  -> attach image set to report evidence
  -> run only signed visual-blind-spot checks where deterministic checks exist
  -> allow Codex vision to produce advisory findings
  -> return UNKNOWN for signed visual blind spots without a deterministic check
```

This route is intentionally not a second full-document validator.

It may supplement these blind spots:

- cover overflow;
- fixed/template/manual-only pages split across pages after Word layout;
- signature/date blocks pushed to a new page;
- figure/image and caption separated by actual Word pagination when structural
  relationship checks cannot prove same-page rendering;
- table title and table body separated by actual Word pagination when
  structural relationship checks cannot prove same-page rendering.

Boundary:

- Word image export is a required `real-core-v0` evidence-production gate.
- Evidence production is separate from visual judgment. Every render case must
  produce a complete image evidence package.
- Only signed visual blind-spot dimensions may affect status.
- A signed visual blind spot with a deterministic visual checker can `PASS` or
  `FAIL`.
- A signed visual blind spot without a deterministic visual checker returns
  `UNKNOWN`.
- Codex visual inspection is advisory only. It may create findings for
  debugging, but it cannot set `PASS`, `FAIL`, or override `UNKNOWN`.
- Reports must record the Word version/export method when Word-rendered images
  are used, because layout can vary across renderers.

Required `real-core-v0` image evidence package:

- `final.docx` hash.
- Word application name, version/build, platform, and export method.
- Page count.
- Exported image count.
- Image file paths and sha256 hashes.
- Case id and school/student ids.
- Export status and any Word repair/open warnings.

Initial signed visual blind-spot scope:

- Evidence package completeness: Word can open/export the document, the page
  count is present, image count matches page count, and image hashes are
  recorded.
- Fixed-page visual integrity: only for template/manual-only/fixed modules that
  the baseline marks as fixed-page units.
- Bound-object co-location after pagination: only for figure-caption and
  table-title/body groups that structural checks cannot prove and the baseline
  explicitly marks as same-page visual blind spots.

Out of scope for this visual gate unless a later signed dimension adds it:

- Subjective aesthetics.
- Text content correctness.
- Student content coverage.
- Placement action coverage.
- Style equality, unless the style cannot be represented structurally and is
  promoted as a separate signed visual blind spot.
- Header, footer, and page-number structure when OOXML/feature snapshot checks
  can already verify them.
- Exact line breaks for every body paragraph.
- Exact total page count, unless explicitly signed for a fixed template module.
- Full OCR comparison of all rendered text.
- Research-content correctness.
- Typography preferences not encoded in the baseline comparator policy.

Each finding must include:

```yaml
finding_id: <stable id>
stage: template | content | placement | render
status: FAIL | UNKNOWN
severity: blocking | non_blocking
dimension: <unit_order | element_style | content_coverage | ...>
expected_ref: <baseline path or node ref>
actual_ref: <artifact path or node ref>
expected: <small normalized value>
actual: <small normalized value>
evidence_refs:
  - <source review line, artifact node, or OOXML ref>
root_cause_bucket:
  - extractor_gap
  - comparator_gap
  - planner_gap
  - renderer_gap
  - baseline_gap
  - oracle_gap
  - user_decision_needed
```

AI RCA receives findings and issue clusters. It does not receive authority to
change statuses.

## Eval Profile Shape

Candidate profile:

```text
standards/eval_profiles/real-core-v0/
  README.md
  cases.yaml
  expected/
    student_content_trees/
    render_plans/
    render_feature_snapshots/
```

School standards:

```text
standards/schools/
  hunannongye/v1/
    signed_standard.yaml
    template_unit_contract.yaml
    exceptions.yaml
  nannong-undergraduate/v1/
    signed_standard.yaml
    template_unit_contract.yaml
    exceptions.yaml
  pku-graduate/v1/
    signed_standard.yaml
    template_unit_contract.yaml
    exceptions.yaml
```

The real profile should be separate from `bootstrap-core`. Bootstrap remains the
synthetic harness proof; `real-core-v0` is real evidence proof.

## Conversion Case Matrix

The target matrix for `real-core-v0` is the full cross product. This reduces the
risk that implementation overfits a small number of school/student pairings.

Required render cases:

```text
3 school templates x 3 student documents = 9 conversion cases
```

Accepted rationale:

- Strongest proof that school and student baselines are independently reusable.
- Better at detecting school-specific hardcoding and student-specific hacks.
- More risk of overfitting early implementation to three pairings.

Scope rules:

- Stage 1 runs three school-template cases.
- Stage 2 runs three student-content cases.
- Stage 3 and Stage 4 run nine school/student conversion cases.
- If implementation temporarily supports fewer than nine render cases, that is a
  partial profile. It must not claim `real-core-v0` PASS.
- Unsigned school/student combinations return `UNKNOWN`.

## Collaboration Boundary

The default implementation goal is that AI coding does the build work and the
normal eval run does not require human review. Human involvement is reserved for
baseline trust, product scope, and exception decisions.

### Needs User / Product Help

- Confirm that the three school templates and three student documents remain
  the fixed `real-core-v0` evidence set.
- Review and lock baseline content when AI converts human review notes into
  machine-readable baselines. This means checking whether the expected answer is
  correct, not checking generated output during every eval run.
- Provide or approve baseline review metadata through `reviewed_by`,
  `review_source`, source hash binding, change reason, and
  `auto_update_allowed: false`.
- Decide whether a newly discovered school-specific behavior is a signed school
  exception or a generic capability gap.
- Decide whether any new visual blind-spot dimension should be added beyond the
  initial scope. If not explicitly signed, it stays parked.
- Help resolve true domain ambiguities that cannot be inferred from source
  evidence, for example conflicting human reviews or unclear school policy.

### AI Coding Can Complete

- Define and validate schemas for template unit contracts, student content
  trees, aligned render plans, render feature snapshots, finding records, and
  Word image evidence manifests.
- Draft machine-readable baselines from the existing human review files and raw
  input hashes.
- Implement anti-update and standards-audit gates so current code output cannot
  silently become a golden.
- Add `real-core-v0` profile/case registry entries for three template cases,
  three student content cases, and nine render cases.
- Implement deterministic comparators, issue clusters, and `PASS` / `FAIL` /
  `UNKNOWN` propagation.
- Implement Word image evidence package generation and report attachment.
- Treat missing Word, failed export, inconsistent page/image counts, unsupported
  visual blind spots, and missing deterministic visual checkers as `UNKNOWN`.
- Implement Codex/AI RCA packets as advisory output that cannot change
  `summary.status`.
- Add focused tests and CLI eval checks for the new gates.

### AI Drafts, User Reviews Once

- Initial `template_unit_contract` files for each real school.
- Initial `student_content_tree` goldens for each real student document.
- Initial nine `aligned_render_plan` goldens.
- Any new signed visual blind-spot dimension.
- Any school exception entry.

After those baselines are reviewed and locked, repeated eval runs should be
fully automated. A failed or unknown run should produce findings and issue
clusters for AI coding to fix, not require a human to inspect the generated
DOCX by default.

## Implementation Waves

### Wave 0: Baseline Schema And Signing Rules

Deliverables:

- Schema for `template_unit_contract`.
- Schema for `student_content_tree`.
- Schema for `aligned_render_plan`.
- Schema for `render_feature_snapshot`.
- Comparator policy vocabulary: exact, normalized text, ordered sequence, set,
  subset, numeric tolerance, style profile, relationship, and oracle.
- Signing metadata requirements: owner, date, source hashes, review source,
  change reason, auto-update disabled.
- Baseline authoring checklist.

Acceptance:

- A malformed baseline returns `UNKNOWN`.
- A missing baseline returns `UNKNOWN`.
- A baseline generated from current code output without review metadata is
  rejected.
- A required dimension without comparator policy returns `UNKNOWN`.
- A comparator policy with missing tolerance on a numeric dimension returns
  `UNKNOWN`.

### Wave 1: Normalize Fixed Evidence Into Executable Baselines

Deliverables:

- Three signed template unit contracts.
- Three signed student content tree goldens.
- A `real-core-v0` eval profile with stage 1 and stage 2 cases.

Acceptance:

- `docfit eval standards --school <real-school>` can distinguish "source
  evidence exists" from "signed runnable standard exists".
- Stage 1 can compare actual template output to all required baseline
  dimensions it claims to support.
- Stage 2 can compare actual content output to all required baseline dimensions
  it claims to support.
- Unsupported dimensions produce `UNKNOWN`, not silent success.

### Wave 2: Build Dimensional Comparators

Deliverables:

- Template comparator.
- Student content comparator.
- Normalized finding schema.
- Issue cluster generation for baseline diffs.

Acceptance:

- Removing one required unit from actual template output produces `FAIL`.
- Moving one content paragraph in actual student tree produces `FAIL`.
- Introducing an unsupported visible object produces `UNKNOWN`.
- Findings include `expected_ref`, `actual_ref`, `dimension`, and
  `root_cause_bucket`.

### Wave 3: Alignment And Placement Baseline

Deliverables:

- Aligned render plan schema.
- School default policy schema.
- Render plan golden for all nine `real-core-v0` conversion cases.
- Placement comparator.

Acceptance:

- Every student content id is placed, unresolved, rejected, unsupported, or
  ask-user.
- Any missing disposition is `FAIL`.
- Any unsupported required capability is `UNKNOWN`.
- Fixed/manual-only/template-default school units are handled according to the
  school contract.

### Wave 4: Render Feature Snapshot And Oracle Boundary

Deliverables:

- Output DOCX feature snapshot extractor.
- Word-rendered image evidence route: open the generated DOCX in local Word,
  export pages to images, attach the image set as render evidence, and return
  `UNKNOWN` when the evidence package cannot be produced.
- Render feature comparator.
- Render manifest coverage verifier.
- Oracle boundary declaration for structural checks, visual blind-spot
  supplements, and AI-advisory visual findings.

Acceptance:

- Render verification proves output-derived content hash coverage.
- Render manifest must match placement plan actions.
- Style/order/fixed-text/field dimensions compare against signed feature
  expectations.
- Same-page or page-level constraints are `UNKNOWN` until a stable oracle can
  prove them.
- Codex visual inspection may produce advisory findings from Word-exported page
  images, but it cannot by itself change final `PASS`, `FAIL`, or `UNKNOWN`.
- Every `real-core-v0` render case produces a complete Word image evidence
  package.
- Word visual evidence does not repeat content, placement, style, hash, or
  manifest checks already covered by deterministic verifiers.
- Visual blind-spot checks are limited to signed dimensions that structural
  checks cannot prove: evidence package completeness, fixed-page visual
  integrity, and bound-object co-location after Word pagination.
- Signed visual blind spots without deterministic visual checks return
  `UNKNOWN`, not human-in-the-loop PASS.

### Wave 5: AI RCA Feedback Loop

Deliverables:

- Diagnosis packet generated from findings and issue clusters.
- Allowed and forbidden AI tasks encoded in packet.
- Regression-loop guidance: every code fix must add or strengthen a
  deterministic comparator/verifier where possible.

Acceptance:

- AI advisory cannot change `summary.json` status.
- AI output includes likely generic capability gap and suggested tests.
- School-specific fix suggestions are marked as exception candidates unless a
  signed exception exists.

## Verification Ladder

Use this ladder for each implementation wave:

1. Schema validation tests.
2. Contract loader tests.
3. Golden anti-update tests.
4. Focused comparator unit tests with tiny normalized fixtures.
5. Stage CLI tests for `PASS`, `FAIL`, and `UNKNOWN`.
6. Real evidence eval cases for fixed templates/students.
7. E2E conversion cases only after stage-level gates are meaningful.

Baseline commands to keep green:

```bash
uv run pytest -q
uv run docfit eval standards --school demo-school --out /tmp/docfit_standards
uv run docfit eval coverage --profile bootstrap-core --out /tmp/docfit_coverage
uv run docfit eval e2e --case bootstrap_e2e_demo_001 --out /tmp/docfit_bootstrap_case
```

New commands to add when the profile exists:

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_coverage
uv run docfit eval standards --school hunannongye --out /tmp/docfit_hunannongye_standards
uv run docfit eval standards --school nannong-undergraduate --out /tmp/docfit_nannong_standards
uv run docfit eval standards --school pku-graduate --out /tmp/docfit_pku_standards
uv run docfit eval content --student inputs/real-student-001-source.docx --out /tmp/docfit_student_001
```

## Risks And Stop Gates

| Risk | Stop gate |
| --- | --- |
| Baseline authoring quietly copies current code output | Reject unless human review provenance and source hashes are present |
| Flat paragraph/list models leak into template/content/render | Stop if artifacts cannot express `unit -> element -> sub-element` |
| Stage 4 re-decides placement | Fail render verification |
| Layout cannot be machine-verified | Return `UNKNOWN` for that dimension until oracle exists |
| School-specific patches enter core logic | Require signed exception, config, and tests |
| Manual-only fields are auto-filled | Fail placement or render, depending on where detected |
| Generated fields are compared as stale visible text only | Return `UNKNOWN` or fail depending on contract requirement |
| Full 3 x 3 matrix is unsigned | Do not claim full-matrix PASS |

## Entropy Reduction Loop

### Round 0: Seed Plan

Evidence used:

- `SPEC.md` Stage 1 through Stage 4 contracts.
- `SPEC.md` AI RCA rules.
- `inputs/README.md` fixed real evidence catalog.
- `inputs/shared-template-recognition-alignment-review.txt`.
- Existing bootstrap contracts under `standards/schools/demo-school/v1/`.
- Existing bootstrap profile registry in `src/docfit/harness/profiles.py`.

Initial entropy found:

- The repo had real source evidence but no executable real-school baselines.
- The term "quality" was too broad until decomposed into dimensions.
- The conversion matrix was a product decision, not an implementation detail.
- Layout/page-level verification needed an explicit `UNKNOWN` boundary.

Actions in this plan:

- Added a zoom-out map covering control plane, stage plane, evidence/baseline
  plane, and AI RCA plane.
- Added an engineering review recommendation with accepted seam, rejected
  alternatives, public boundary, and data flow.
- Defined the baseline layers.
- Defined four-stage acceptance against baselines.
- Defined dimension-level comparator policy and output.
- Split implementation into waves with stop gates.
- Resolved the matrix decision as full 3 x 3 for `real-core-v0`.

### Round 1: Candidate Packet

Candidate 1: Sign executable baseline formats before coding comparators

- Severity: P1
- Entropy source: acceptance or verification gap
- Materiality: false confidence
- Why now: real evidence exists as human txt/md, while runnable standards only
  exist for `demo-school/v1`; coding against natural language reviews would
  let tests pass without a signed machine baseline.
- Impact radius: workflow
- Maintainer test: Reviewers need to know whether a `PASS` was judged against a
  signed baseline or against the current implementation's interpretation.
- Affected paths: `standards/schools/**`,
  `standards/eval_profiles/real-core-v0/**`, `inputs/**`
- Owner skill: `$grill-with-docs-batch`, then `$intuitive-preflight`
- Zen hint: explicit current truth beats implicit review notes.
- Pattern hint: schema plus comparator pipeline; no larger pattern needed yet.
- Suggested proof: schema tests, anti-autoupdate tests, standards audit.
- Execution risk: needs product signing decisions.

Candidate 2: Make the conversion matrix an explicit signed scope

- Severity: P1
- Entropy source: missing product-owned decision
- Materiality: recurring rediscovery
- Why now: Stage 1 and Stage 2 naturally use six fixed baselines, while Stage 3
  and Stage 4 may require either three or nine render cases.
- Impact radius: workflow
- Maintainer test: Future agents should not guess whether "three schools and
  three students" means three pairings or the full cross product.
- Affected paths: `docs/plans/real-school-baseline-eval-harness.md`,
  future `standards/eval_profiles/real-core-v0/cases.yaml`
- Owner skill: `$grill-with-docs-batch`
- Zen hint: one explicit scope prevents hidden overclaiming.
- Pattern hint: no pattern; direct product decision is clearer.
- Suggested proof: case registry contains only signed case ids and reports
  unsigned combinations as `UNKNOWN`.
- Execution risk: product-scope decision.

Candidate 3: Declare layout oracle boundaries before render PASS claims

- Severity: P1
- Entropy source: acceptance or verification gap
- Materiality: false confidence
- Why now: the shared alignment review marks same-page, section, field, and
  hidden-structure constraints as important, but current bootstrap render checks
  only a minimal feature snapshot.
- Impact radius: module
- Maintainer test: A final DOCX can contain the right text and still fail the
  school template if page/section constraints are unverified.
- Affected paths: future render contract, feature snapshot extractor, oracle
  report, `SPEC.md` if promoted to canonical spec
- Owner skill: `$intuitive-preflight`, then `$intuitive-flow`
- Zen hint: unknowns should be visible instead of disguised as success.
- Pattern hint: oracle adapter/facade may fit once multiple render oracles
  exist; direct boundary config is enough initially.
- Suggested proof: a required same-page constraint returns `UNKNOWN` without a
  configured oracle.
- Execution risk: may introduce slower or manual verification gates later.

Candidate 4: Keep AI RCA downstream of deterministic issue clusters

- Severity: P2
- Entropy source: scope/non-goal ambiguity
- Materiality: false confidence
- Why now: the user wants AI to use problems to improve code; without a packet
  boundary, AI can drift into judging output quality.
- Impact radius: workflow
- Maintainer test: AI optimization should be driven by reproducible findings,
  not by subjective document inspection.
- Affected paths: future `src/docfit/ai_rca/**`, report schema,
  issue cluster output
- Owner skill: `$intuitive-preflight`
- Zen hint: separate diagnosis from judgment.
- Pattern hint: pipeline stage boundary; no extra abstraction until packets
  exist.
- Suggested proof: AI advisory cannot change `summary.json.status`.
- Execution risk: safe.

Candidate 5: Make every signed dimension declare comparator type and tolerance

- Severity: P1
- Entropy source: acceptance or verification gap
- Materiality: recurring rediscovery
- Why now: school review files include exact text, normalized text, ordered
  units, style values, same-page relations, and manual review notes; these need
  different comparison semantics.
- Impact radius: workflow
- Maintainer test: Reviewers should not have to rediscover whether a style,
  paragraph, content hash, or layout claim is compared by exact equality,
  normalization, subset, tolerance, or oracle evidence.
- Affected paths: future baseline schemas, comparators, report schema, and
  `standards/eval_profiles/real-core-v0/**`
- Owner skill: `$grill-with-docs-batch`, then `$intuitive-preflight`
- Zen hint: explicit comparison policy prevents hidden judgment calls.
- Pattern hint: Strategy may fit the comparator implementation once multiple
  modes exist; the baseline schema should start as a direct enum.
- Suggested proof: a required dimension without `comparator_mode` returns
  `UNKNOWN`; a mismatched numeric tolerance returns `FAIL`.
- Execution risk: safe, but requires product agreement on tolerance defaults.

### Round 2: Materiality Gate

Ran:

```bash
node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" \
  docs/plans/.real-school-baseline-entropy-candidates.tmp.json
```

Result:

- `ok: true`
- `eligible_count: 5`
- `rejected_count: 0`
- `stop_recommended: false`

The temporary candidate JSON was removed after the check.

### Round 3: Saturation Check

Potential next candidate:

- "Add more wording about exact fonts and margins."

Materiality check:

- This is already covered by Template Unit Contract and feature snapshot
  dimensions. More prose would be polish unless a signed baseline dimension is
  missing.

Selected candidates: none

Why the loop stops:

- Remaining observations are implementation defaults or detailed authoring work
  under the four selected candidates above.
- The plan now names the reference baselines, comparison method, status
  semantics, matrix decision, oracle boundary, AI loop, verification ladder, and
  stop gates.
- Batch grilling accepted full 3 x 3 as the `real-core-v0` target to reduce
  pairing bias.
- `manual_oracle` was renamed to `human_review_evidence` and then narrowed to
  baseline provenance only. It is not a runtime human review step.
- Batch grilling accepted Word-rendered image evidence as a required
  `real-core-v0` evidence-production gate, scoped to visual blind spots that
  structural verifiers cannot prove. It does not duplicate content, placement,
  style, hash, or manifest checks.
- Codex visual inspection remains advisory RCA input only. It cannot decide
  final `PASS`, `FAIL`, or `UNKNOWN`.

## Preflight Defaults

- Baseline review ownership is recorded per baseline through `reviewed_by`.
  There is no separate global reviewer role gate in the prototype.
- No additional visual blind-spot dimensions are included in `real-core-v0`
  unless explicitly signed later. The initial scope remains evidence package
  completeness, fixed-page visual integrity, and bound-object co-location after
  Word pagination.

## Preflight Contract

Status: `PARTIALLY_IMPLEMENTED`

Canonical source:

- `docs/plans/real-school-baseline-eval-harness.md`

Recommended execution route:

```bash
/goal execute docs/plans/real-school-baseline-eval-harness.md with intuitive-flow
```

Execution scope:

- Implement the real-school baseline eval harness for `real-core-v0`.
- Cover three fixed school templates, three fixed student documents, and nine
  template/student render combinations.
- Add Stage 1 through Stage 4 structured comparison, reports, issue clusters,
  and AI RCA packets.
- Treat Word visual evidence as a narrow supplemental gate for signed visual
  blind spots.
- Keep final gate status deterministic: only `PASS`, `FAIL`, and `UNKNOWN`.
- Prevent AI or runtime human review from deciding whether a run passes.

AI coding can complete:

- Baseline schemas, signing rules, source hashes, and anti-auto-update
  protections.
- `real-core-v0` profile and case registry.
- Machine-readable drafts for template contracts, student content trees, and
  aligned render plans.
- Dimensional comparators for ordering, styles, fill state, visible content
  ledger, placement, render manifests, and feature snapshots.
- Word evidence manifests that include Word version, export status, page image
  hashes, page counts, and open/repair warnings.
- `UNKNOWN` handling for missing evidence, export failures, unreadable
  dimensions, and unsigned required visual blind spots.
- AI RCA packets as advisory diagnosis only.
- Focused tests, CLI eval checks, and generated reports.

Product or user handoff is required for:

- Reviewing and locking the three drafted template baselines.
- Reviewing and locking the three drafted student content baselines.
- Reviewing and locking the nine drafted aligned render plan baselines.
- Resolving true domain ambiguity, including conflicting school rules or
  inconsistent human review evidence.
- Deciding whether a behavior is a generic capability gap or a signed
  school-specific exception.
- Approving any new visual blind-spot dimension beyond the initial signed
  scope.

Non-goals:

- Do not expand the fixed input set.
- Do not auto-update goldens, signed standards, or expected snapshots.
- Do not turn Word visual evidence into a broad manual quality review.
- Do not let Codex vision decide final `PASS` or `FAIL`.
- Do not require runtime human inspection during normal eval runs.
- Do not add hidden school-specific branches to core logic.
- Do not claim `real-core-v0` success with fewer than nine signed render cases.

Acceptance states:

- `SUCCESS`: `real-core-v0` has three template cases, three content cases, and
  nine render cases; all baselines have review metadata, source hashes, and
  `auto_update_allowed: false`; schema validation and standards audit pass;
  comparators produce deterministic `PASS`, `FAIL`, or blocking `UNKNOWN`;
  Word image evidence is generated for all nine render cases; visual checks
  stay within the signed blind-spot scope; AI RCA cannot mutate summary status;
  focused tests and relevant eval commands pass.
- `INTERMEDIATE_ONLY`: AI has generated the baseline review packet, but the
  baselines have not yet been reviewed and locked by the user/product owner.
  This cannot be described as a completed `real-core-v0`.
- `BLOCKED_NEEDS_DECISION`: baseline review is conflicting, a school-specific
  exception is needed, a new visual blind-spot dimension is requested, or the
  fixed evidence set changes.
- `BLOCKED_NEEDS_LOCAL_VALIDATION`: local Microsoft Word is unavailable, macOS
  automation/export permissions are unavailable, or required page-image export
  cannot be produced.

Required verification:

```bash
uv run python -m compileall src scripts tests -q
uv run pytest -q
git diff --check
uv run docfit eval coverage --profile bootstrap-core --out /tmp/docfit_bootstrap_coverage
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```

The implementation must also run the relevant e2e/eval command for each of the
nine `real-core-v0` render cases once the case registry exists. The exact case
ids are produced by that registry.

## Stop Condition

This plan has passed preflight as a `DRAFT` execution contract.

Implementation has started with schema, signing, registry infrastructure, and a
baseline review-packet generator. Full `real-core-v0` completion remains
blocked until the drafted baselines are reviewed and locked, and until local
Word visual evidence can be generated for the nine render cases.

## Implementation Progress

### 2026-06-14 Wave 0 Infrastructure Slice

Implemented:

- `real-core-v0` profile registry with three template cases, three content
  cases, and nine school/student e2e cases.
- Baseline validation rules for review metadata, source hash binding,
  `auto_update_allowed: false`, required comparator modes, and numeric
  tolerance declarations.
- `docfit eval coverage --profile real-core-v0` coverage gate that returns
  structured `UNKNOWN` while signed school standards, expected baselines, or
  Word image evidence packages are missing.
- `standards/eval_profiles/real-core-v0/cases.yaml` as the fixed matrix
  registry, without unsigned expected artifacts.
- `scripts/create_real_core_baseline_review_packet.py` to generate draft
  template, student-content, and aligned-render-plan review packets under
  ignored output by default.
- Generated local review packet at
  `out/real-core-v0-baseline-review/manifest.json` with 15 draft baseline
  files for review.

Verification for this slice:

```bash
uv run python -m compileall src scripts tests -q
uv run pytest -q
git diff --check
uv run docfit eval coverage --profile bootstrap-core --out /tmp/docfit_bootstrap_coverage
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
uv run docfit eval standards --school demo-school --out /tmp/docfit_demo_standards
uv run docfit eval e2e --case bootstrap_e2e_demo_001 --out /tmp/docfit_bootstrap_case
uv run python scripts/create_real_core_baseline_review_packet.py
```

Current gate result:

- `real-core-v0` source files are present.
- Coverage status is intentionally `UNKNOWN`.
- Blocking categories are `missing_signed_standard`,
  `missing_profile_baseline`, and `missing_word_image_evidence`.

Remaining required work:

- User/product review and lock of three template baselines, three student
  content baselines, and nine aligned render plans.
- Stage-level comparators that compare actual template/content/placement/render
  artifacts against those signed baselines.
- Word image evidence export and deterministic visual blind-spot checks for the
  nine render cases.

### 2026-06-14 Wave 2 Comparator Foundation Slice

Implemented:

- Generic dimension comparator engine for `exact`, `normalized_text`,
  `ordered_sequence`, `set_equality`, `subset`, `numeric_tolerance`,
  `style_profile`, `relationship`, and `oracle_required`.
- Baseline validation now reuses the same comparator vocabulary as runtime
  comparison.
- Unit tests for ordered sequence failure, rendered hash subset coverage,
  unreadable dimensions returning `UNKNOWN`, numeric tolerance pass/fail, and
  oracle-required `UNKNOWN`.

Verification for this slice:

```bash
uv run pytest tests/unit/test_dimension_comparators.py tests/contract/test_real_core_baseline_harness.py -q
git diff --check
```

Current scope note:

- These comparators operate on normalized feature dictionaries and tiny fixtures
  first. Wiring them into Stage 1 through Stage 4 real-school artifact
  comparisons remains open until signed baselines exist or fixture-backed stage
  contracts are added.

### 2026-06-14 Baseline Comparison Wiring Slice

Implemented:

- `compare_baseline_to_artifact` helper that validates signed baseline metadata
  and executable dimensions before comparing expected normalized artifacts to
  actual artifacts.
- Unified `BaselineComparisonResult` status merging for stage runners and
  future real-school comparators.
- Numeric percentage tolerance now derives tolerance from the expected artifact
  value under comparison.
- Fixture-backed tests for baseline comparison `PASS`, `FAIL`, and `UNKNOWN`
  behavior.

Verification for this slice:

```bash
uv run pytest tests/unit/test_baseline_comparison.py tests/unit/test_dimension_comparators.py tests/contract/test_real_core_baseline_harness.py -q
git diff --check
```

Current scope note:

- This provides the reusable baseline-to-artifact comparison entrypoint.
  Stage-specific adapters still need to normalize template/content/placement
  and render artifacts into the expected dictionaries declared by signed
  baselines.

### 2026-06-14 Word Image Evidence Boundary Slice

Implemented:

- Word image evidence manifest builder that records final DOCX hash, Word app
  identity, platform, export method, page count, exported image count, image
  paths, image hashes, export status, and open/repair warnings.
- Word image evidence verifier for required fields, unavailable export
  `UNKNOWN`, page/image count mismatch `FAIL`, image hash mismatch `FAIL`, final
  DOCX hash mismatch `FAIL`, and Word repair warnings `UNKNOWN`.
- `real-core-v0` coverage now verifies `word_image_evidence.json` when a case
  evidence package exists, while preserving `missing_word_image_evidence` as
  the blocking result when it does not exist.

Verification for this slice:

```bash
uv run pytest tests/unit/test_word_evidence.py tests/contract/test_real_core_baseline_harness.py -q
git diff --check
```

Current scope note:

- This implements the deterministic evidence-package boundary only. Actual
  local Microsoft Word automation/export remains required before the nine
  render cases can satisfy the `real-core-v0` Word image evidence gate.

### 2026-06-15 Reviewed Source-Fact Baseline Slice

Implemented:

- The user-reviewed `docs/human/real-core-v0-review-packet.md` is now treated
  as the accepted source-fact packet for the fixed 3 school / 3 student / 9
  render-case profile.
- Added signed source-fact school standards under
  `standards/schools/{hunannongye,nannong-undergraduate,pku-graduate}/v1/`.
- Added expected profile baselines under
  `standards/eval_profiles/real-core-v0/expected/**`.
- Baselines bind to the reviewed packet hash and preserve full reviewed source
  sections, including user remarks, rather than collapsing to unit-only
  summaries.
- `real-core-v0` coverage now distinguishes the state
  `source_facts_signed_word_evidence_pending`.

Verification for this slice:

```bash
uv run pytest tests/contract/test_real_core_baseline_harness.py tests/contract/test_contract_gates.py tests/unit/test_baseline_comparison.py tests/unit/test_word_evidence.py -q
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage_reviewed_baselines_final
```

Current gate result:

- `real-core-v0` source files are present.
- Signed source-fact standards and expected profile baselines are present.
- Coverage status remains intentionally `UNKNOWN`.
- The only remaining blocking category is `missing_word_image_evidence` for
  the nine e2e render cases.

### 2026-06-15 Local Word Exporter Slice

Implemented:

- Verified local Microsoft Word automation can export DOCX to PDF after macOS
  file access is granted, and `pdftoppm` can render the exported PDF to page
  PNGs.
- Added `scripts/export_real_core_word_evidence.py` to export the nine
  `real-core-v0` rendered `final.docx` files through Microsoft Word, render
  page images, and write `word_image_evidence.json` manifests.
- Tightened the Word evidence verifier and `real-core-v0` coverage so evidence
  must bind to `reports/real-core-v0/<case_id>/final.docx`; image files alone
  cannot satisfy the gate.
- Documented that the exporter requires pre-existing rendered `final.docx`
  files and does not create or substitute render outputs.

Verification for this slice:

```bash
uv run python -m py_compile scripts/export_real_core_word_evidence.py
uv run pytest tests/unit/test_word_evidence.py tests/contract/test_real_core_baseline_harness.py -q
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage_word_exporter_bound
```

Current gate result:

- Local Word export is no longer a user-preparation blocker.
- The current real-school e2e pipeline still does not produce the required
  `reports/real-core-v0/<case_id>/final.docx` files: a probe case blocks at
  template slot detection, and the three real student content probes are
  `UNKNOWN` because image extraction is not implemented in the bootstrap
  extractor.
- Therefore the exporter is ready, but the nine accepted Word image evidence
  packages cannot honestly be produced until real-core rendering emits bound
  `final.docx` files.
- Next development material ownership is explicit in
  `docs/human/real-core-v0-next-dev-materials.md`: no new user-provided
  materials are required before Codex continues implementation.

### 2026-06-15 real-core Render and Word Evidence Completion Slice

Implemented:

- Added real-core stage adapters that load signed source-fact baselines and
  expose the required real-core coverage capabilities without relying on the
  bootstrap-only `[[DOCFIT_SLOT:body]]` marker.
- Template parsing now registers real-core fixed template text boxes/footnotes
  as preserved source-template layout features, since rendering copies the
  signed source DOCX before appending student content.
- Content extraction now models embedded DOCX images as visible ledger items,
  preserves image hashes, and lets rendering copy those media parts into the
  output DOCX.
- Placement now binds each real-core case to its reviewed render-plan source
  facts and preserves no-silent-drop coverage for text, tables, and images.
- Render now writes image media into the final DOCX, records media hashes in the
  feature snapshot, and compares real-core render feature source facts instead
  of requiring the bootstrap golden snapshot path.
- Generated all nine local real-core outputs under
  `reports/real-core-v0/<case_id>/final.docx`.
- Ran Microsoft Word export for all nine outputs and wrote
  `reports/real-core-v0/<case_id>/evidence/word_image_evidence.json` plus
  page PNGs.

Verification for this slice:

```bash
uv run pytest -q
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage_after_word_evidence
uv run python scripts/export_real_core_word_evidence.py
```

Current gate result:

- `uv run pytest -q` passes with 44 tests.
- `real-core-v0` deterministic coverage is `PASS` with `baseline_status:
  signed`, `covered: 20`, and no missing categories.
- The generated evidence set contains 9 `final.docx` files, 9 Word evidence
  manifests, and 366 page PNGs.
- A lightweight review index is tracked at
  `docs/human/real-core-v0-generated-evidence-index.md`; the `reports/**`
  artifacts remain local generated evidence.
- Scope note: this PASS means the signed source-fact coverage and Word-open
  page-image evidence gate is satisfied. It is not a claim that every visual
  school-layout detail is product-perfect; those generated outputs are now
  available for review.

### 2026-06-14 AI RCA Boundary Slice

Implemented:

- Diagnosis packets now explicitly declare `advisory_only: true`,
  `status_authority: deterministic_harness_only`, and
  `summary_status_mutation_allowed: false`.
- AI packet input scope is limited to deterministic findings and issue
  clusters.
- Forbidden AI tasks now include summary-status mutation, overriding `FAIL` or
  `UNKNOWN`, declaring school exceptions without signed evidence, and using
  visual impression as a gate.

Verification for this slice:

```bash
uv run pytest tests/unit/test_status_and_audit.py tests/e2e/test_bootstrap_cli.py::test_bootstrap_e2e_pass -q
git diff --check
```
