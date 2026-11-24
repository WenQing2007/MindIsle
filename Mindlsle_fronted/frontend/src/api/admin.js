import request from './request'

// ===== 用户管理 =====
export function getAdminUsers(role) {
  return request({ url: '/api/admin/users', method: 'get', params: role ? { role } : {} })
}
export function createAdminUser(data) {
  return request({ url: '/api/admin/users', method: 'post', data })
}
export function updateAdminUser(userId, data) {
  return request({ url: `/api/admin/users/${userId}`, method: 'put', data })
}
export function deleteAdminUser(userId) {
  return request({ url: `/api/admin/users/${userId}`, method: 'delete' })
}

// ===== 内容管理：树洞审核 + 资源 =====
export function getAdminTreeholes(status) {
  return request({ url: '/api/admin/treehole', method: 'get', params: status ? { status } : {} })
}
export function reviewTreehole(holeId, status) {
  return request({ url: `/api/admin/treehole/${holeId}/review`, method: 'post', data: { status } })
}
export function deleteTreehole(holeId) {
  return request({ url: `/api/admin/treehole/${holeId}`, method: 'delete' })
}
export function getAdminResources() {
  return request({ url: '/api/admin/resources', method: 'get' })
}
export function createResource(data) {
  return request({ url: '/api/admin/resources', method: 'post', data })
}
export function updateResource(resId, data) {
  return request({ url: `/api/admin/resources/${resId}`, method: 'put', data })
}
export function deleteResource(resId) {
  return request({ url: `/api/admin/resources/${resId}`, method: 'delete' })
}

// ===== 日志 =====
export function getLoginLogs(limit = 100) {
  return request({ url: '/api/admin/logs/login', method: 'get', params: { limit } })
}
export function getOperationLogs(limit = 100) {
  return request({ url: '/api/admin/logs/operation', method: 'get', params: { limit } })
}

// ===== 安全配置 =====
export function getAdminConfig() {
  return request({ url: '/api/admin/config', method: 'get' })
}
export function updateHotline(hotline) {
  return request({ url: '/api/admin/config/hotline', method: 'post', data: { hotline } })
}
export function getRiskKeywords() {
  return request({ url: '/api/admin/risk-keywords', method: 'get' })
}
export function addRiskKeyword(level, keyword) {
  return request({ url: '/api/admin/risk-keywords', method: 'post', data: { level, keyword } })
}
export function toggleRiskKeyword(kid, enabled) {
  return request({ url: `/api/admin/risk-keywords/${kid}`, method: 'put', data: { enabled } })
}
export function deleteRiskKeyword(kid) {
  return request({ url: `/api/admin/risk-keywords/${kid}`, method: 'delete' })
}
export function seedRiskKeywords() {
  return request({ url: '/api/admin/risk-keywords/seed', method: 'post' })
}

// ===== 协作日志 =====
export function getCollaboration(sessionId) {
  return request({ url: '/api/admin/collaboration/latest', method: 'get', params: sessionId ? { session_id: sessionId } : {} })
}
