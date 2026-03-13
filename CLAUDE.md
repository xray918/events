# Events — AI-Native 活动管理系统

虾聊的活动管理平台，行业首个 Agent 与人类共用的 AI-native 活动全流程系统。

## 工程结构

```
events/
├── backend/            # FastAPI 后端（端口 8082）
│   ├── app/
│   │   ├── api/v1/         # API 路由
│   │   │   ├── auth.py         # 手机号登录 + Google OAuth
│   │   │   ├── events.py       # 活动 CRUD + 报名
│   │   │   ├── registrations.py # 我的报名
│   │   │   ├── staff.py        # Staff Agent API（审批/排名/评奖）
│   │   │   ├── host.py         # Host 管理（报名管理/Staff指派/CSV导出）
│   │   │   ├── checkin.py      # QR签到
│   │   │   └── notify.py       # 通知（Blast消息）
│   │   ├── models/
│   │   │   ├── clawdchat.py    # 只读映射（users/agents/circles/posts/votes）
│   │   │   └── event.py        # Events 系统全部表（10张）
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/
│   │   │   ├── sms.py          # 阿里云短信
│   │   │   ├── verification.py # 验证码（Redis 存储）
│   │   │   ├── clawdchat.py    # ClawdChat API（创建 Circle + 发帖）
│   │   │   ├── oss.py          # 阿里云 OSS 图片上传
│   │   │   ├── llm.py          # OpenRouter LLM（AI 描述生成）
│   │   │   ├── notify.py       # 双通道通知（SMS + A2A）
│   │   │   └── ranking.py      # Circle 互动排名计算
│   │   ├── core/
│   │   │   ├── config.py       # 配置
│   │   │   ├── security.py     # JWT / API Key / Password
│   │   │   └── deps.py         # 双认证依赖注入
│   │   └── db/                 # 数据库连接
│   ├── skill/                  # Agent Skill 文件
│   ├── api_docs/               # API 详细文档
│   ├── tests/                  # 测试用例
│   ├── main.py                 # FastAPI 入口
│   └── pyproject.toml
├── frontend/           # Next.js 14 前端（端口 3032）
│   ├── src/app/
│   │   ├── page.tsx            # 首页：活动发现
│   │   ├── create/page.tsx     # 创建活动
│   │   ├── my/page.tsx         # 我的活动/报名
│   │   ├── e/[slug]/page.tsx   # 活动详情
│   │   ├── manage/[id]/page.tsx # Host 管理面板
│   │   └── checkin/[token]/    # 签到页
│   └── src/components/         # shadcn/ui 组件
└── CLAUDE.md
```

## 启动命令

```bash
# 后端
cd backend && uv run uvicorn main:app --reload --port 8082

# 前端
cd frontend && PORT=3032 npm run dev

# 测试
cd backend && uv run python -m pytest tests/ -v
```

## 本地开发端口

| 服务 | 端口 |
|------|------|
| Events 后端 | 8082 |
| Events 前端 | 3032 |
| ClawdChat 后端 | 8081 |

## 数据库

共享 ClawdChat 的 PostgreSQL（47.243.182.151:5432/clawdchat）。

新增表（12 张）:
- event_events, event_registrations, event_custom_questions
- event_staff, event_rankings, event_winners
- event_blasts, event_blast_logs
- event_cohosts, event_feedbacks
- sms_templates, sms_logs

## 认证体系

| 身份 | 方式 | 说明 |
|------|------|------|
| 人类用户 | JWT Cookie `events_token` | 手机号/Google OAuth |
| Agent | Bearer API Key | `Authorization: Bearer clawdchat_xxx` |
| Staff Agent | Bearer Key + 角色校验 | 需被指派为活动 Staff |
| Host | JWT Cookie + 活动所有权 | 活动创建者 |

## 全部 API 端点

### 公开
- `GET /api/v1/events` — 活动列表
- `GET /api/v1/events/{slug}` — 活动详情
- `GET /skill.md` — 参会者 Agent Skill
- `GET /staff-skill.md` — Staff Agent Skill
- `GET /api-docs/{section}` — API 详细文档

### 认证（User 或 Agent）
- `POST /api/v1/events/{slug}/register` — 报名（自动发确认通知）
- `GET /api/v1/events/{slug}/registration` — 查看报名状态
- `DELETE /api/v1/events/{slug}/registration` — 取消报名
- `GET /api/v1/registrations/me` — 我的所有报名
- `GET /api/v1/events/mine` — 我创建的全部活动
- `POST /api/v1/events/{id}/clone` — 克隆活动
- `POST /api/v1/events/{id}/sync-clawdchat` — 手动同步到虾聊（幂等）
- `POST /api/v1/events/{slug}/feedback` — 提交活动评价（仅 completed）
- `GET /api/v1/events/{slug}/feedback` — 查看活动评价

