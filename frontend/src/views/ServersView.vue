<template>
  <div class="servers-view">
    <!-- 头部 -->
    <div class="view-header">
      <div class="header-left">
        <h2 class="view-title">MCP 服务管理</h2>
        <el-tag type="info" size="small">{{ servers.length }} 个服务</el-tag>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加服务
        </el-button>
      </div>
    </div>

    <!-- 服务列表 -->
    <div class="servers-container">
      <div v-if="servers.length === 0" class="empty-state">
        <el-icon class="empty-icon"><Connection /></el-icon>
        <h3>暂无MCP服务</h3>
        <p>点击"添加服务"按钮添加本地或远程MCP服务</p>
      </div>

      <el-row :gutter="20">
        <el-col
          v-for="server in servers"
          :key="server.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <el-card class="server-card hover-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <div class="server-name">
                  <el-icon><Connection /></el-icon>
                  <span>{{ server.name }}</span>
                </div>
                <el-dropdown @command="(cmd) => handleServerAction(cmd, server)">
                  <el-icon class="more-icon"><MoreFilled /></el-icon>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">
                        <el-icon><Edit /></el-icon>
                        编辑
                      </el-dropdown-item>
                      <el-dropdown-item command="toggle" v-if="server.enabled">
                        <el-icon><VideoPause /></el-icon>
                        停止
                      </el-dropdown-item>
                      <el-dropdown-item command="toggle" v-else>
                        <el-icon><VideoPlay /></el-icon>
                        启用
                      </el-dropdown-item>
                      <el-dropdown-item command="restart" v-if="server.enabled">
                        <el-icon><RefreshRight /></el-icon>
                        重启
                      </el-dropdown-item>
                      <el-dropdown-item command="delete" divided>
                        <el-icon><Delete /></el-icon>
                        删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>

            <div class="server-info">
              <div class="info-item">
                <span class="info-label">类型:</span>
                <el-tag :type="server.type === 'remote' ? 'success' : 'info'" size="small">
                  {{ server.type === 'remote' ? '远程' : '本地' }}
                </el-tag>
              </div>
              
              <div class="info-item" v-if="server.type === 'remote'">
                <span class="info-label">地址:</span>
                <span class="info-value">{{ server.config.url }}</span>
              </div>
              
              <div class="info-item" v-else>
                <span class="info-label">命令:</span>
                <span class="info-value">{{ formatCommand(server.config.command) }}</span>
              </div>

              <div class="info-item">
                <span class="info-label">状态:</span>
                <el-tag :type="server.enabled ? 'success' : 'danger'" size="small">
                  {{ server.enabled ? '已启用' : '已禁用' }}
                </el-tag>
              </div>

              <div class="info-item" v-if="server.type === 'local'">
                <span class="info-label">连接:</span>
                <el-tag :type="server.connected ? 'success' : 'danger'" size="small">
                  {{ server.connected ? '已连接' : '未连接' }}
                </el-tag>
              </div>

              <div class="info-item">
                <span class="info-label">工具数:</span>
                <el-tag type="info" size="small">
                  {{ server.tool_count || getServerToolCount(server.id) }}
                </el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 编辑服务对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑MCP服务"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="editServer" label-width="100px">
        <el-form-item label="服务名称" required>
          <el-input v-model="editServer.name" placeholder="例如: 天气服务" />
        </el-form-item>

        <el-form-item label="服务类型">
          <el-tag :type="editServer.type === 'remote' ? 'success' : 'info'" size="small">
            {{ editServer.type === 'remote' ? '远程' : '本地' }}
          </el-tag>
          <div class="form-hint">服务类型不可修改</div>
        </el-form-item>

        <!-- 远程服务配置 -->
        <template v-if="editServer.type === 'remote'">
          <el-form-item label="服务地址" required>
            <el-input
              v-model="editServer.url"
              placeholder="http://localhost:3000"
            />
          </el-form-item>
        </template>

        <!-- 本地服务配置 -->
        <template v-else>
          <el-form-item label="启动命令" required>
            <el-input
              v-model="editServer.command"
              placeholder="python backend/test_mcp_server.py"
            />
            <div class="form-hint">命令将自动按空格分割为数组</div>
          </el-form-item>
          <el-form-item label="工作目录">
            <el-input
              v-model="editServer.cwd"
              placeholder="可选，默认为项目根目录"
            />
          </el-form-item>
          <el-form-item label="环境变量">
            <el-input
              v-model="editServer.env"
              type="textarea"
              :rows="3"
              placeholder='{"KEY": "value"}'
            />
            <div class="form-hint">JSON 格式的环境变量</div>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateServer" :loading="updating">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加服务对话框 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加MCP服务"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="newServer" label-width="100px">
        <el-form-item label="服务名称" required>
          <el-input v-model="newServer.name" placeholder="例如: 天气服务" />
        </el-form-item>

        <el-form-item label="服务类型" required>
          <el-radio-group v-model="newServer.type">
            <el-radio label="remote">远程服务</el-radio>
            <el-radio label="local">本地服务</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 远程服务配置 -->
        <template v-if="newServer.type === 'remote'">
          <el-form-item label="服务地址" required>
            <el-input
              v-model="newServer.url"
              placeholder="http://localhost:3000"
            />
          </el-form-item>
        </template>

        <!-- 本地服务配置 -->
        <template v-else>
          <el-form-item label="启动命令" required>
            <el-input
              v-model="newServer.command"
              placeholder="python backend/test_mcp_server.py"
            />
            <div class="form-hint">命令将自动按空格分割为数组</div>
          </el-form-item>
          <el-form-item label="工作目录">
            <el-input
              v-model="newServer.cwd"
              placeholder="可选，默认为项目根目录"
            />
          </el-form-item>
          <el-form-item label="环境变量">
            <el-input
              v-model="newServer.env"
              type="textarea"
              :rows="3"
              placeholder='{"KEY": "value"}'
            />
            <div class="form-hint">JSON 格式的环境变量</div>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addServer" :loading="adding">
          添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Connection,
  Plus,
  Delete,
  MoreFilled,
  Edit,
  VideoPause,
  VideoPlay,
  RefreshRight
} from '@element-plus/icons-vue'

