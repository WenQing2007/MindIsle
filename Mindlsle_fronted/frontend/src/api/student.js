import request from './request'

export function studentLogin(data) {
  return request({
    url: '/api/student/login',
    method: 'post',
    data
  })
}

export function getTreeHoleList() {
  return request({
    url: '/api/treehole/list',
    method: 'get'
  })
}

export function postTreeHole(data) {
  return request({
    url: '/api/treehole/add',
    method: 'post',
    data
  })
}

export function sendChatMessage(data) {
  return request({
    url: '/api/chat/send',
    method: 'post',
    data
  })
}

export function getChatSessions(student_id) {
  return request({
    url: '/api/chat/sessions',
    method: 'get',
    params: { student_id }
  })
}

export function getChatHistory(session_id) {
  return request({
    url: '/api/chat/history',
    method: 'get',
    params: { session_id }
  })
}

export function endChatSession(session_id) {
  return request({
    url: `/api/chat/sessions/${session_id}/end`,
    method: 'post'
  })
}