import axios from 'axios'

// API基础URL
const BASE_URL = 'http://127.0.0.1:8765'

// 创建axios实例
const http = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
http.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API请求失败:', error)
    return Promise.reject(error)
  }
)

const api = {
  // 配置相关
  getConfig() {
    return http.get('/config')
  },
  
  updateApiKey(provider, apiKey) {
    return http.post('/config/api-key', { provider, api_key: apiKey })
  },
  
  // 模型相关
  getModels() {
    return http.get('/llm/models')
  },
  
  chat(data) {
    return http.post('/llm/chat', data)
  },
  
  // MCP服务器相关
  getServers() {
    return http.get('/mcp/servers')
  },
  
  addServer(data) {
    return http.post('/mcp/servers', data)
  },
  
  updateServer(serverId, data) {
    return http.patch(`/mcp/servers/${serverId}`, data)
  },
  
  enableServer(serverId) {
    return http.post(`/mcp/servers/${serverId}/enable`)
  },
  
  disableServer(serverId) {
    return http.post(`/mcp/servers/${serverId}/disable`)
  },
  
  restartServer(serverId) {
    return http.post(`/mcp/servers/${serverId}/restart`)
  },
  
  deleteServer(serverId) {
    return http.delete(`/mcp/servers/${serverId}`)
  },
  
  // MCP工具相关
  getTools() {
    return http.get('/mcp/tools')
  },
  
  callTool(data) {
    return http.post('/mcp/tools/call', data)
  }
}

export default api
export { BASE_URL }

