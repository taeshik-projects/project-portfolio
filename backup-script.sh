#!/bin/bash
# OpenClaw 중요 파일 자동 백업 스크립트

BACKUP_DIR=~/.openclaw/backups
WORKSPACE=~/.openclaw/workspace
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_PATH"

# 중요 파일 백업
cp "$WORKSPACE/MEMORY.md" "$BACKUP_PATH/" 2>/dev/null
cp "$WORKSPACE/investment-constitution.md" "$BACKUP_PATH/" 2>/dev/null
cp "$WORKSPACE/AGENTS.md" "$BACKUP_PATH/" 2>/dev/null
cp "$WORKSPACE/USER.md" "$BACKUP_PATH/" 2>/dev/null
cp "$WORKSPACE/SOUL.md" "$BACKUP_PATH/" 2>/dev/null
cp "$WORKSPACE/TOOLS.md" "$BACKUP_PATH/" 2>/dev/null
cp "$WORKSPACE/IDENTITY.md" "$BACKUP_PATH/" 2>/dev/null
cp "$WORKSPACE/TODO.md" "$BACKUP_PATH/" 2>/dev/null
cp -r "$WORKSPACE/memory/" "$BACKUP_PATH/" 2>/dev/null

# 설정 파일 백업
cp ~/.openclaw/openclaw.json "$BACKUP_PATH/" 2>/dev/null

# 30일 이상 된 백업 삭제
find "$BACKUP_DIR" -type d -name "backup_*" -mtime +30 -exec rm -rf {} \; 2>/dev/null

echo "✅ Backup completed: $BACKUP_PATH"
