import request from './request'

// 学生登录
export function studentLogin(data) {
  return request({
    url: '/api/student/login',
    method: 'post',
    data
  })
}

// 获取树洞列表
export function getTreeHoleList() {
  return request({
    url: '/api/treehole/list',
    method: 'get'
  })
}

// 发布树洞
export function postTreeHole(data) {
  return request({
    url: '/api/treehole/add',
    method: 'post',
    data
  })
}

// 发送聊天消息
export function sendChatMessage(data) {
  return request({
    url: '/api/chat/send',
    method: 'post',
    data
  })
}

// 获取该学生所有会话
export function getChatSessions(student_id) {
  return request({
    url: '/api/chat/sessions',
    method: 'get',
    params: { student_id }
  })
}

// 获取单条会话聊天记录
export function getChatHistory(session_id) {
  return request({
    url: '/api/chat/history',
    method: 'get',
    params: { session_id }
  })
}

// 结束会话
export function endChatSession(session_id) {
  return request({
    url: `/api/chat/sessions/${session_id}/end`,
    method: 'post'
  })
}

// ---- 新增：心理报告相关接口（顺便一起补上，和之前文档对齐）
export function getReportList(student_id) {
  return request({
    url: '/api/report/list',
    method: 'get',
    params: { student_id }
  })
}

export function getReportDetail(report_id) {
  return request({
    url: '/api/report/detail',
    method: 'get',
    params: { report_id }
  })
}
