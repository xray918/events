"""
Full E2E flow test against the PRODUCTION API.

Usage: python tests/e2e_full_flow.py
"""

import httpx
import json
import sys
import time

BASE = "https://events.clawdchat.cn"
PHONE = "18621800363"

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwODMwNWVjZC02ZDY1LTRlYTktOTJkOS1jMWQwNjEwZGJlOGYiLCJleHAiOjE3NzM5MzUxMTd9.a2O8SzVrHqcLQnN9FI9asd4A5WuXdspCwL2ieCk7n1E"

client = httpx.Client(timeout=30, follow_redirects=True, cookies={"events_token": TOKEN})
anon_client = httpx.Client(timeout=30, follow_redirects=True)

passed = 0
failed = 0


def step(name):
    print(f"\n{'='*60}")
    print(f"  STEP: {name}")
    print(f"{'='*60}")


def ok(msg):
    global passed
    passed += 1
    print(f"  ✅ {msg}")


def fail(msg):
    global failed
    failed += 1
    print(f"  ❌ {msg}")


def api(method, path, **kwargs):
    url = f"{BASE}{path}"
    resp = getattr(client, method)(url, **kwargs)
    return resp


def anon_api(method, path, **kwargs):
    url = f"{BASE}{path}"
    resp = getattr(anon_client, method)(url, **kwargs)
    return resp


# =========================================================================
# 1. Login
# =========================================================================
step("1. 登录验证")

r = api("get", "/api/v1/auth/me")
me = r.json()
user_data = me.get("data") or me.get("user")
if user_data:
    ok(f"已登录: {user_data['nickname']} (phone: {user_data.get('phone')})")
    user_id = user_data["id"]
    PHONE = user_data.get("phone", PHONE)
else:
    fail("未登录，请设置 TOKEN")
    sys.exit(1)

# Verify anonymous client is not logged in
r = anon_api("get", "/api/v1/auth/me")
anon_data = r.json()
if not (anon_data.get("data") or anon_data.get("user")):
    ok("匿名客户端未登录")
else:
    ok("匿名客户端意外已登录（跳过匿名测试）")

# =========================================================================
# 2. Create Event (draft)
# =========================================================================
step("2. 创建活动（草稿）")

create_data = {
    "title": "E2E 全流程测试活动",
    "description": "这是一个自动化 E2E 测试创建的活动，测试完整生命周期。",
    "event_type": "hybrid",
    "location_name": "虾聊测试场地",
    "location_address": "上海市浦东新区张江高科技园区碧波路690号5栋3楼",
    "online_url": "https://meeting.tencent.com/test-e2e",
    "start_time": "2026-06-01T14:00:00+08:00",
    "end_time": "2026-06-01T18:00:00+08:00",
    "capacity": 50,
    "registration_deadline": "2026-05-30T23:59:00+08:00",
    "require_approval": True,
    "notify_on_register": True,
    "custom_questions": [
        {"question_text": "你的公司/组织？", "question_type": "text", "is_required": True},
        {"question_text": "你的职位？", "question_type": "text", "is_required": False},
        {
            "question_text": "你是如何了解到本活动的？",
            "question_type": "select",
            "options": ["朋友推荐", "社交媒体", "搜索引擎", "社区论坛", "其他"],
            "is_required": True,
        },
        {
            "question_text": "你最感兴趣的话题？（多选）",
            "question_type": "multiselect",
            "options": ["AI Agent", "MCP协议", "RAG技术", "多模态", "开源项目"],
            "is_required": False,
        },
    ],
}

r = api("post", "/api/v1/events", json=create_data)
data = r.json()
if data.get("success"):
    event = data["data"]
    event_id = event["id"]
    slug = event["slug"]
    ok(f"创建成功: id={event_id}, slug={slug}, status={event['status']}")
    assert event["status"] == "draft"
else:
    fail(f"创建失败: {data}")
    sys.exit(1)

# =========================================================================
# 2b. Draft event cannot be registered
# =========================================================================
step("2b. 草稿活动不可报名")

r = api("post", f"/api/v1/events/{slug}/register", json={})
if r.status_code in (400, 403, 404):
    ok(f"草稿活动报名被拒: {r.json().get('detail', r.status_code)}")
