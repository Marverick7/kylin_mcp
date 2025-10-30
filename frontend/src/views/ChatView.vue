<template>
  <div class="chat-view">
    <!-- 顶部工具栏 -->
    <div class="chat-header">
      <div class="header-left">
        <h2 class="chat-title">AI 对话</h2>
        <el-tag v-if="selectedModel" type="success" size="small">
          {{ selectedProvider }} / {{ selectedModel }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-tooltip content="工具数量">
          <el-tag type="info" size="small">
            <el-icon><Tools /></el-icon>
            {{ toolCount }} 个工具
          </el-tag>
        </el-tooltip>
        <el-button @click="showModelSelector = true" type="primary" size="small">
          <el-icon><Grid /></el-icon>
          选择模型
        </el-button>
        <el-button @click="clearChat" size="small">
          <el-icon><Delete /></el-icon>
          清空对话
        </el-button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="messages-container" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <el-icon class="empty-icon"><ChatDotRound /></el-icon>
        <h3>开始新对话</h3>
        <p>选择一个模型，然后开始与AI对话</p>
      </div>

      <div v-for="(msg, index) in messages" :key="index" class="message-wrapper">
        <div :class="['message-bubble', msg.role]">
          <div class="message-header">
            <span class="message-role">{{ getRoleName(msg.role) }}</span>
            <span class="message-time">{{ msg.time }}</span>
          </div>
          <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
          
          <!-- 工具调用显示 -->
          <div v-if="msg.tool_calls && msg.tool_calls.length > 0" class="tool-calls">
            <div v-for="(call, idx) in msg.tool_calls" :key="idx" class="tool-call">
              <div class="tool-call-header">
                <el-icon><Tools /></el-icon>
                <span class="tool-name">{{ call.function.name }}</span>
                <el-tag v-if="call.result" :type="call.result.error ? 'danger' : 'success'" size="small">
                  {{ call.result.error ? '失败' : '成功' }}
                </el-tag>
              </div>
              <div v-if="call.result" class="tool-result">
                <pre>{{ formatToolResult(call.result) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载指示器 -->
      <div v-if="isLoading" class="message-wrapper">
        <div class="message-bubble assistant">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-container">
      <el-input
        v-model="userInput"
        type="textarea"
        :rows="3"
        placeholder="输入消息... (Ctrl+Enter 发送)"
        @keydown.ctrl.enter="sendMessage"
        :disabled="!selectedModel || isLoading"
      />
      <el-button
        type="primary"
        class="send-button gradient-button"
        @click="sendMessage"
        :disabled="!userInput.trim() || !selectedModel || isLoading"
        :loading="isLoading"
      >
        <el-icon><Promotion /></el-icon>
        发送
      </el-button>
    </div>

    <!-- 模型选择对话框 -->
    <el-dialog v-model="showModelSelector" title="选择模型" width="500px">
      <el-form label-width="80px">
        <el-form-item label="提供商">
          <el-select v-model="selectedProvider" placeholder="选择提供商" @change="onProviderChange">
            <el-option
              v-for="provider in availableProviders"
              :key="provider"
              :label="getProviderName(provider)"
              :value="provider"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模型">
          <el-select v-model="selectedModel" placeholder="选择模型">
            <el-option
              v-for="model in currentModels"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="使用工具">
          <el-switch v-model="useMcpTools" />
          <span class="form-hint">启用MCP工具调用</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showModelSelector = false">取消</el-button>
        <el-button type="primary" @click="confirmModelSelection">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, reactive } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  Promotion,
  Delete,
  Grid,
  Tools
} from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/atom-one-dark.css'

const appStore = useAppStore()

// 使用 store 中的聊天状态
const messages = computed({
  get: () => appStore.chatMessages,
  set: (val) => {
    appStore.chatMessages = val
  }
})

const userInput = ref('')
const isLoading = ref(false)
const messagesContainer = ref(null)

const showModelSelector = ref(false)
const selectedProvider = computed({
  get: () => appStore.chatConfig.provider,
  set: (val) => appStore.updateChatConfig({ provider: val })
})
const selectedModel = computed({
  get: () => appStore.chatConfig.model,
  set: (val) => appStore.updateChatConfig({ model: val })
})
const useMcpTools = computed({
  get: () => appStore.chatConfig.useMcpTools,
  set: (val) => appStore.updateChatConfig({ useMcpTools: val })
})

const md = new MarkdownIt({
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch (__) {}
    }
    return ''
  }
})

const availableProviders = computed(() => {
  return Object.keys(appStore.availableModels)
})

const currentModels = computed(() => {
  return appStore.availableModels[selectedProvider.value] || []
})

const toolCount = computed(() => {
  return appStore.mcpTools.length
})

const getRoleName = (role) => {
  const names = {
    user: '我',
    assistant: 'AI',
    system: '系统',
    tool: '工具'
  }
  return names[role] || role
}

const getProviderName = (provider) => {
  const names = {
    deepseek: 'DeepSeek',
    qwen: '通义千问'
  }
  return names[provider] || provider
}

const renderMarkdown = (content) => {
  return md.render(content || '')
}

