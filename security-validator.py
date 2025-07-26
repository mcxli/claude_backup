#!/usr/bin/env python3
"""
Claude Code セキュリティバリデーター - 段階2
危険なコマンドパターンを包括的に検出してブロックする
- コマンドインジェクション対策を追加
- 間接実行パターンの検出を追加
- システム管理コマンドの検出を強化
- エラーハンドリングを改善

設置場所: ~/.claude/security-validator.py
実行権限: chmod +x ~/.claude/security-validator.py
"""

import json
import sys
import re
import datetime
import os
from pathlib import Path

def log_security_event(command, action, reason):
    """セキュリティイベントをログに記録"""
    try:
        log_dir = Path.home() / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "security.log"
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "command": command,
            "action": action,
            "reason": reason,
            "user": os.getenv("USER", "unknown"),
            "pwd": os.getcwd()
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        # ログ書き込みエラーは静かに失敗（セキュリティ機能は継続）
        # stderr に最小限のエラー情報を出力
        print(f"# Log write error: {e}", file=sys.stderr)

def is_dangerous_command(command):
    """
    危険なコマンドパターンを包括的にチェック
    段階2: システム破壊リスク、コマンドインジェクション、間接実行を検出
    """
    
    # 超危険コマンドパターン（絶対にブロック）
    CRITICAL_PATTERNS = [
        # sudo系（権限昇格）
        (r'sudo\s+.*', "Root権限での実行は禁止されています"),
        (r'su\s+.*', "ユーザー切り替えは禁止されています"),
        
        # 再帰削除系（データ消失）
        (r'rm\s+-[rf]*r[rf]*\s+.*', "再帰削除は非常に危険です"),
        (r'rm\s+-[rf]*f[rf]*\s+.*/.+', "強制削除は危険です"),
        (r'rm\s+--recursive\s+.*', "再帰削除は非常に危険です"),
        (r'rm\s+--force\s+.*/.+', "強制削除は危険です"),
        (r'rm\s+-r\s+\\*', "全ファイルの再帰削除は極めて危険です"),
        (r'rm\s+--recursive\s+\\*', "全ファイルの再帰削除は極めて危険です"),
        (r'rm\s+-rf\s+/', "ルートディレクトリの削除は禁止されています"),
        (r'rm\s+-rf\s+~', "ホームディレクトリの削除は危険です"),
        (r'rm\s+-rf\s+\.', "カレントディレクトリの削除は危険です"),
        (r'find\s+.*-delete', "findコマンドによる削除は危険です"),
        (r'find\s+.*-exec\s+rm', "findコマンド経由の削除は危険です"),
        
        # ディスク操作系（復旧不可能）
        (r'dd\s+.*', "ディスク直接操作は極めて危険です"),
        (r'fdisk\s+.*', "パーティション操作は危険です"),
        (r'parted\s+.*', "パーティション操作は危険です"),
        (r'mkfs\s+.*', "ファイルシステム作成は危険です"),
        
        # システム制御系（サービス停止）
        (r'shutdown\s+.*', "システムシャットダウンは禁止されています"),
        (r'poweroff\s+.*', "システム電源切断は禁止されています"),
        (r'reboot\s+.*', "システム再起動は禁止されています"),
        (r'halt\s+.*', "システム停止は禁止されています"),
        (r'init\s+[06]', "システム停止/再起動は禁止されています"),
        (r'systemctl\s+(poweroff|reboot|halt|shutdown)', "systemctl経由のシステム制御は禁止されています"),
        (r'service\s+.*\s+(stop|restart)\s*$', "重要サービスの停止/再起動は危険です"),
        (r'telinit\s+[06]', "システム停止/再起動は禁止されています"),
        
        # 権限変更系（セキュリティリスク）
        (r'chmod\s+777\s+.*', "全アクセス権限付与は危険です"),
        (r'chmod\s+-R\s+777\s+.*', "再帰的な全権限付与は極めて危険です"),
        (r'chmod\s+-R\s+777\s+\\*', "全ファイルへの再帰的な全権限付与は極めて危険です"),
        (r'chmod\s+[ago]\+rwx\s+.*', "全アクセス権限付与は危険です"),
        (r'chmod\s+-R\s+666\s+.*', "再帰的な書き込み権限付与は危険です"),
        (r'chown\s+root\s+.*', "root所有権変更は危険です"),
        (r'chown\s+-R\s+root:root\s+/', "システム全体のroot所有権変更は禁止されています"),
        
        # プロセス強制終了系
        (r'kill\s+-9\s+1\s*$', "init プロセス終了は禁止されています"),
        (r'kill\s+-KILL\s+1\s*$', "init プロセス終了は禁止されています"),
        (r'killall\s+-9\s+.*', "一括強制終了は危険です"),
        (r'pkill\s+-9\s+.*', "プロセス名による強制終了は危険です"),
        (r'pkill\s+-KILL\s+.*', "プロセス名による強制終了は危険です"),
        
        # システムファイル操作
        (r'rm\s+.*/(etc|boot|usr|bin|sbin|var|lib|opt)/.*', "システムファイル削除は危険です"),
        (r'.*>\s*/dev/(sda|sdb|sdc|nvme).*', "ディスクデバイスへの書き込みは危険です"),
        (r'>\s*/etc/(passwd|shadow|group|sudoers)', "重要システムファイルへの上書きは禁止されています"),
        (r'>>\s*/etc/(passwd|shadow|group|sudoers)', "重要システムファイルへの追記は危険です"),
        (r'truncate\s+.*/(etc|boot|usr|bin|sbin)/', "システムファイルの切り詰めは危険です"),
        (r'shred\s+.*/(etc|boot|usr|bin|sbin)/', "システムファイルの完全削除は危険です"),
        
        # 危険なワンライナー
        (r':\(\)\{\s*:\|\:&\s*\};\:', "フォークボムは禁止されています"),
        (r'cat\s+/dev/zero\s*>\s*.*', "ディスク容量を消費する操作は危険です"),
        
        # コマンドインジェクション検出
        (r';\s*(sudo|rm\s+-rf?|dd|shutdown|reboot)', "コマンドインジェクションの可能性があります"),
        (r'&&\s*(sudo|rm\s+-rf?|dd|shutdown|reboot)', "コマンド連結による危険な操作です"),
        (r'\|\|\s*(sudo|rm\s+-rf?|dd|shutdown|reboot)', "コマンド連結による危険な操作です"),
        (r'\|\s*(sudo|rm\s+-rf?|dd|shutdown)', "パイプによる危険な操作です"),
        (r'`[^`]*rm\s+-rf?[^`]*`', "バッククォート内の危険な操作です"),
        (r'\$\([^)]*rm\s+-rf?[^)]*\)', "コマンド置換内の危険な操作です"),
        (r'`[^`]*sudo[^`]*`', "バッククォート内のroot権限操作です"),
        (r'\$\([^)]*sudo[^)]*\)', "コマンド置換内のroot権限操作です"),
        
        # 間接実行パターン
        (r'(sh|bash|zsh|ksh)\s+-c\s+["\'].*rm\s+-rf?.*["\']', "シェル経由の危険な操作です"),
        (r'(sh|bash|zsh|ksh)\s+-c\s+["\'].*sudo.*["\']', "シェル経由のroot権限操作です"),
        (r'eval\s+["\'].*rm\s+-rf?.*["\']', "eval経由の危険な操作です"),
        (r'eval\s+["\'].*sudo.*["\']', "eval経由のroot権限操作です"),
        (r'exec\s+.*rm\s+-rf?', "exec経由の危険な操作です"),
        (r'exec\s+.*sudo', "exec経由のroot権限操作です"),
        (r'source\s+.*\.(sh|bash)', "スクリプトのsourceは危険です"),
        (r'\.\s+.*\.(sh|bash)', "スクリプトのsourceは危険です"),
        (r'echo\s+["\'].*rm\s+-rf?.*["\']\s*\|\s*(sh|bash)', "パイプ経由の危険な実行です"),
        (r'printf\s+["\'].*rm\s+-rf?.*["\']\s*\|\s*(sh|bash)', "パイプ経由の危険な実行です"),
    ]
    
    for pattern, reason in CRITICAL_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, reason
    
    return False, None