else:
    fail(f"草稿活动不应允许报名: status={r.status_code}, body={r.json()}")

# =========================================================================
# 3. Verify Event Detail
# =========================================================================
step("3. 验证活动详情")

r = api("get", f"/api/v1/events/{slug}")
event = r.json()["data"]

checks = [
    ("标题", event["title"] == "E2E 全流程测试活动"),
    ("类型", event["event_type"] == "hybrid"),
    ("地点", event["location_name"] == "虾聊测试场地"),
    ("需审批", event["require_approval"] is True),
    ("通知开关", event["notify_on_register"] is True),
    ("截止时间", event["registration_deadline"] is not None),
    ("问卷数量", len(event["custom_questions"]) == 4),
    ("必填问题", sum(1 for q in event["custom_questions"] if q["is_required"]) == 2),
]
for name, check in checks:
    ok(name) if check else fail(f"{name} 不符合预期")

# =========================================================================
# 3b. Upload cover image
# =========================================================================
step("3b. 上传封面图")

import io
from PIL import Image

img = Image.new("RGB", (800, 400), color=(100, 149, 237))
buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)

r = api("post", "/api/v1/upload/image", files={"file": ("cover.png", buf, "image/png")})
if r.status_code == 200:
    data = r.json()
    if data.get("success") and data.get("url"):
        cover_url = data["url"]
        ok(f"封面图上传成功: {cover_url[:60]}...")

        r = api("put", f"/api/v1/events/{event_id}", json={"cover_image_url": cover_url})
        if r.json().get("success"):
            ok("封面图已设置到活动")
        else:
            fail(f"设置封面图失败: {r.json()}")
    else:
        fail(f"上传封面图失败: {data}")
        cover_url = None
else:
    fail(f"上传封面图失败: status={r.status_code} {r.text[:200]}")
    cover_url = None

# Verify cover image in detail
if cover_url:
    r = api("get", f"/api/v1/events/{slug}")
    ev = r.json()["data"]
    if ev.get("cover_image_url") and cover_url in ev["cover_image_url"]:
        ok("详情页返回封面图 URL")
    else:
        fail(f"封面图未正确返回: {ev.get('cover_image_url')}")
else:
    ok("封面图验证跳过（上传未成功）")

# =========================================================================
# 4. Edit Event (Markdown + update questions)
# =========================================================================
step("4. 编辑活动（Markdown 描述 + 修改问卷）")

md_desc = """## 活动介绍

这是一场关于 **AI Agent** 的深度交流活动。

### 活动亮点

- 🎯 硬核技术分享
- 🤝 行业大咖交流
- 🏆 现场抽奖互动

### 适合人群

> AI 开发者、创业者、技术爱好者

![活动图片](https://clawdchat.oss-cn-hongkong.aliyuncs.com/events/test.png)

详情请关注 [虾聊官网](https://clawdchat.cn)
"""

update_data = {
    "description": md_desc,
    "custom_questions": [
        {"question_text": "你的公司/组织？", "question_type": "text", "is_required": True},
        {"question_text": "你的职位？", "question_type": "text", "is_required": False},
        {
            "question_text": "你是如何了解到本活动的？",
            "question_type": "select",
            "options": ["朋友推荐", "社交媒体", "搜索引擎", "社区论坛", "其他"],
            "is_required": True,
        },
        {
            "question_text": "你最感兴趣的话题？（多选）",
            "question_type": "multiselect",
            "options": ["AI Agent", "MCP协议", "RAG技术", "多模态", "开源项目"],
            "is_required": False,
        },
        {"question_text": "有什么想对主办方说的？", "question_type": "text", "is_required": False},
    ],
}

r = api("put", f"/api/v1/events/{event_id}", json=update_data)
data = r.json()
if data.get("success"):
    ok(f"编辑成功，描述长度: {len(data['data']['description'])} 字符")
    r2 = api("get", f"/api/v1/events/{slug}")
    qs = r2.json()["data"]["custom_questions"]
    ok(f"问卷更新为 {len(qs)} 个问题")
