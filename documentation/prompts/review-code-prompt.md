---
name: review-code
description: Review Shifu code together, prepare GitHub comments, and publish each comment only after user approval.
---

# Review Shifu code together

Review the requested PR, branch, commit range, or current worktree. Report two
independent axes: **Standards** (does the change follow Shifu's documented
rules?) and **Contract** (does it satisfy the selected Spec or other stated
request?). Work with the user to test and refine findings before posting review
comments. Do not edit source, tests, SDD artifacts, Jira, or Confluence, and do
not change artifact statuses as part of this review.

## 1. Establish the exact candidate

Inspect `git status --short` first. Preserve unrelated work. Record the branch,
`HEAD`, comparison base, commit list, and changed paths before reviewing.

- For a PR, inspect its actual head and base with authenticated `gh`; review the
  PR diff. Keep unrelated local changes out of the PR verdict.
- For a supplied Git ref, verify it resolves. Review
  `git diff <ref>...HEAD` and `git log <ref>..HEAD --oneline`. If the user also
  requested the current worktree, review `git diff HEAD` and untracked files as
  a separately labeled overlay.
- For a worktree review without a supplied ref, review `git diff HEAD` (tracked
  staged and unstaged changes) and relevant untracked files. State that this
  does not include earlier commits.

Do not assume an empty committed diff means an empty worktree. Do not open `.pen`
files with shell or generic filesystem tools. If the requested comparison is
invalid or empty, say so before giving a verdict. GitHub inline comments need
an actual PR; a local-only review can still be discussed without posting.

## 2. Resolve authority and scope

Read `AGENTS.md`, `documentation/rules.md`, and every Rule Pack selected by the
actual changed paths and behavior. Recheck the selection when a dependency
crosses into another layer. Read `documentation/modules.md` and
`documentation/architecture.md` when ownership, system boundaries, persistence,
authentication, messaging, or integrations are affected. Check current manifests
and source for implemented commands and behavior; documentation may describe
planned capabilities.

For feature behavior, read `documentation/sdd.md`, the exact local `spec.md`,
`plan.md` when present, and `evaluation.md`. Verify the Spec revision, status,
allowed and prohibited paths, `RF-*`/`CA-*`, design references, and required
`VM-*`/`CI-*` evidence. Locate the relevant Jira issue and read the complete
canonical Confluence PRD when a requirement or product-intent claim depends on
it. Check its content ID and version against the Spec. Confluence owns product
intent; the local Spec owns the selected implementation contract. Report a
conflict between them without silently choosing a new contract.

For maintenance without a feature Spec, use the stated request, issue, or bug
report as the Contract source. If none is available, review Standards and report
that Contract fidelity cannot be determined; do not invent requirements.

## 3. Review the two axes independently

**Standards pass:** For each changed boundary, check the selected Rule Pack,
module ownership, dependency direction, test placement and integrity, generated
artifacts, migrations, REST-client parity, and applicable security or runtime
constraints. Cite the exact rule or authority behind each violation. Consider
code smells such as duplication, unclear names, speculative abstractions, and
scattered change as judgment calls only. A documented Shifu rule takes
precedence over a generic smell; do not report formatting or other matters
already reliably enforced by an applicable tool unless that tool's result is
part of the finding.

**Contract pass:** Trace every affected `CA-*` to changed behavior and current
evidence. Find missing or partial requirements, incorrect outcomes, unapproved
scope, changed exclusions, and behavior inconsistent with `RF-*`, `RP-*`, or
`JN-*`. Check relevant error, authorization, persistence, concurrency, event,
loading, empty, recovery, keyboard, responsive, and visual states. Passing unit
tests alone do not prove server-backed or rendered behavior. Treat stale,
missing, mocked-only, or unavailable Evaluation evidence as an evidence gap,
not as proof of a runtime defect. Cite the contract line or ID for each claim.

When the two passes are genuinely independent and this is a standalone review,
run them in parallel with specifically named, read-only reviewers and bounded
sources. The main task verifies their findings against the integrated diff and
authorities. If reviewing within `implement-spec`, follow its single
Implementation Reviewer workflow instead; keep the Standards and Contract
questions separate within that review. Do not activate a Spec Reviewer to
review implementation code.

## 4. Validate findings and review them with the user

Inspect the complete relevant source around each changed hunk and trace its
callers or consumers before claiming a defect. Run focused existing checks only
when they can resolve a concrete uncertainty; record the exact command, result,
and candidate revision. For UI or browser behavior, use Playwright CLI and the
repository's browser workflow. Do not call unrun checks passed or substitute
mocked transport for real application evidence.

Present proposed findings under `## Standards` and `## Contract`. For each one,
include severity, precise file and line, the rule or criterion, observed
evidence, impact, and a concrete correction. Keep style opinions clearly
labeled as suggestions. State coverage gaps, checks run, and any authority or
environment limitation. Keep the axes separate; do not combine them into one
score or rerank findings across axes.

Invite the user to challenge, clarify, dismiss, or revise the proposed findings.
Investigate each disputed point using source, authority, and focused checks.
Update the proposed findings in the conversation and explain changed judgments.
Do not treat a lack of reply as agreement. If a finding depends on an unresolved
product or technical decision, identify that decision instead of writing a
definitive comment. Continue until the user has a concrete set of review
comments to decide on.

## 5. Prepare and approve GitHub comments

For a PR review, verify `gh auth status`, the PR head, and the current diff
before preparing comments. Draft each comment with its exact body, repository
path, side, and current diff line. Prefer a narrowly anchored inline comment;
use a general PR review comment only when an inline anchor is impossible. Keep
the wording factual, actionable, and tied to the evidence discussed with the
user. Do not post low-confidence suggestions as defects.

Show the complete draft of **each** proposed GitHub comment to the user, with
its target and the finding it represents. Ask for an explicit approve, revise,
or skip decision for each comment. A batch response is acceptable only when it
unambiguously identifies every approved comment. Approval of the review task,
or silence after a draft, is not approval to post. If a comment's wording or
target changes, show the new draft and request approval again.

Only after approval, post the approved comments using authenticated `gh` CLI.
Recheck the PR head and anchors immediately before posting; if they moved,
re-anchor and request approval for the changed targets. Never post rejected,
undecided, or superseded drafts. Read back every posted comment and provide its
GitHub link. If no PR exists, leave the reviewed findings in the conversation
and explain that GitHub comments require a PR; do not create one implicitly.

After the comment decisions, give a separate Standards and Contract verdict,
the disposition of every proposed comment, checks run, and remaining evidence
gaps. Do not present an unposted draft as a published comment.

If this review is part of an active SDD delivery, send verified findings to the
Orchestrator for `ACH-*` disposition in `evaluation.md`. The review itself does
not decide official evidence or delivery status.