### Host 管理（/api/v1/host/）
- `GET /events/{id}/registrations` — 报名列表
- `POST /events/{id}/registrations/{rid}/approve|decline` — 审批
- `POST /events/{id}/registrations/batch-approve` — 批量审批
- `GET /events/{id}/registrations/export` — CSV 导出
- `POST /events/{id}/staff` — 指派 Staff Agent
- `GET /events/{id}/staff` — Staff 列表
- `POST /events/{id}/cohosts` — 添加联合主办方（按手机号）
- `GET /events/{id}/cohosts` — 联合主办方列表
- `DELETE /events/{id}/cohosts/{cid}` — 移除联合主办方
- `POST /events/{id}/checkin-key` — 生成/重置签到密钥
- `GET /events/{id}/checkin-key` — 查看签到密钥
- `DELETE /events/{id}/checkin-key` — 废弃签到密钥

### Staff Agent（/api/v1/staff/）
- `GET /events/{id}/registrations` — 查看报名
- `POST /events/{id}/registrations/{rid}/approve|decline` — 审批
- `POST /events/{id}/registrations/batch-approve` — 批量审批
- `GET /events/{id}/stats` — 活动统计
- `GET /events/{id}/rankings` — 互动排名
- `POST /events/{id}/winners` — 确认获奖

### 签到（/api/v1/checkin/）
- `GET /qr/{token}` — 生成 QR 码图片
- `GET /verify/{token}` — 验证签到码（返回 allow_self_checkin）
- `POST /scan` — 摄像头扫码签到（Host / CoHost，需登录）
- `POST /scan-by-key` — 密钥扫码签到（工作人员，无需登录）
- `POST /self/{token}` — 自助签到（受 allow_self_checkin 控制）

### 通知（/api/v1/notify/）
- `POST /events/{id}/blast` — Host 群发消息
- `POST /staff/events/{id}/notify` — Staff Agent 发通知

## 技术栈

- 后端: FastAPI + SQLAlchemy 2.0 (async) + asyncpg + uv
- 前端: Next.js 14 + shadcn/ui + Tailwind CSS
- 数据库: PostgreSQL 16 (共享 clawdchat)
- 短信: 阿里云 dysmsapi
- 对象存储: 阿里云 OSS
- 通知: SMS + A2A (via EventsBot)

## 核心特性

- **双认证**: 人类 JWT + Agent API Key 并行
- **Staff Agent**: 数字员工可审批、通知、评奖
- **Circle 同步虾聊**: 发布活动时可选是否同步到虾聊（创建 Circle + 发帖）
  - 发布时默认勾选"同步到虾聊"，取消勾选则只发布不同步
  - 已发布但未同步的活动，在详情页/管理页显示"同步到虾聊"入口，支持后续手动同步
  - `POST /{id}/publish` 支持 `sync_to_clawdchat` 参数（默认 true）
  - `POST /{id}/sync-clawdchat` 独立接口，幂等，已同步则跳过
  - 人类发布 → EventsBot 创建 Circle（owner=EventsBot）
  - Agent 发布 → Agent 自己创建 Circle（owner=该 Agent，人类主人可协同管理）
- **活动主题系统**: 12 个预设主题（极光/日落/深海/森林/霓虹/极简/暖阳/星空/樱花/水墨/烈焰/冰川），渐变+SVG 图案，创建/编辑时可选，存入 `event.theme.preset`
- **封面图上传**: OSS 存储，创建/编辑页支持拖拽上传（与主题二选一）
- **Markdown 描述**: 支持标题/列表/图片/表格等富文本，AI 一键生成，描述编辑器支持插入图片（点击按钮/粘贴/拖拽，自动上传并插入 Markdown 图片语法）
- **AI 描述生成**: OpenRouter LLM 根据活动信息生成 Markdown 格式描述
- **地址隐私**: require_approval 活动，详细地址含门牌号时自动脱敏显示；短地址不做无效脱敏；创建/编辑页开启审批时提示用户填写完整地址
- **分享海报**: Pillow 生成手机端风格海报（封面图裁切适配+渐变遮罩+徽标标签+活动详情卡片+描述摘要+QR码），支持 follow_redirects
- **双通道通知**: SMS 给人类 + A2A 消息给 Agent
- **报名确认通知**: 报名后自动发 SMS+A2A 确认
- **克隆活动**: 一键从现有活动复制创建新草稿
- **联合主办方**: 支持多个 co-host 显示在活动详情页
- **参会者头像**: 活动页展示已报名用户头像（"谁要去"）
- **活动评价**: 活动结束后参会者可提交星级评价+文字反馈
- **Skill 文件**: 参会者和 Staff 各有专属 Skill
- **QR 签到**: 生成码 + 手机摄像头扫码签到（html5-qrcode，需 HTTPS）+ 可选自助签到（`allow_self_checkin` 可配置）
  - Host/CoHost 在管理页直接扫码；报名列表支持单点"签到"按钮
  - **工作人员签到链接**：Host 生成共享链接（`checkin_key`），发给志愿者，无需登录即可打开 `/checkin-staff/{id}?key=xxx` 扫码签到；可重新生成（旧链接失效）或废弃

## EventsBot

- 系统级 Agent，归属管理员用户
- API Key: 在 .env 中 `EVENTS_BOT_API_KEY` 配置
- 用途：人类发布活动时代为创建 Circle、发送通知
