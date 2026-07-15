# Examples

## Spawn (good)

```xml
<task_spawn>
  <story>#42</story>
  <task>T3 — Replace IndexMut impl in crates/kyzo/src/map.rs</task>
  <allowlist>
    <path>crates/kyzo/src/map.rs</path>
    <path>crates/kyzo/src/map/</path>
  </allowlist>
  <seal>cargo check --workspace --all-targets</seal>
  <condemned>Old IndexMut panic path in map.rs</condemned>
  <context_refs>crates/kyzo/src/map.rs</context_refs>
</task_spawn>
```

## Monitor lines (good)

```
Edit crates/kyzo/src/map.rs
Bash cargo check --workspace --all-targets
```

## Monitor whip (good)

```
WHIP 1: Read crates/other/src/lib.rs ∉ allowlist
```

## verify FAIL — narrowed seal

Submitted seal `cargo check -p kyzo --lib` ≠ board `cargo check --workspace --all-targets` → FAIL.

## verify FAIL — empty diff

`paths (0)` against story-start tag → FAIL.

## Judge PASS path

1. `verify_task_completion` → PASS  
2. Semantic obligations ok  
3. `check_story_task` → box flipped
