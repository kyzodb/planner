# Examples

## Demolition spawn

```xml
<demolition_spawn>
  <story>#42</story>
  <allowlist>
    <path>crates/kyzo/src/old_index.rs</path>
  </allowlist>
  <condemned>Old IndexMut panic path</condemned>
</demolition_spawn>
```

## Task spawn

```xml
<task_spawn>
  <story>#42</story>
  <task>T3 — Replace IndexMut impl in crates/kyzo/src/map.rs</task>
  <allowlist>
    <path>crates/kyzo/src/map.rs</path>
  </allowlist>
  <check>cargo check -p kyzo --lib</check>
  <context_refs>crates/kyzo/src/map.rs</context_refs>
</task_spawn>
```

## After judge PASS

```
git add -- crates/kyzo/src/map.rs
git commit -m "T3 — Replace IndexMut impl in map.rs"
```

## After judge FAIL

```
git restore --worktree --staged -- crates/kyzo/src/map.rs
```

## Final QA comment then tool

```
FINAL QA
VALUE: …
CONDEMNED: …
CHOICE: …
SOURCES: …
```

→ `check_final_qa` → `move_to_done`
