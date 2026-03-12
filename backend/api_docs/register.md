# Registration API

## 报名（Agent 或人类）
```
POST /api/v1/events/{slug}/register
Authorization: Bearer YOUR_API_KEY    (Agent)
               Cookie events_token    (人类)
```
Body:
```json
{
  "custom_answers": {"问题1": "回答1"},
  "phone": "13800138000"
}
```
如果用户没有手机号且未提供，返回 `need_phone: true`，Agent 需向人类索要手机号。

响应:
```json
{
  "success": true,
  "data": {
    "registration_id": "uuid",
    "status": "approved|pending|waitlisted",
    "qr_code_token": "abc123",
    "qr_code_url": "/checkin/abc123",
    "message": "报名成功！"
  }
}
```

## 查看报名状态
```
GET /api/v1/events/{slug}/registration
```

## 取消报名
```
DELETE /api/v1/events/{slug}/registration
```

## 我的所有报名
```
GET /api/v1/registrations/me
```
