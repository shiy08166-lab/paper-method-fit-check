---
name: paper-method-fit-check
description: Decide whether a paper's method transfers to your project: extract its hard preconditions, anchor load-bearing claims to exact source locations, separate what the paper states from what you infer, and return a fit verdict with the gaps still blocking it. Use when asked whether a paper's approach is applicable, reproducible or transferable here.
---

## Workflow

### 1. Pin down the decision the reader actually has to make

- Do not start by summarising the paper. First capture the **decision** the reader faces and the **constraint set** they are judging against:
  - target question / the claim they want to reuse
  - compute envelope (GPU model, VRAM, wall-clock budget, whether training is possible at all)
  - data regime (available sample count, label availability, domain match)
  - what counts as success for them (reproduce the number / adopt the method / only need the mechanism)
- Write these into `cases/<task-id>/task.md` before touching the paper. Every later judgement is scored against this constraint set, so it must exist **before** you read the results.
- **Checkpoint**: `task.md` contains a finite, checkable constraint list — if any constraint is "unknown", record it as an explicit open question rather than guessing.

### 2. Extract the method's hard preconditions from the paper

- Read the full text, not only the abstract. For every quantity the method's results depend on, record:
  - **compute**: accelerator type and count, training time, peak memory if stated
  - **data scale**: dataset, sample/sequence/token counts, splits
  - **hyperparameters**: the ones the result is actually sensitive to (not every one)
  - **hidden assumptions**: what must be true for the method to work (convergence, i.i.d. samples, a particular noise model, a specific regulariser, a specific preprocessing step)
- Write each precondition as one row of `preconditions.csv`: `id, category, value, unit, source_locator, confidence`.
- `source_locator` is **mandatory** — a section number, figure/table number, equation number, page, or appendix heading. A precondition you cannot locate is a precondition you did not read.
- Distinguish explicitly:
  - **stated** — the paper says it (locate it)
  - **inferred** — you derived it from the method (state the derivation)
  - **absent** — the paper never mentions it, yet the result plausibly depends on it (record it; an absent precondition is often the real answer to "can I use this?")
- **Checkpoint**: every row has a non-empty `source_locator` or an explicit `confidence=absent`. A blank locator is a rejected row.

### 3. Build a locatable evidence index over the original text

- Extract the source into a working copy (`materials/source.pdf`, `materials/source.txt`) and split the text into stable, citable units:
  - page/paragraph blocks, figure and table captions, equation labels
- Produce `evidence_index.json`: a list of `{id, kind, locator, quote, sha256}` where `quote` is a **single contiguous** span copied verbatim from the unit.
- Never paraphrase inside `quote`. Never stitch two non-adjacent spans into one quote — a quote that cannot be found by a search for it is worthless as evidence.
- Record the SHA-256 of every file you quote from, so a reviewer can prove the text was not edited.
- **Checkpoint**: for each entry, `sha256` of the quoted file exists and `quote` is byte-identical to a substring of the extracted text (verify programmatically, not by eye).

### 4. Anchor the load-bearing claims to the source

- Identify the claims the method's usefulness rests on — typically: the central quantitative result, the conditions under which it was obtained, any stated limitation, and any comparison the paper leans on.
- For each claim produce one row of `claims.csv`: `claim_id, claim_text, classification, locator, quote, dependency_preconditions, confidence`.
- `classification` is exactly one of:
  - `paper-fact` — stated in the paper, located and quoted
  - `inference` — your reasoning from the paper, with the reasoning written out
  - `undetermined` — cannot be settled from the available material
- A claim may only be `paper-fact` if its `locator` and `quote` are filled. Anything you cannot locate must be demoted to `inference` or `undetermined` — never silently presented as established.
- **Checkpoint**: zero rows with `classification=paper-fact` and an empty `quote`.

### 5. Assess transferability against the reader's constraints

- Join the two tables: for each precondition, compare `value` against the reader's constraint from `cases/<task-id>/task.md`.
- Classify each precondition:
  - `satisfied` — the reader's envelope meets it
  - `stretch` — attainable, but needs a stated change (smaller batch, longer schedule, different precision, subsampled data, a missing dependency to install)
  - `blocked` — not attainable under the reader's constraints
  - `unknown` — the paper does not say, so transfer cannot be judged
- For every `stretch` precondition, write the **concrete change** and its expected effect. "Needs more memory" is not a change; "drop the context length from 2048 to 512 and halve the model width, which costs roughly 3x fewer tokens per step" is.
- For every `blocked` precondition, write the nearest viable alternative **if one exists in the paper's own material**, and label it as an adaptation rather than a reproduction.
- **Checkpoint**: every precondition has a classification and a one-line rationale; no row is left blank.

### 6. Produce the fit verdict

- Write `verdict.md` with four sections, in this order:
  1. **Verdict** — one of `transferable-as-is`, `transferable-with-changes`, `not-transferable`, `undetermined`, plus two sentences of reasoning. Never blur two verdicts into one sentence.
  2. **What is established** — the `paper-fact` claims with their locators.
  3. **What I inferred** — the `inference` rows, with the reasoning, marked as not coming from the paper.
  4. **What remains open** — the `undetermined` claims and the `absent` preconditions, each with the specific thing that would settle it and where to look.
- Close with **next reading steps**: the exact next figure/table/section or next paper to read that would resolve the highest-impact open question. Prefer reading over running when running is blocked.
- **Checkpoint**: the verdict string is one of the four allowed values, and every `undetermined` claim from step 4 appears in section 4.