const appStore = useAppStore()

const showAddDialog = ref(false)
const adding = ref(false)
const newServer = ref({
  name: '',
  type: 'remote',
  url: '',
  command: '',
  cwd: '',
  env: ''
})

const showEditDialog = ref(false)
const updating = ref(false)
const editServer = ref({
  id: '',
  name: '',
  type: 'remote',
  url: '',
  command: '',
  cwd: '',
  env: ''
})

const servers = computed(() => appStore.mcpServers)

const getServerToolCount = (serverId) => {
  return appStore.mcpTools.filter(tool => tool.server_id === serverId).length
}

const formatCommand = (command) => {
  if (Array.isArray(command)) {
    return command.join(' ')
  }
  return command || ''
}

const resetNewServer = () => {
  newServer.value = {
    name: '',
    type: 'remote',
    url: '',
    command: '',
    cwd: '',
    env: ''
  }
}

const addServer = async () => {
  if (!newServer.value.name) {
    ElMessage.warning('请输入服务名称')
    return
  }

  if (newServer.value.type === 'remote' && !newServer.value.url) {
    ElMessage.warning('请输入服务地址')
    return
  }

  if (newServer.value.type === 'local' && !newServer.value.command) {
    ElMessage.warning('请输入启动命令')
    return
  }

  adding.value = true

  try {
    const config = {}
    
    if (newServer.value.type === 'remote') {
      config.url = newServer.value.url
    } else {
      // 将命令字符串转换为数组
      const commandStr = newServer.value.command.trim()
      config.command = commandStr.split(/\s+/).filter(s => s.length > 0)
      
      if (newServer.value.cwd) {
        config.cwd = newServer.value.cwd
      }
      if (newServer.value.env) {
        try {
          config.env = JSON.parse(newServer.value.env)
        } catch (e) {
          ElMessage.warning('环境变量格式错误，请使用 JSON 格式')
          adding.value = false
          return
        }
      }
    }

    const result = await appStore.addServer({
      name: newServer.value.name,
      type: newServer.value.type,
      config: config
    })

    if (result.success) {
      ElMessage.success('添加服务成功')
      showAddDialog.value = false
      resetNewServer()
    } else {
      ElMessage.error('添加服务失败: ' + result.error)
    }
  } catch (error) {
    ElMessage.error('添加服务失败: ' + error.message)
  } finally {
    adding.value = false
  }
}