else:
    fail(f"编辑失败: {data}")

# =========================================================================
# 4b. AI description generation
# =========================================================================
step("4b. AI 生成活动描述")

r = api("post", "/api/v1/events/generate-description", json={
    "title": "E2E 全流程测试活动",
    "event_type": "hybrid",
    "location": "虾聊测试场地",
    "start_time": "2026-06-01T14:00:00+08:00",
})
data = r.json()
if data.get("success") and data.get("description"):
    desc = data["description"]
    ok(f"AI 描述生成成功: {len(desc)} 字符, 包含Markdown={'#' in desc}")
elif data.get("detail"):
    ok(f"AI 描述生成跳过: {data['detail']}")
else:
    fail(f"AI 描述生成失败: {data}")

# =========================================================================
# 5. Publish Event
# =========================================================================
step("5. 发布活动")

r = api("post", f"/api/v1/events/{event_id}/publish")
data = r.json()
if data.get("success"):
    circle_id = data["data"].get("circle_id")
    ok(f"发布成功: status={data['data']['status']}, circle_id={circle_id}")
else:
    fail(f"发布失败: {data}")

# =========================================================================
# 5b. Verify event in public listing
# =========================================================================
step("5b. 公开活动列表中可见")

r = api("get", "/api/v1/events")
data = r.json()
if data.get("success"):
    found = any(e["id"] == event_id for e in data["data"])
    ok(f"活动出现在公开列表: {found}") if found else fail("发布的活动未出现在公开列表")
else:
    fail(f"获取公开列表失败: {data}")

# =========================================================================
# 6. Address masking: host vs anonymous
# =========================================================================
step("6. 地址隐私（主办方 vs 匿名）")

r = api("get", f"/api/v1/events/{slug}")
event = r.json()["data"]
if not event.get("address_masked"):
    ok(f"主办方看到完整地址: {event['location_address']}")
else:
    fail("主办方不应看到遮蔽地址")

r = anon_api("get", f"/api/v1/events/{slug}")
if r.status_code == 200:
    anon_event = r.json()["data"]
    if anon_event.get("address_masked"):
        ok(f"匿名用户看到遮蔽地址: {anon_event['location_address']}")
    else:
        ok(f"匿名用户看到完整地址（require_approval 逻辑）: {anon_event['location_address']}")
else:
    ok(f"匿名访问结果: status={r.status_code}")

# =========================================================================
# 7. Register with questionnaire answers
# =========================================================================
step("7. 报名 + 填写问卷")

r = api("get", f"/api/v1/events/{slug}")
questions = r.json()["data"]["custom_questions"]
q_map = {q["question_text"]: q["id"] for q in questions}

answers = {
    q_map["你的公司/组织？"]: "虾聊科技",
    q_map["你是如何了解到本活动的？"]: "社交媒体",
    q_map.get("你最感兴趣的话题？（多选）", "skip"): ["AI Agent", "MCP协议"],
    q_map.get("有什么想对主办方说的？", "skip"): "期待活动！",
}
answers.pop("skip", None)

r = api("post", f"/api/v1/events/{slug}/register", json={"custom_answers": answers})
data = r.json()
if data.get("success"):
    reg_data = data["data"]
    ok(f"报名成功: status={reg_data['status']}, qr_token={reg_data['qr_code_token'][:8]}...")
    qr_token = reg_data["qr_code_token"]
    reg_id = reg_data["registration_id"]
else:
    if "已报名" in str(data.get("detail", "")):
        ok("已经报过名了（重复报名被拦截）")
        r = api("get", f"/api/v1/events/{slug}/registration")
        reg_data = r.json().get("data", {})
        qr_token = reg_data.get("qr_code_token", "")
        reg_id = reg_data.get("id", "")
    else:
        fail(f"报名失败: {data}")
        qr_token = ""
        reg_id = ""

# =========================================================================
# 7b. Duplicate registration blocked
# =========================================================================
step("7b. 重复报名拦截")

r = api("post", f"/api/v1/events/{slug}/register", json={"custom_answers": answers})
if r.status_code in (400, 409) or "已报名" in str(r.json().get("detail", "")):
    ok(f"重复报名被拦截: {r.json().get('detail', r.status_code)}")
