import request from './request'

// 获取学生所有会话列表
export function getSessionList(studentId) {
  return request({
    url: `/chat/sessions/${studentId}`,
    method: 'get'
  })
}

// 获取单个会话历史消息
export function getHistory(sessionId) {
  return request({
    url: `/chat/${sessionId}`,
    method: 'get'
  })
}

// 发送消息
export function sendChatMsg(data) {
  return request({
    url: '/chat',
    method: 'post',
    data
  })
}

// 结束会话
export function closeSession(sessionId) {
  return request({
    url: `/chat/sessions/${sessionId}/end`,
    method: 'post'
  })
}
