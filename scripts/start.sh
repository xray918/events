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
# 3. 注册 systemd 服务（首次部署时自动启用，后续 reload 即可）
# ---------------------------------------------------------------------------

echo "🔧 注册 systemd 服务..."
cp -f "$SCRIPT_DIR/events-backend.service" /etc/systemd/system/events-backend.service
cp -f "$SCRIPT_DIR/events-frontend.service" /etc/systemd/system/events-frontend.service
systemctl daemon-reload
systemctl enable events-backend events-frontend
echo "  systemd 服务已注册并设为开机自启"

# ---------------------------------------------------------------------------
# 4. 停旧启新（这里才中断服务，尽快完成）
# ---------------------------------------------------------------------------

echo ""
echo "🛑 重启服务..."
systemctl restart events-backend
echo "  后端已重启"
systemctl restart events-frontend
echo "  前端已重启"

echo -n "  等待后端启动"
for i in $(seq 1 15); do
    if curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 1
done

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
# 5. Nginx
# ---------------------------------------------------------------------------

echo ""
echo "🔧 配置 Nginx..."
cp -f "$PROJECT_DIR/nginx.conf" /etc/nginx/conf.d/events.conf

nginx -t 2>&1 && echo "  Nginx 配置检查通过" || { echo "❌ Nginx 配置有误"; exit 1; }
nginx -s reload 2>/dev/null || systemctl reload nginx
echo "  Nginx 已重载"

# ---------------------------------------------------------------------------
# 6. 验证
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