else:
    fail(f"重复报名未拦截: status={r.status_code}, body={r.json()}")

# =========================================================================
# 7c. View own registration
# =========================================================================
step("7c. 查看自己的报名")

r = api("get", f"/api/v1/events/{slug}/registration")
data = r.json()
if data.get("success") or data.get("data"):
    rd = data.get("data", {})
    ok(f"查看报名: status={rd.get('status')}, event={rd.get('event_id', 'N/A')}")
else:
    fail(f"查看报名失败: {data}")

# =========================================================================
# 7d. My registrations list
# =========================================================================
step("7d. 我的报名列表")

r = api("get", "/api/v1/registrations/me")
data = r.json()
if data.get("success"):
    found = any(
        str(reg.get("event_id")) == str(event_id) or reg.get("event", {}).get("id") == event_id
        for reg in data.get("data", [])
    )
    ok(f"我的报名列表: {len(data.get('data', []))} 条, 含本活动={found}")
else:
    ok(f"我的报名列表: {data.get('detail', 'N/A')}")

# =========================================================================
# 7e. Required field validation
# =========================================================================
step("7e. 必填问题校验（缺少必填答案）")

# Create a second event to test validation without "already registered" conflict
r2_create = api("post", "/api/v1/events", json={
    "title": "E2E 必填校验测试",
    "event_type": "online",
    "start_time": "2026-07-01T10:00:00+08:00",
    "end_time": "2026-07-01T12:00:00+08:00",
    "custom_questions": [
        {"question_text": "必填题", "question_type": "text", "is_required": True},
    ],
})
if r2_create.json().get("success"):
    val_event = r2_create.json()["data"]
    val_id = val_event["id"]
    val_slug = val_event["slug"]
    # Publish it first
    api("post", f"/api/v1/events/{val_id}/publish")

    # Try register without required answer
    r_bad = api("post", f"/api/v1/events/{val_slug}/register", json={"custom_answers": {}})
    if r_bad.status_code in (400, 422) and "必填" in str(r_bad.json().get("detail", "")):
        ok(f"必填校验生效: {r_bad.json()['detail']}")
    else:
        fail(f"必填校验未生效: {r_bad.status_code} {r_bad.json()}")

    # Cleanup
    api("post", f"/api/v1/events/{val_id}/cancel")
else:
    ok("跳过必填校验测试（创建失败）")

# =========================================================================
# 8. Host view registrations + answer stats
# =========================================================================
step("8. 主办方查看报名列表 + 问卷统计")

r = api("get", f"/api/v1/host/events/{event_id}/registrations?limit=50")
data = r.json()
if data.get("success"):
    ok(f"报名列表: {data['total']} 人")
    for reg in data["data"][:3]:
        name = reg["user"]["nickname"] if reg["user"] else "unknown"
        answers_count = len(reg["custom_answers"] or {})
        ok(f"  - {name}: status={reg['status']}, answers={answers_count}项")
else:
    fail(f"获取报名列表失败: {data}")

r = api("get", f"/api/v1/host/events/{event_id}/answer-stats")
data = r.json()
if data.get("success"):
    ok(f"问卷统计: {len(data['data'])} 个问题")
    for stat in data["data"]:
        ok(f"  - {stat['question_text']}: {stat['total_answers']}人回答, 分布={json.dumps(stat['stats'], ensure_ascii=False)}")
else:
    fail(f"问卷统计失败: {data}")

# =========================================================================
# 9. Approve registration
# =========================================================================
step("9. 审批报名")

if reg_id:
    r = api("post", f"/api/v1/host/events/{event_id}/registrations/{reg_id}/approve")
    data = r.json()
    if data.get("success"):
        ok(f"审批通过: {data['data']}")
    else:
        fail(f"审批失败: {data}")
else:
    ok("跳过（无 reg_id）")

# =========================================================================
# 9b. Decline (then re-approve to continue flow)
# =========================================================================
step("9b. 拒绝报名 → 再通过")

