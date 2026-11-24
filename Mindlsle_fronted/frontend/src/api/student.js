import request from './request'

// 学生登录
export function studentLogin(data) {
  return request({
    url: '/api/student/login',
    method: 'post',
    data
  })
}

// 学生注册
export function studentRegister(data) {
  return request({
    url: '/api/student/register',
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
// 获取树洞评论列表
export function getTreeHoleComments(hole_id) {
  return request({
    url: '/api/treehole/comments',
    method: 'get',
    params: { hole_id }
  })
}
// 发布树洞评论
export function postTreeHoleComment(data) {
  return request({
    url: '/api/treehole/comment/add',
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

// ===== 情景演练成长记录 =====
export function saveScenarioRecord(data) {
  return request({ url: '/api/scenario/record', method: 'post', data })
}
export function getScenarioRecords(student_id) {
  return request({ url: '/api/scenario/records', method: 'get', params: { student_id } })
}

// ===== 心理量表测评记录 =====
export function saveAssessmentRecord(data) {
  return request({ url: '/api/assessment/record', method: 'post', data })
}
export function getAssessmentRecords(student_id) {
  return request({ url: '/api/assessment/records', method: 'get', params: { student_id } })
}

// ===== 已发布心理资源（内容管理） =====
export function getPublishedResources() {
  return request({ url: '/api/resources', method: 'get' })
}