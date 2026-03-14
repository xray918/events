#!/bin/bash
# Events 生产环境启动脚本（近零停机部署）
# 策略：先装依赖+构建，最后一步才杀旧起新，最小化服务中断
# 用法: ./scripts/start.sh

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "🎪 Events — AI-Native 活动系统部署"
echo "=================================="

# ---------------------------------------------------------------------------
# 1. 检查依赖
# ---------------------------------------------------------------------------

check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "❌ $1 未安装"
        return 1
    fi
    echo "  ✅ $1"
}

echo ""
echo "📋 检查依赖..."
check_command uv
check_command node
check_command npm
check_command nginx

# ---------------------------------------------------------------------------
# 2. 预装依赖 + 构建（旧服务仍在运行，用户无感）
# ---------------------------------------------------------------------------

echo ""
echo "📦 [准备阶段] 安装后端依赖..."
cd "$BACKEND_DIR"
cp -f .env.production .env
uv sync 2>&1 | tail -3

echo ""
echo "📦 [准备阶段] 安装前端依赖..."
cd "$FRONTEND_DIR"
cp -f .env.production .env.local

# 只在 package-lock.json 变化时才重装依赖（避免每次 npm ci 删除 node_modules）
LOCK_HASH=$(md5sum package-lock.json 2>/dev/null | cut -d' ' -f1 || echo "none")
LOCK_HASH_FILE="/tmp/events-frontend-lock.md5"
PREV_LOCK_HASH=$(cat "$LOCK_HASH_FILE" 2>/dev/null || echo "")

if [ "$LOCK_HASH" != "$PREV_LOCK_HASH" ] || [ ! -d "node_modules" ]; then
    echo "  依赖有变化，执行 npm install..."
    npm install --production=false 2>&1 | tail -3
    echo "$LOCK_HASH" > "$LOCK_HASH_FILE"
else
    echo "  依赖无变化，跳过安装 ✅"
fi

echo ""
echo "🔍 [准备阶段] 前端 Lint 检查..."
npm run lint 2>&1 | tail -10

echo ""
echo "🔨 [准备阶段] 构建前端..."
time npm run build 2>&1 | tail -5

echo ""
echo "✅ 准备完成，开始切换（停旧启新）..."
echo ""

# ---------------------------------------------------------------------------
# 3. 停旧启新（这里才中断服务，尽快完成）
# ---------------------------------------------------------------------------

# --- 停止旧进程 (多策略确保彻底清理) ---
echo "🛑 停止旧进程..."

kill_by_pid_file() {
    local pidfile="$1" label="$2"
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM -- -"$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
            echo "  $label 进程组 $pid 已发送 TERM"
        fi
        rm -f "$pidfile"
    fi
}

kill_by_pid_file /tmp/events-backend.pid "后端"
kill_by_pid_file /tmp/events-frontend.pid "前端"
sleep 1

# 按端口强杀残留 (lsof / fuser / ss 多重保障)
for port in 8001 3001; do
    lsof -ti:"$port" 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    fuser -k "$port"/tcp 2>/dev/null || true
done

# 按进程名杀孤儿 next-server
pkill -9 -f 'next-server' 2>/dev/null || true
sleep 1

echo "  端口 8001: $(ss -tlnp | grep -c ':8001' || echo 0) 个监听"
echo "  端口 3001: $(ss -tlnp | grep -c ':3001' || echo 0) 个监听"

# --- 立即启动新后端 ---
echo ""
echo "🚀 启动后端 (端口 8001)..."
cd "$BACKEND_DIR"
nohup uv run uvicorn main:app --host 0.0.0.0 --port 8001 --workers 2 \
    > /tmp/events-backend.log 2>&1 &
echo $! > /tmp/events-backend.pid
echo "  PID: $(cat /tmp/events-backend.pid)"

echo -n "  等待后端启动"
for i in $(seq 1 15); do
    if curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 1
done

# --- 立即启动新前端（已构建好，秒启动） ---
echo ""
echo "🚀 启动前端 (端口 3001)..."
cd "$FRONTEND_DIR"
PORT=3001 nohup npx next start -p 3001 \
    > /tmp/events-frontend.log 2>&1 &
echo $! > /tmp/events-frontend.pid
echo "  PID: $(cat /tmp/events-frontend.pid)"

echo -n "  等待前端启动"
for i in $(seq 1 15); do
    if curl -s http://127.0.0.1:3001/ > /dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 1
done

# ---------------------------------------------------------------------------
# 4. Nginx
# ---------------------------------------------------------------------------

echo ""
echo "🔧 配置 Nginx..."
cp -f "$PROJECT_DIR/nginx.conf" /etc/nginx/conf.d/events.conf

nginx -t 2>&1 && echo "  Nginx 配置检查通过" || { echo "❌ Nginx 配置有误"; exit 1; }
nginx -s reload 2>/dev/null || systemctl reload nginx
echo "  Nginx 已重载"

# ---------------------------------------------------------------------------
# 5. 验证
# ---------------------------------------------------------------------------

echo ""
echo "=================================="
echo "🎪 部署完成！"
echo ""
echo "  后端: http://127.0.0.1:8001/health"
echo "  前端: http://127.0.0.1:3001/"
echo "  线上: https://events.clawdchat.cn"
echo ""
echo "📋 日志:"
echo "  后端: tail -f /tmp/events-backend.log"
echo "  前端: tail -f /tmp/events-frontend.log"
echo "=================================="

curl -s http://127.0.0.1:8001/health && echo ""
curl -s http://127.0.0.1:3001/ > /dev/null && echo "前端 OK" || echo "前端启动中..."