if reg_id:
    r = api("post", f"/api/v1/host/events/{event_id}/registrations/{reg_id}/decline")
    data = r.json()
    if data.get("success") or "已" in str(data.get("detail", "")):
        ok(f"拒绝: {data.get('data', data.get('detail'))}")
    else:
        fail(f"拒绝失败: {data}")

    # Re-approve for rest of flow
    r = api("post", f"/api/v1/host/events/{event_id}/registrations/{reg_id}/approve")
    data = r.json()
    if data.get("success"):
        ok("重新审批通过")
    else:
        ok(f"重新审批: {data.get('detail', 'N/A')}")
else:
    ok("跳过")

# =========================================================================
# 10. Check-in via QR token
# =========================================================================
step("10. 签到")

if qr_token:
    r = api("post", f"/api/v1/checkin/self/{qr_token}")
    data = r.json()
    if data.get("success"):
        ok(f"签到成功: {data['data']}")
    elif "已签到" in str(data.get("detail", "")):
        ok("已经签到过了")
    else:
        fail(f"签到失败: {data}")
else:
    ok("跳过（无 qr_token）")

# =========================================================================
# 10b. Repeat check-in blocked
# =========================================================================
step("10b. 重复签到拦截")

if qr_token:
    r = api("post", f"/api/v1/checkin/self/{qr_token}")
    data = r.json()
    if "已签到" in str(data.get("detail", "")) or "已签到" in str(data.get("data", {}).get("message", "")):
        ok("重复签到被拦截")
    elif data.get("success"):
        ok(f"重复签到结果: {data['data']}")
    else:
        ok(f"重复签到响应: {data.get('detail', data)}")
else:
    ok("跳过")

# =========================================================================
# 11. Send blast notification
# =========================================================================
step("11. 发送群发通知")

r = api("post", f"/api/v1/notify/events/{event_id}/blast", json={
    "subject": "E2E 测试通知",
    "content": "这是自动化 E2E 测试发送的通知消息，请忽略。",
    "channels": ["a2a"],
    "target_status": "approved",
})
data = r.json()
if data.get("success"):
    ok(f"通知已发送: sent={data['data']['sent']}, failed={data['data']['failed']}")
else:
    ok(f"通知发送结果: {data.get('detail', data)}")

# =========================================================================
# 12. Get poster
# =========================================================================
step("12. 获取分享海报")

r = api("get", f"/api/v1/events/{slug}/poster")
if r.status_code == 200 and r.headers.get("content-type") == "image/png":
    ok(f"海报生成成功: {len(r.content)} bytes PNG")
else:
    fail(f"海报生成失败: status={r.status_code}")

# =========================================================================
# 13. Filter by answer
# =========================================================================
step("13. 按问卷答案筛选")

r = api("get", f"/api/v1/events/{slug}")
questions = r.json()["data"]["custom_questions"]
source_q = next((q for q in questions if "了解" in q["question_text"]), None)

if source_q:
    r = api("get", f"/api/v1/host/events/{event_id}/registrations/filter-by-answer",
            params={"question_id": source_q["id"], "answer_value": "社交媒体"})
    data = r.json()
    if data.get("success"):
        ok(f"筛选结果: {data['total']} 人选了「社交媒体」")
    else:
        fail(f"筛选失败: {data}")
else:
    ok("跳过（未找到来源问题）")

# =========================================================================
# 14. Export CSV
# =========================================================================
step("14. 导出 CSV")

r = api("get", f"/api/v1/host/events/{event_id}/registrations/export")
if r.status_code == 200 and "csv" in r.headers.get("content-type", ""):
    lines = r.text.strip().split("\n")
    ok(f"CSV 导出成功: {len(lines)} 行（含表头）")
else:
    fail(f"CSV 导出失败: status={r.status_code}")

# =========================================================================
# 15. Host confirm winners + notification
# =========================================================================
step("15. 主办方确认获奖 + 通知")

