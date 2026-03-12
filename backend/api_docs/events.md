# Events API

## 浏览活动列表
```
GET /api/v1/events?status=published&skip=0&limit=20
```
无需认证。返回公开已发布活动。

## 活动详情
```
GET /api/v1/events/{slug}
```
返回含自定义问题、主办方信息的完整活动数据。

## 创建活动（Host）
```
POST /api/v1/events
Authorization: Cookie events_token
```
Body:
```json
{
  "title": "活动名称",
  "description": "描述",
  "event_type": "in_person|online|hybrid",
  "location_name": "地点名",
  "start_time": "2026-04-15T09:00:00+08:00",
  "end_time": "2026-04-16T18:00:00+08:00",
  "capacity": 100,
  "require_approval": true,
  "custom_questions": [
    {"question_text": "问题", "question_type": "text", "is_required": true}
  ],
  "staff_agents": [
    {"agent_name": "my-agent", "role": "staff", "permissions": ["all"]}
  ]
}
```

## 发布/取消
```
POST /api/v1/events/{event_id}/publish
POST /api/v1/events/{event_id}/cancel
```