const openEditDialog = (server) => {
  // 填充编辑表单
  editServer.value.id = server.id
  editServer.value.name = server.name
  editServer.value.type = server.type
  
  if (server.type === 'remote') {
    editServer.value.url = server.config.url || ''
  } else {
    editServer.value.command = formatCommand(server.config.command)
    editServer.value.cwd = server.config.cwd || ''
    editServer.value.env = server.config.env ? JSON.stringify(server.config.env, null, 2) : ''
  }
  
  showEditDialog.value = true
}

const updateServer = async () => {
  if (!editServer.value.name) {
    ElMessage.warning('请输入服务名称')
    return
  }

  updating.value = true

  try {
    const updateData = {
      name: editServer.value.name
    }
    
    // 构建新的config
    const config = {}
    if (editServer.value.type === 'remote') {
      if (!editServer.value.url) {
        ElMessage.warning('请输入服务地址')
        updating.value = false
        return
      }
      config.url = editServer.value.url
    } else {
      if (!editServer.value.command) {
        ElMessage.warning('请输入启动命令')
        updating.value = false
        return
      }
      // 将命令字符串转换为数组
      const commandStr = editServer.value.command.trim()
      config.command = commandStr.split(/\s+/).filter(s => s.length > 0)
      
      if (editServer.value.cwd) {
        config.cwd = editServer.value.cwd
      }
      if (editServer.value.env) {
        try {
          config.env = JSON.parse(editServer.value.env)
        } catch (e) {
          ElMessage.warning('环境变量格式错误，请使用 JSON 格式')
          updating.value = false
          return
        }
      }
    }
    
    updateData.config = config

    const success = await appStore.updateServer(editServer.value.id, updateData)
    if (success) {
      ElMessage.success('更新成功')
      showEditDialog.value = false
    } else {
      ElMessage.error('更新失败')
    }
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    updating.value = false
  }
}

const handleServerAction = async (command, server) => {
  if (command === 'edit') {
    openEditDialog(server)
  } else if (command === 'toggle') {
    // 启用/禁用
    try {
      const action = server.enabled ? '停止' : '启用'
      const success = server.enabled 
        ? await appStore.disableServer(server.id)
        : await appStore.enableServer(server.id)
      
      if (success) {
        ElMessage.success(`${action}成功`)
      } else {
        ElMessage.error(`${action}失败`)
      }
    } catch (error) {
      ElMessage.error('操作失败: ' + error.message)
    }
  } else if (command === 'restart') {
    try {
      const success = await appStore.restartServer(server.id)
      if (success) {
        ElMessage.success('重启成功')
      } else {
        ElMessage.error('重启失败')
      }
    } catch (error) {
      ElMessage.error('重启失败: ' + error.message)
    }
  } else if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除服务 "${server.name}" 吗？`,
        '确认删除',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )

      const success = await appStore.removeServer(server.id)
      if (success) {
        ElMessage.success('删除成功')
      } else {
        ElMessage.error('删除失败')
      }
    } catch (error) {
      // 用户取消
    }
  }
}

onMounted(() => {
  appStore.loadServers()
})
</script>

<style scoped>
.servers-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.view-header {
  padding: 20px 30px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.view-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.servers-container {
  flex: 1;
  overflow-y: auto;
  padding: 30px;
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

.server-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.server-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

.more-icon {
  cursor: pointer;
  font-size: 18px;
  color: #909399;
}

.more-icon:hover {
  color: #606266;
}

.server-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
}

.info-label {
  color: #909399;
  font-weight: 500;
}

.info-value {
  color: #606266;
  font-family: monospace;
  font-size: 12px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>