### 7. Run the numeric agreement check

- Wherever the paper states a number that the method's usefulness depends on, check your extracted value against the paper's:
  ```bash
  python3 scripts/check_agreement.py \
      --claims claims.csv \
      --preconditions preconditions.csv \
      --tolerance 0.01 \
      --report logs/agreement.json
  ```
- The script compares every quoted numeric value against the number it was transcribed from, and flags any row whose relative difference exceeds the tolerance.
- A flagged row is **not** deleted — it is corrected, or its classification is downgraded to `inference`, or the disagreement is written into section 4 of `verdict.md` as a genuine inconsistency in the source.
- **Checkpoint**: `logs/agreement.json` exists, every flag has a recorded disposition, and no row is left unreviewed.

### 8. Package for reuse and record the trace

- Emit, in this order:
  ```
  submission/
    README.md            # environment, how to run, budget, what was human-done
    report.md            # problem, design, results, limitations
    manifest.json        # file/version/case/run index
    review.json          # evidence index (generated, not hand-written)
    skill/SKILL.md       # this file
    materials/           # the source and the extracted units actually used
    cases/               # task + the acceptance criteria written before the run
    runs/                # raw outputs, logs, and the agreement report
  ```
- Keep every failed attempt, retry and manual correction in `runs/`. A run that produced nothing is evidence about the method, not a mistake to hide.
- Export the agent's own session log as the trace: one JSON event per line, steps typed as `thought` / `tool_call` / `tool_result` / `artifact` / `decision` / `error` / `observation`.
- **Checkpoint**: `manifest.json` lists every file that exists under `submission/`, and every claim in `claims.csv` has a matching entry in `review.json`.

## Validation

- **原文锚定率**: every row in `claims.csv` marked `paper-fact` carries a non-empty `locator` and a `quote` that is a byte-identical contiguous substring of the extracted text; the ratio of `paper-fact` rows to total rows is reported in `report.md`. A claim without a locator is never presented as established.
- **事实/推断分离**: every claim is classified as exactly one of `paper-fact` / `inference` / `undetermined`, and every `inference` row carries its reasoning in writing. No row is left unclassified, and no inference is worded as a statement from the paper.
- **前置条件完备性**: `preconditions.csv` covers all four categories (compute, data scale, hyperparameters, hidden assumptions) and each row is either located in the source or explicitly marked `absent` with the reason it plausibly matters. Preconditions the paper never mentions are recorded, not omitted.
- **结论可判定**: `verdict.md` carries exactly one verdict from `{transferable-as-is, transferable-with-changes, not-transferable, undetermined}`, every `stretch` precondition names a concrete change rather than a difficulty, and every `undetermined` claim appears in the "what remains open" section.
- **数值一致**: every quoted numeric value agrees with the transcribed source within 1% relative error; disagreements are either corrected or written into the report as an inconsistency in the source, and `logs/agreement.json` shows no unreviewed flag.
- **自检**: the whole workflow re-runs in a clean directory from `materials/` alone, with no dependency on files outside `submission/`, and produces the same verdict and the same set of located claims.

## Failure modes

- **Source is paywalled or unreachable**: If the PDF cannot be retrieved, then obtain the legally shareable version — an author-hosted preprint, an institutional copy, the accepted manuscript — and record its version and locator. If no shareable version exists, then set the verdict to `undetermined` and list the specific sections that would be needed. Never fabricate a quote from memory or from a summary.
- **The paper's numbers cannot be located**: If a number appears in the text but its origin cannot be pinned to a page, table or equation, then classify the corresponding claim as `inference` and note in `report.md` that the transcription could not be traced. Do not cite a value you cannot point at.
- **Figures are vector graphics and cannot be parsed**: If a value must be read off a figure, then extract the figure's vector paths and digitise the curve programmatically, and record the digitised value in `logs/` with the extraction method. If digitisation is not reliable, then mark the claim `undetermined` and say so — an eyeballed number is a fabricated number.
- **The method depends on an unpublished detail**: If the result plausibly depends on a hyperparameter, preprocessing step or dataset version the paper never gives, then add it to `preconditions.csv` as `absent`. If that absent precondition is the one blocking transfer, then the verdict becomes `not-transferable` or `undetermined` — not a hopeful `transferable-with-changes`.
- **The reader's constraint set is under-specified**: If the constraints cannot be pinned down from the request, then ask for the single most decision-relevant one (usually compute or data volume) and proceed with the rest marked `unknown`. If no constraint can be established at all, then report only the method's preconditions and the open questions, and return no verdict.
- **The evidence index exceeds the size or file-count limit**: If `review.json` or the package grows past the contest limit, then deduplicate by file SHA-256, keep shared material once, and select only the quotes that carry load-bearing claims — citing fewer, locatable quotes is better than many unverifiable ones. Never drop a failed run to make room, and never nest a zip inside a zip.
- **The tool that extracts or checks something fails**: If a script in this skill errors out, then read the error, fix the input rather than the criterion, and re-run. If the check cannot be made to pass, then record the failure in `runs/` with its output, and downgrade the affected claim's classification. Never delete the failing run and never write a passing verdict over a check that did not run.
- **The reader asks for a yes/no answer only**: If they want a single verdict with no working shown, then give the verdict first and the evidence underneath it, but keep the located claims and the open questions in `verdict.md` regardless. A bare verdict is not a transferable method.