def main():
    try:
        # 標準入力からJSONデータを読み取り
        data = json.load(sys.stdin)
        
        # コマンド抽出
        tool_input = data.get('tool_input', {})
        command = tool_input.get('command', '')
        
        if not command:
            # コマンドが空の場合は通す
            print(json.dumps({"decision": "approve"}))
            return
        
        # 危険なコマンドチェック
        is_dangerous, reason = is_dangerous_command(command)
        
        if is_dangerous:
            # ログ記録
            log_security_event(command, "BLOCKED", reason)
            
            # ブロック応答
            result = {
                "decision": "block",
                "reason": f"""🚫 SECURITY ALERT: コマンドがブロックされました

コマンド: {command}
理由: {reason}

このコマンドはシステムに深刻な損害を与える可能性があります。
安全な代替手段を使用してください。

セキュリティログ: ~/.claude/logs/security.log"""
            }
            
            print(json.dumps(result, ensure_ascii=False))
            
        else:
            # 安全なコマンドは通す
            print(json.dumps({"decision": "approve"}))
            
    except json.JSONDecodeError as e:
        # JSON解析エラー
        raw_input = str(sys.stdin.buffer.read() if hasattr(sys.stdin, 'buffer') else '<stdin>')[:200]
        log_security_event(f"INVALID_JSON: {raw_input}", "ERROR", f"Failed to parse hook input: {str(e)}")
        result = {
            "decision": "block",
            "reason": "🚫 Hook入力の解析に失敗しました"
        }
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        # その他のエラー
        log_security_event("HOOK_ERROR", "ERROR", str(e))
        # エラー時は安全側に倒してブロック
        result = {
            "decision": "block",
            "reason": f"🚫 内部エラーが発生しました: {str(e)}"
        }
        print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
