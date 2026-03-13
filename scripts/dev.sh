#!/bin/bash
# Events 本地开发环境启停脚本
# 用法: bash scripts/dev.sh [start|stop|restart]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_PORT=8082
FRONTEND_PORT=3032
BACKEND_PID_FILE="/tmp/events-dev-backend.pid"
FRONTEND_PID_FILE="/tmp/events-dev-frontend.pid"

stop_services() {
    echo "🛑 停止本地开发服务..."

    if [ -f "$BACKEND_PID_FILE" ]; then
        OLD_PID=$(cat "$BACKEND_PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill "$OLD_PID" && echo "  后端进程 $OLD_PID 已停止"
        fi
        rm -f "$BACKEND_PID_FILE"
    fi

    if [ -f "$FRONTEND_PID_FILE" ]; then
        OLD_PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill "$OLD_PID" && echo "  前端进程 $OLD_PID 已停止"
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi

    lsof -ti:$BACKEND_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
    sleep 1
    echo "  ✅ 已清理"
}

start_services() {
    echo ""
    echo "🚀 启动后端 (端口 $BACKEND_PORT, reload 模式)..."
    cd "$BACKEND_DIR"
    nohup uv run uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT --reload \
        > /tmp/events-dev-backend.log 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    echo "  PID: $(cat "$BACKEND_PID_FILE")"

    echo -n "  等待后端启动"
    for i in $(seq 1 10); do
        if curl -s http://127.0.0.1:$BACKEND_PORT/health > /dev/null 2>&1; then
            echo " ✅"
            break
        fi
        echo -n "."
        sleep 1
    done

    echo ""
    echo "🚀 启动前端 (端口 $FRONTEND_PORT, dev 模式)..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > /tmp/events-dev-frontend.log 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    echo "  PID: $(cat "$FRONTEND_PID_FILE")"

    echo -n "  等待前端启动"
    for i in $(seq 1 10); do
        if curl -s http://127.0.0.1:$FRONTEND_PORT/ > /dev/null 2>&1; then
            echo " ✅"
            break
        fi
        echo -n "."
        sleep 1
    done

    echo ""
    echo "=================================="
    echo "🎪 本地开发环境已启动"
    echo ""
    echo "  前端: http://localhost:$FRONTEND_PORT"
    echo "  后端: http://localhost:$BACKEND_PORT"
    echo "  API:  http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo "📋 日志:"
    echo "  后端: tail -f /tmp/events-dev-backend.log"
    echo "  前端: tail -f /tmp/events-dev-frontend.log"
    echo "=================================="
}

CMD="${1:-restart}"

case "$CMD" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        start_services
        ;;
    *)
        echo "用法: bash scripts/dev.sh [start|stop|restart]"
        exit 1
        ;;
esac
