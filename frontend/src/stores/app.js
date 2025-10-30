import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAppStore = defineStore('app', () => {
  // 状态
  const apiConfig = ref({
    deepseek: false,
    qwen: false
  })
  
  const availableModels = ref({})
  const mcpServers = ref([])
  const mcpTools = ref([])
  
  // 聊天相关状态
  const chatMessages = ref([])
  const chatConfig = ref({
    provider: '',
    model: '',
    useMcpTools: true
  })
  
  // 初始化
  const init = async () => {
    try {
      // 获取API配置状态
      const configRes = await api.getConfig()
      apiConfig.value = {
        deepseek: configRes.has_deepseek,
        qwen: configRes.has_qwen
      }
      
      // 获取可用模型
      await loadModels()
      
      // 获取MCP服务器列表
      await loadServers()
      
      // 获取MCP工具列表
      await loadTools()
    } catch (error) {
      console.error('初始化失败:', error)
    }
  }
  
  // 加载模型列表
  const loadModels = async () => {
    try {
      const res = await api.getModels()
      availableModels.value = res.models
    } catch (error) {
      console.error('加载模型失败:', error)
    }
  }
  
  // 加载MCP服务器
  const loadServers = async () => {
    try {
      const res = await api.getServers()
      mcpServers.value = res.servers
    } catch (error) {
      console.error('加载服务器失败:', error)
    }
  }
  
  // 加载MCP工具
  const loadTools = async () => {
    try {
      const res = await api.getTools()
      mcpTools.value = res.tools
    } catch (error) {
      console.error('加载工具失败:', error)
    }
  }
  
  // 更新API密钥
  const updateApiKey = async (provider, apiKey) => {
    try {
      await api.updateApiKey(provider, apiKey)
      apiConfig.value[provider] = true
      await loadModels()
      return true
    } catch (error) {
      console.error('更新API密钥失败:', error)
      return false
    }
  }
  
  // 添加MCP服务器
  const addServer = async (serverData) => {
    try {
      await api.addServer(serverData)
      await loadServers()
      await loadTools()
      return { success: true }
    } catch (error) {
      console.error('添加服务器失败:', error)
      // 提取后端返回的错误详情
      const errorDetail = error.response?.data?.detail || error.message || '未知错误'
      return { success: false, error: errorDetail }
    }
  }
  
  // 更新MCP服务器
  const updateServer = async (serverId, updateData) => {
    try {
      await api.updateServer(serverId, updateData)
      await loadServers()
      await loadTools()
      return true
    } catch (error) {
      console.error('更新服务器失败:', error)
      return false
    }
  }
  
  // 启用MCP服务器
  const enableServer = async (serverId) => {
    try {
      await api.enableServer(serverId)
      await loadServers()
      await loadTools()
      return true
    } catch (error) {
      console.error('启用服务器失败:', error)
      return false
    }
  }
  
  // 禁用MCP服务器
  const disableServer = async (serverId) => {
    try {
      await api.disableServer(serverId)
      await loadServers()
      await loadTools()
      return true
    } catch (error) {
      console.error('禁用服务器失败:', error)
      return false
    }
  }
  
  // 重启MCP服务器
  const restartServer = async (serverId) => {
    try {
      await api.restartServer(serverId)
      await loadServers()
      await loadTools()
      return true
    } catch (error) {
      console.error('重启服务器失败:', error)
      return false
    }
  }
  
  // 删除MCP服务器
  const removeServer = async (serverId) => {
    try {
      await api.deleteServer(serverId)
      await loadServers()
      await loadTools()
      return true
    } catch (error) {
      console.error('删除服务器失败:', error)
      return false
    }
  }
  
  // 聊天相关方法
  const addMessage = (message) => {
    chatMessages.value.push(message)
  }
  
  const clearMessages = () => {
    chatMessages.value = []
  }
  
  const updateChatConfig = (config) => {
    chatConfig.value = { ...chatConfig.value, ...config }
  }
  
  return {
    apiConfig,
    availableModels,
    mcpServers,
    mcpTools,
    chatMessages,
    chatConfig,
    init,
    loadModels,
    loadServers,
    loadTools,
    updateApiKey,
    addServer,
    updateServer,
    enableServer,
    disableServer,
    restartServer,
    removeServer,
    addMessage,
    clearMessages,
    updateChatConfig
  }
})

