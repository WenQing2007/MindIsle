import request from './request'

// 学生登录
export function studentLogin(data){
  return request({
    url:'/api/student/login',
    method:'post',
    data
  })
}

// 获取树洞列表
export function getTreeHoleList(){
  return request({
    url:'/api/treehole/list',
    method:'get'
  })
}

// 发布树洞
export function postTreeHole(data){
  return request({
    url:'/api/treehole/add',
    method:'post',
    data
  })
}
// 发送聊天消息
export function sendChatMessage(data) {
  return request({
    url: '/chat',
    method: 'post',
    data: data
  })
}

// 获取该学生所有会话列表
export function getChatSessions(studentId) {
  return request({
    url: `/chat/sessions/${studentId}`,
    method: 'get'
  })
}

// 获取某个会话的聊天历史
export function getChatHistory(sessionId) {
  return request({
    url: `/chat/${sessionId}`,
    method: 'get'
  })
}

// 结束会话
export function endChatSession(sessionId) {
  return request({
    url: `/chat/sessions/${sessionId}/end`,
    method: 'post'
  })
}
// ========== 树洞接口 ==========
// 发布树洞
export function createTreehole(data) {
  return request({
    url: '/api/treehole/add',
    method: 'post',
    data
  })
}
// 获取树洞广场全部列表
export function getTreeholeList() {
  return request({
    url: '/api/treehole/list',
    method: 'get'
  })
}
// 获取我发布的树洞
export function getMyTreehole() {
  return request({
    url: '/api/treehole/my',
    method: 'get'
  })
}

// ========== 心理报告接口 ==========
// 新增报告
export function createReport(data) {
  return request({
    url: '/api/report/add',
    method: 'post',
    data
  })
}
// 根据会话id获取报告列表
export function getReportBySession(sessionId) {
  return request({
    url: `/api/report/list/${sessionId}`,
    method: 'get'
  })
}
// 获取我的所有报告
export function getMyReport() {
  return request({
    url: '/api/report/my',
    method: 'get'
  })
}

