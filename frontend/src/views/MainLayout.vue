<template>
  <el-container class="main-layout">
    <!-- 左侧导航栏 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo-section">
        <h1 class="logo-title">
          <el-icon class="logo-icon"><ChatDotRound /></el-icon>
          Kylin MCP
        </h1>
        <p class="logo-subtitle">AI Client</p>
      </div>
      
      <el-menu
        :default-active="currentRoute"
        class="sidebar-menu"
        background-color="transparent"
        text-color="#fff"
        active-text-color="#fff"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话</span>
        </el-menu-item>
        <el-menu-item index="/servers">
          <el-icon><Connection /></el-icon>
          <span>MCP服务</span>
          <el-badge :value="serverCount" class="server-badge" v-if="serverCount > 0" />
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <div class="status-indicator">
          <span :class="['status-dot', backendStatus ? 'online' : 'offline']"></span>
          <span class="status-text">{{ backendStatus ? '后端已连接' : '后端未连接' }}</span>
        </div>
      </div>
    </el-aside>
    
    <!-- 主内容区域 -->
    <el-main class="main-content">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import { ChatDotRound, Connection, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const currentRoute = computed(() => route.path)
const serverCount = computed(() => appStore.mcpServers.length)
const backendStatus = ref(false)
const isFirstCheck = ref(true)

let healthCheckInterval = null

const handleMenuSelect = (index) => {
  router.push(index)
}

// 检查后端连接状态
const checkBackendHealth = async () => {
  try {
    await api.getConfig()
    const wasOffline = backendStatus.value === false && !isFirstCheck.value
    backendStatus.value = true
    
    // 如果后端从离线变为在线，重新加载数据（排除首次检查）
    if (wasOffline) {
      console.log('后端已重新连接，正在重新加载数据...')
      await appStore.init()
      ElMessage.success('后端已重新连接，数据已更新')
    }
    
    isFirstCheck.value = false
  } catch (error) {
    backendStatus.value = false
    isFirstCheck.value = false
  }
}

onMounted(() => {
  checkBackendHealth()
  // 每5秒检查一次后端状态
  healthCheckInterval = setInterval(checkBackendHealth, 5000)
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
})
</script>

<style scoped>
.main-layout {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

.logo-section {
  padding: 30px 20px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.logo-icon {
  font-size: 28px;
}

.logo-subtitle {
  margin: 8px 0 0 0;
  font-size: 12px;
  opacity: 0.8;
  letter-spacing: 2px;
}

.sidebar-menu {
  flex: 1;
  border: none;
  padding: 20px 10px;
}

.sidebar-menu .el-menu-item {
  border-radius: 8px;
  margin-bottom: 8px;
  height: 48px;
  line-height: 48px;
  transition: all 0.3s ease;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.sidebar-menu .el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.2);
  font-weight: 600;
}

.server-badge {
  margin-left: 8px;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot.online {
  background: #4caf50;
}

.status-dot.offline {
  background: #f44336;
}

.status-text {
  opacity: 0.9;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.main-content {
  padding: 0;
  background: #f5f7fa;
  overflow: hidden;
}
</style>

