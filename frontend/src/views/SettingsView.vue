<template>
  <div class="settings-view">
    <!-- 头部 -->
    <div class="view-header">
      <h2 class="view-title">设置</h2>
    </div>

    <!-- 设置内容 -->
    <div class="settings-container">
      <el-card class="settings-card" shadow="never">
        <template #header>
          <div class="card-title">
            <el-icon><Key /></el-icon>
            <span>API 密钥配置</span>
          </div>
        </template>

        <el-form label-width="120px">
          <!-- DeepSeek -->
          <el-form-item>
            <template #label>
              <div class="form-label">
                <span>DeepSeek</span>
                <el-tag
                  v-if="apiConfig.deepseek"
                  type="success"
                  size="small"
                  effect="plain"
                >
                  已配置
                </el-tag>
              </div>
            </template>
            <div class="api-key-input">
              <el-input
                v-model="apiKeys.deepseek"
                type="password"
                placeholder="sk-..."
                show-password
              />
              <el-button
                type="primary"
                @click="saveApiKey('deepseek')"
                :loading="saving === 'deepseek'"
              >
                保存
              </el-button>
            </div>
            <div class="form-hint">
              获取API密钥: <a href="https://platform.deepseek.com" target="_blank">https://platform.deepseek.com</a>
            </div>
          </el-form-item>

          <!-- Qwen -->
          <el-form-item>
            <template #label>
              <div class="form-label">
                <span>通义千问</span>
                <el-tag
                  v-if="apiConfig.qwen"
                  type="success"
                  size="small"
                  effect="plain"
                >
                  已配置
                </el-tag>
              </div>
            </template>
            <div class="api-key-input">
              <el-input
                v-model="apiKeys.qwen"
                type="password"
                placeholder="sk-..."
                show-password
              />
              <el-button
                type="primary"
                @click="saveApiKey('qwen')"
                :loading="saving === 'qwen'"
              >
                保存
              </el-button>
            </div>
            <div class="form-hint">
              获取API密钥: <a href="https://dashscope.console.aliyun.com" target="_blank">阿里云百炼</a>
            </div>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="settings-card" shadow="never">
        <template #header>
          <div class="card-title">
            <el-icon><InfoFilled /></el-icon>
            <span>关于</span>
          </div>
        </template>

        <div class="about-section">
          <div class="about-item">
            <span class="about-label">应用名称:</span>
            <span class="about-value">Kylin MCP Client</span>
          </div>
          <div class="about-item">
            <span class="about-label">版本:</span>
            <span class="about-value">1.0.0</span>
          </div>
          <div class="about-item">
            <span class="about-label">描述:</span>
            <span class="about-value">一个功能强大的MCP客户端应用</span>
          </div>
          <div class="about-item">
            <span class="about-label">技术栈:</span>
            <span class="about-value">Python + FastAPI + Electron + Vue.js</span>
          </div>
          <div class="about-item">
            <span class="about-label">许可证:</span>
            <span class="about-value">MIT</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'
import { Key, InfoFilled } from '@element-plus/icons-vue'

const appStore = useAppStore()

const apiKeys = ref({
  deepseek: '',
  qwen: ''
})

const saving = ref('')

const apiConfig = computed(() => appStore.apiConfig)

const saveApiKey = async (provider) => {
  const apiKey = apiKeys.value[provider]
  
  if (!apiKey || !apiKey.trim()) {
    ElMessage.warning('请输入API密钥')
    return
  }

  saving.value = provider

  try {
    const success = await appStore.updateApiKey(provider, apiKey.trim())
    
    if (success) {
      ElMessage.success('API密钥保存成功')
      apiKeys.value[provider] = ''
    } else {
      ElMessage.error('API密钥保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = ''
  }
}
</script>

<style scoped>
.settings-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.view-header {
  padding: 20px 30px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.view-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.settings-container {
  flex: 1;
  overflow-y: auto;
  padding: 30px;
}

.settings-card {
  margin-bottom: 20px;
  max-width: 800px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.api-key-input {
  display: flex;
  gap: 12px;
  width: 100%;
}

.api-key-input .el-input {
  flex: 1;
}

.form-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.form-hint a {
  color: #409eff;
  text-decoration: none;
}

.form-hint a:hover {
  text-decoration: underline;
}

.about-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.about-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.about-label {
  font-weight: 600;
  color: #606266;
  min-width: 120px;
}

.about-value {
  color: #303133;
}
</style>

