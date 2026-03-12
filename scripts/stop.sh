#!/bin/bash
# Events 停止脚本

echo "🛑 停止 Events 服务..."

if [ -f /tmp/events-backend.pid ]; then
    kill "$(cat /tmp/events-backend.pid)" 2>/dev/null && echo "  后端已停止"
    rm -f /tmp/events-backend.pid
fi

if [ -f /tmp/events-frontend.pid ]; then
    kill "$(cat /tmp/events-frontend.pid)" 2>/dev/null && echo "  前端已停止"
    rm -f /tmp/events-frontend.pid
fi

lsof -ti:8001 2>/dev/null | xargs -r kill -9 2>/dev/null || true
lsof -ti:3001 2>/dev/null | xargs -r kill -9 2>/dev/null || true

echo "✅ 完成"
