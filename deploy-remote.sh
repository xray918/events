#!/bin/bash
# Events 本地一键远程部署脚本
# 用法: bash deploy-remote.sh [deploy|sync|restart|stop|logs|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/deploy.config"

CMD="${1:-deploy}"

SSHPASS="sshpass -p '$DEPLOY_PASS'"
SSH="$SSHPASS ssh -o StrictHostKeyChecking=no $DEPLOY_USER@$DEPLOY_HOST"
RSYNC="$SSHPASS rsync -avz --delete \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.next' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='.pytest_cache' \
    --exclude='.env' \
    --exclude='.env.local' \
    -e 'ssh -o StrictHostKeyChecking=no' \
    $SCRIPT_DIR/ $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH/"

case "$CMD" in
    deploy)
        echo "🚀 完整部署 Events 到 $DEPLOY_HOST..."
        echo ""
        echo "📤 同步代码..."
        eval "$RSYNC"
        echo ""
        echo "🔧 远程执行启动脚本..."
        eval "$SSH 'cd $DEPLOY_PATH && chmod +x scripts/*.sh && bash scripts/start.sh'"
        echo ""
        echo "✅ 部署完成！线上地址: https://events.clawdchat.cn"
        ;;
    sync)
        echo "📤 仅同步代码到 $DEPLOY_HOST:$DEPLOY_PATH ..."
        eval "$RSYNC"
        echo "✅ 同步完成"
        ;;
    restart)
        echo "🔄 重启服务..."
        eval "$SSH 'cd $DEPLOY_PATH && bash scripts/start.sh'"
        ;;
    stop)
        echo "🛑 停止服务..."
        eval "$SSH 'cd $DEPLOY_PATH && bash scripts/stop.sh'"
        ;;
    logs)
        echo "📋 查看日志 (最新 50 行)..."
        eval "$SSH 'echo \"=== 后端日志 ===\"; tail -50 /tmp/events-backend.log; echo \"\"; echo \"=== 前端日志 ===\"; tail -20 /tmp/events-frontend.log'"
        ;;
    status)
        echo "📊 服务状态..."
        eval "$SSH 'echo \"后端:\"; curl -s http://127.0.0.1:8001/health; echo \"\"; echo \"前端:\"; curl -s -o /dev/null -w \"HTTP %{http_code}\" http://127.0.0.1:3001/; echo \"\"'"
        ;;
    ssh)
        echo "🔑 登录服务器..."
        eval "$SSH"
        ;;
    *)
        echo "用法: bash deploy-remote.sh [deploy|sync|restart|stop|logs|status|ssh]"
        echo ""
        echo "  deploy   — 同步代码 + 安装依赖 + 重启服务（完整部署）"
        echo "  sync     — 仅同步代码，不重启"
        echo "  restart  — 不同步，仅重启服务"
        echo "  stop     — 停止所有服务"
        echo "  logs     — 查看后端 + 前端日志"
        echo "  status   — 检查服务是否健康"
        echo "  ssh      — 登录到服务器"
        exit 1
        ;;
esac
