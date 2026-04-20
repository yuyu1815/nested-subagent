# 動作確認プロンプト

セッション再起動後、これをそのまま送信する。

---

## Test 1: 最小テスト

mcp__nested_subagent__task を prompt="What is 2+2? Reply with just the number." model="haiku" で呼んで。

---

## Test 2: ツール使用テスト

mcp__nested_subagent__task を prompt="Read pyproject.toml in the current directory and list the dependencies." model="haiku" で呼んで。

---

## Test 3: TUI 確認

Test 1, 2 の後に /tmp/nested-subagent-tasks/ の中身を確認して、JSONL に何件イベントが記録されたか教えて。TUI ウィンドウが起動していたかも確認。
