# Gotchas (from real burns)

## Lib-green / narrowed seal

Running `cargo check -p foo --lib` when the task Seal is `cargo check --workspace --all-targets` is fraud. `verify_task_completion` fails. Do not shrink the gate mid-flight.

## Empty allowlist testimony

"Done in allowlist" with `git diff --name-only` empty is not done. Discard the agent.

## Shrink the cut

Dropping call sites to get green, or rewriting the task mid-flight, is a story change — form `STORY OR TASK CHANGES` / kill, never silent scope collapse.

## Stolen-valor narration

Measuring done by explanation, demo leftovers, or "zero errors in allowlist" reports without a tree diff. Trust verify + checkbox only.

## Batch without proof-of-edit

Mega-batches that re-derive `IndexMut` across 100+ files. Slice T#s; compile checkpoint per batch.

## Whole-file insurance reads

Read that feeds no Edit is stall fuel. Whip.

## Fake TREE DIFF on the form

Pasted paths the git edge never saw. Verify runs real git — fake forms die.
