# Claude Code Configuration

## 基本設定

- **言語**: 常に日本語で回答してください

## Think Harderモードの常時適用

Claude Codeを使用する際は、常にThink Harderモードで動作してください。これにより：

- **深い分析**: 問題の根本原因を徹底的に分析
- **多角的検討**: 複数のアプローチや解決策を検討
- **リスク評価**: 変更による影響や副作用を事前に評価
- **最適化**: より効率的で保守性の高いソリューションを追求
- **品質重視**: コードの品質、可読性、パフォーマンスを総合的に考慮

## Context7使用について

**重要**: コードに関する質問や実装をする際は、必ずContext7を使用してください。

- ライブラリやフレームワークに関する質問では、常に "use context7" を含めてください
- 最新のドキュメンテーションと正確なAPIリファレンスを取得するため、Context7の使用は必須です
- 古い情報や存在しないAPIを避けるため、Context7なしでのコード生成は避けてください

例：
"Create a Next.js component with TypeScript. use context7"
"How to implement authentication in FastAPI? use context7"

## Git作業フロー

- **ファイル修正前のブランチ作成**:
  ファイルを修正する際は、必ず作業用ブランチを作成してから作業を開始してください
- **ブランチ命名規則**: 
  `feat/`, `fix/`, `enhance/`などの適切なプレフィックスを使用してください
- **作業の流れ**:
  1. 作業用ブランチを作成
  2. ファイルを修正
  3. フォーマットを確認
  4. テスト実行
  5. 変更をコミット
  6. 必要に応じてプルリクエストを作成

### 作業フロー遵守の確実性向上

Claude Codeが確実にGit作業フローを守るための追加ガイドライン：

- **事前チェック必須**: ファイル修正前に必ず`git status`で現在のブランチを確認
- **mainブランチでの直接作業禁止**: mainブランチで作業している場合は即座に作業用ブランチを作成
- **TodoWrite活用**: 複数ステップの作業では必ずTodoWriteで「ブランチ作成」を最初のタスクに含める
- **エラー時の対処**: 既にmainブランチで変更してしまった場合：
  1. 変更をstash（`git stash`）
  2. 作業用ブランチを作成
  3. stashした変更を適用（`git stash pop`）
  4. 作業を継続

## Project Overview

This repository contains a security validator script for Claude Code CLI that acts as a command execution hook to prevent dangerous system operations. The validator intercepts commands before execution and blocks those that could cause system damage.

## Project Structure

- `security-validator.py` - Main security validation script designed to be installed at `~/.claude/security-validator.py`
- Script uses only Python 3 standard library (no external dependencies)

## Key Commands

### Testing the Validator
```bash
# Test with sample JSON input (simulating Claude Code hook)
echo '{"tool_input": {"command": "rm -rf /"}}' | python3 security-validator.py

# Check security logs
cat ~/.claude/logs/security.log
```

## Architecture

The security validator implements a hook-based security model:

1. **Hook Interface**: Reads JSON from stdin containing command details, returns approval/block decision
2. **Pattern Matching**: Uses regex patterns to detect dangerous commands including:
   - Privilege escalation (`sudo`, `su`)
   - Recursive/force deletions (`rm -rf`)
   - Disk operations (`dd`, `fdisk`, `mkfs`)
   - System control (`shutdown`, `reboot`)
   - Dangerous permission changes (`chmod 777`)
   - System file modifications

3. **Logging System**: All security events are logged to `~/.claude/logs/security.log` with timestamp, command, action, and reason

4. **Fail-Safe Design**: On parsing errors, the validator blocks execution for safety

## Development Guidelines

When modifying the security validator:
- Test all regex patterns thoroughly to avoid false positives
- Ensure Japanese error messages remain clear and helpful
- Maintain the fail-safe principle: when in doubt, block
- Keep the script dependency-free (standard library only)
- Log all security events for audit trails

## Maintenance

### Using Symbolic Links (Recommended)
The script is maintained in the Git repository and linked to Claude's directory:
- **Repository location**: `<your-project-path>/security-validator.py`
- **Claude location**: `~/.claude/security-validator.py` (symlink)

Benefits:
- Changes to the repository file are immediately reflected
- Version control and history tracking
- Easy backup and restoration
- IDE-friendly development

### Updating the Validator
```bash
# Edit the script in your repository
vim <your-project-path>/security-validator.py

# Changes are automatically reflected via symlink
# Test the updated validator
echo '{"tool_input": {"command": "test command"}}' | ~/.claude/security-validator.py
```