#!/bin/bash
# Events 远程部署脚本
# 用法: bash deploy.sh [deploy|sync|restart|stop|logs|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/deploy.config"

CMD="${1:-deploy}"
SSH_CMD="sshpass -p '$DEPLOY_PASS' ssh -o StrictHostKeyChecking=no $DEPLOY_USER@$DEPLOY_HOST"
RSYNC_CMD="sshpass -p '$DEPLOY_PASS' rsync -avz --delete \
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
        echo "🚀 完整部署 Events..."
        echo "📤 同步代码到 $DEPLOY_HOST:$DEPLOY_PATH..."
        eval "$RSYNC_CMD"
        echo "🔧 远程执行启动脚本..."
        eval "$SSH_CMD 'cd $DEPLOY_PATH && chmod +x scripts/*.sh && bash scripts/start.sh'"
        echo "✅ 部署完成!"
        ;;
    sync)
        echo "📤 仅同步代码..."
        eval "$RSYNC_CMD"
        echo "✅ 同步完成"
        ;;
    restart)
        echo "🔄 重启服务..."
        eval "$SSH_CMD 'cd $DEPLOY_PATH && bash scripts/start.sh'"
        ;;
    stop)
        echo "🛑 停止服务..."
        eval "$SSH_CMD 'cd $DEPLOY_PATH && bash scripts/stop.sh'"
        ;;
    logs)
        echo "📋 查看日志..."
        eval "$SSH_CMD 'tail -50 /tmp/events-backend.log && echo \"---\" && tail -20 /tmp/events-frontend.log'"
        ;;
    status)
        echo "📊 服务状态..."
        eval "$SSH_CMD 'echo \"后端:\" && curl -s http://127.0.0.1:8001/health && echo \"\" && echo \"前端:\" && curl -s -o /dev/null -w \"%{http_code}\" http://127.0.0.1:3001/ && echo \"\"'"
        ;;
    *)
        echo "用法: bash deploy.sh [deploy|sync|restart|stop|logs|status]"
        exit 1
        ;;
esac