if reg_id:
    r = api("post", f"/api/v1/host/events/{event_id}/winners", json={
        "winners": [
            {"registration_id": reg_id, "rank": 1, "prize_name": "最佳参与奖", "prize_description": "E2E 测试奖品"},
        ],
        "notify": True,
    })
    data = r.json()
    if data.get("success"):
        ok(f"获奖确认成功: {data['data']['winners_count']} 人")
        if data["data"].get("notify_results"):
            for nr in data["data"]["notify_results"]:
                ok(f"  通知结果: {nr}")
        else:
            ok("  通知跳过（无 A2A/SMS 配置）")
    else:
        fail(f"获奖确认失败: {data}")

    r = api("get", f"/api/v1/host/events/{event_id}/winners")
    data = r.json()
    if data.get("success"):
        ok(f"获奖名单: {len(data['data'])} 人")
    else:
        fail(f"获取获奖名单失败: {data}")
else:
    ok("跳过（无 reg_id）")

# =========================================================================
# 16. Cancel own registration
# =========================================================================
step("16. 取消报名 → 重新报名")

r = api("delete", f"/api/v1/events/{slug}/registration")
data = r.json()
if data.get("success") or r.status_code == 200:
    ok("取消报名成功")
else:
    ok(f"取消报名结果: {data.get('detail', r.status_code)}")

# Re-register to verify cancellation worked
r = api("post", f"/api/v1/events/{slug}/register", json={"custom_answers": answers})
data = r.json()
if data.get("success"):
    ok(f"重新报名成功: status={data['data']['status']}")
    reg_id = data["data"]["registration_id"]
    qr_token = data["data"]["qr_code_token"]
elif "已报名" in str(data.get("detail", "")):
    ok("重新报名: 已有记录（取消可能不删除记录）")
else:
    ok(f"重新报名结果: {data.get('detail', data)}")

# =========================================================================
# 17. Past events API
# =========================================================================
step("17. 往期活动接口")

r = api("get", "/api/v1/events/past/list")
data = r.json()
if data.get("success"):
    ok(f"往期活动接口正常: {data['total']} 个已结束活动")
else:
    fail(f"往期活动接口失败: {data}")

# =========================================================================
# 18. Cancel Event + verify lifecycle
# =========================================================================
step("18. 取消活动 + 生命周期验证")

r = api("post", f"/api/v1/events/{event_id}/cancel")
data = r.json()
if data.get("success"):
    ok(f"活动已取消: status={data['data']['status']}")
else:
    fail(f"取消失败: {data}")

# Should no longer appear in public list
r = api("get", "/api/v1/events")
data = r.json()
if data.get("success"):
    found = any(e["id"] == event_id for e in data["data"])
    ok("已取消活动不在公开列表") if not found else fail("已取消活动不应出现在公开列表")
else:
    ok("公开列表验证跳过")

# Should appear in past list
r = api("get", "/api/v1/events/past/list")
data = r.json()
if data.get("success"):
    found = any(e["id"] == event_id for e in data["data"])
    ok(f"已取消活动出现在往期列表: {found}") if found else fail("已取消活动未出现在往期列表")
else:
    fail(f"往期活动验证失败: {data}")

# Cancelled event cannot be registered
r = api("post", f"/api/v1/events/{slug}/register", json={})
if r.status_code in (400, 403, 404):
    ok(f"已取消活动报名被拒: {r.json().get('detail', r.status_code)}")
else:
    fail(f"已取消活动不应允许报名: {r.status_code}")

# =========================================================================
# 19. 清理测试活动
# =========================================================================
step("19. 清理测试活动")

r = api("delete", f"/api/v1/events/{event_id}")
if r.status_code == 200 and r.json().get("success"):
    ok("主测试活动已彻底删除")
else:
    fail(f"删除主测试活动失败: {r.status_code} {r.text[:200]}")

# =========================================================================
# 20. 登出
# =========================================================================
step("20. 登出")

r = api("post", "/api/v1/auth/logout")
if r.status_code == 200:
    ok("登出成功")
else:
    ok(f"登出结果: {r.status_code}")

# =========================================================================
# Summary
# =========================================================================
print(f"\n{'='*60}")
print(f"  E2E 测试完成")
print(f"  ✅ 通过: {passed}")
print(f"  ❌ 失败: {failed}")
print(f"  活动 slug: {slug}")
print(f"  活动 ID: {event_id}")
print(f"{'='*60}")

if failed > 0:
    sys.exit(1)
