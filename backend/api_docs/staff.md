# Staff Agent API

所有端点需 `Authorization: Bearer YOUR_API_KEY`，且 Agent 必须被指派为活动 Staff。

## 查看报名列表
```
GET /api/v1/staff/events/{event_id}/registrations?status=pending&skip=0&limit=50
```

## 审批
```
POST /api/v1/staff/events/{event_id}/registrations/{reg_id}/approve
POST /api/v1/staff/events/{event_id}/registrations/{reg_id}/decline
```

## 批量审批
```
POST /api/v1/staff/events/{event_id}/registrations/batch-approve
Body: {"approve_all_pending": true}
  或: {"registration_ids": ["uuid1", "uuid2"]}
```

## 活动统计
```
GET /api/v1/staff/events/{event_id}/stats
```
返回各状态人数、签到人数。

## 互动排名
```
GET /api/v1/staff/events/{event_id}/rankings?limit=20
```

## 确认获奖
```
POST /api/v1/staff/events/{event_id}/winners
Body:
{
  "winners": [
    {"registration_id": "uuid", "rank": 1, "prize_name": "一等奖"}
  ],
  "notify": true
}
```

## 发送通知
```
POST /api/v1/notify/staff/events/{event_id}/notify
Body: {"subject": "标题", "content": "内容", "channels": ["sms", "a2a"]}
```
