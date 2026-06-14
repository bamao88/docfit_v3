# Bootstrap Core Eval Profile

This profile owns bootstrap harness facts that are not raw user or school
inputs.

- Required capabilities live in `src/docfit/harness/profiles.py`.
- Expected intermediate artifacts live in `expected/`.
- Raw DOCX/DOC inputs and human review evidence live in `inputs/`.
- Signed standards, contracts, goldens, and exceptions live in
  `standards/schools/demo-school/v1/`.

Files under `expected/` are deterministic eval profile evidence. They are not
original student or school inputs.