const formatToolResult = (result) => {
  return JSON.stringify(result, null, 2)
}

const onProviderChange = () => {
  selectedModel.value = ''
}

const confirmModelSelection = () => {
  if (!selectedProvider.value || !selectedModel.value) {
    ElMessage.warning('请选择提供商和模型')
    return
  }
  showModelSelector.value = false
  ElMessage.success(`已选择: ${getProviderName(selectedProvider.value)} / ${selectedModel.value}`)
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  if (!userInput.value.trim() || !selectedModel.value || isLoading.value) {
    return
  }

  const content = userInput.value.trim()
  userInput.value = ''

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: content,
    time: new Date().toLocaleTimeString()
  })

  scrollToBottom()
  isLoading.value = true

  try {
    // 通过WebSocket发送消息
    await sendMessageViaWebSocket(content)
  } catch (error) {
    ElMessage.error('发送消息失败: ' + error.message)
    isLoading.value = false
  }
}

const sendMessageViaWebSocket = (content) => {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket('ws://127.0.0.1:8765/ws/chat')
    let assistantMessage = null
    let messageInList = false
    let currentMessageIndex = -1

    // 创建新的助手消息（使用reactive使其响应式）
    const createAssistantMessage = () => {
      return reactive({
        role: 'assistant',
        content: '',
        time: new Date().toLocaleTimeString(),
        tool_calls: [],
        is_final: false
      })
    }

    ws.onopen = () => {
      // 构建消息历史
      const messageHistory = messages.value.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      ws.send(JSON.stringify({
        provider: selectedProvider.value,
        model: selectedModel.value,
        messages: messageHistory,
        use_mcp_tools: useMcpTools.value
      }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'content') {
          // 如果是新一轮对话或第一次接收内容，创建新消息
          if (!assistantMessage || assistantMessage.is_final) {
            assistantMessage = createAssistantMessage()
            messageInList = false
          }
          
          // 累积内容
          assistantMessage.content += data.content
          
          // 更新或添加助手消息到UI
          if (!messageInList) {
            messages.value.push(assistantMessage)
            currentMessageIndex = messages.value.length - 1
            messageInList = true
          }
          
          // 立即滚动到底部以显示新内容
          scrollToBottom()
        } else if (data.type === 'tool_call') {
          // 确保有当前消息对象
          if (!assistantMessage || assistantMessage.is_final) {
            assistantMessage = createAssistantMessage()
            messageInList = false
          }
          
          // 添加工具调用
          assistantMessage.tool_calls.push(data.tool_call)
          
          // 确保消息已添加到列表
          if (!messageInList) {
            messages.value.push(assistantMessage)
            messageInList = true
          }
          scrollToBottom()
        } else if (data.type === 'tool_result') {
          // 找到对应的工具调用并添加结果
          if (assistantMessage) {
            const toolCall = assistantMessage.tool_calls.find(
              tc => tc.id === data.tool_call_id
            )
            if (toolCall) {
              toolCall.result = data.result
            }
            
            // 标记当前消息为最终状态，下次内容会创建新消息
            assistantMessage.is_final = true
          }
          scrollToBottom()
        } else if (data.type === 'done') {
          // 标记消息为最终状态
          if (assistantMessage && !assistantMessage.is_final) {
            assistantMessage.is_final = true
          }
          ws.close()
          isLoading.value = false
          resolve()
        } else if (data.type === 'error') {
          ElMessage.error('错误: ' + data.error)
          ws.close()
          isLoading.value = false
          reject(new Error(data.error))
        }
      } catch (e) {
        console.error('解析消息失败:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      ElMessage.error('连接错误')
      isLoading.value = false
      reject(error)
    }

    ws.onclose = () => {
      isLoading.value = false
    }
  })
}

const clearChat = () => {
  appStore.clearMessages()
  ElMessage.success('对话已清空')
}

onMounted(() => {
  // 如果还没有选择提供商和模型，默认选择第一个可用的
  if (!selectedProvider.value || !selectedModel.value) {
    const providers = availableProviders.value
    if (providers.length > 0) {
      selectedProvider.value = providers[0]
      const models = appStore.availableModels[selectedProvider.value]
      if (models && models.length > 0) {
        selectedModel.value = models[0]
      }
    }
  }
})
</script>

<style scoped>
.chat-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-header {
  padding: 20px 30px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 30px;
  background: #f5f7fa;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #909399;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h3 {
  margin: 0 0 12px 0;
  font-size: 20px;
  color: #606266;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.message-wrapper {
  display: flex;
  margin-bottom: 16px;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
}

.message-role {
  font-weight: 600;
}

.message-time {
  opacity: 0.7;
}

.message-content {
  line-height: 1.6;
}

.tool-calls {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.tool-call {
  padding: 10px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.tool-call-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.tool-name {
  font-weight: 600;
  flex: 1;
  color: #409eff;
}

.tool-result {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.tool-result pre {
  margin: 0;
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.input-container {
  padding: 20px 30px;
  background: white;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-container :deep(.el-textarea__inner) {
  resize: none;
  font-size: 14px;
}

.send-button {
  height: 40px;
  padding: 0 24px;
}

.form-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}
</style>

