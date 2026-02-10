<template>
  <div class="logs-page">
    <el-card>
      <template #header>
        <div class="header-actions">
          <span>容器操作日志</span>
          <div class="filter-actions">
            <el-select 
              v-model="filterUser" 
              placeholder="选择用户" 
              clearable 
              filterable
              style="width: 160px; margin-right: 10px;"
            >
              <el-option 
                v-for="user in userList" 
                :key="user.id" 
                :label="user.company_name" 
                :value="user.id" 
              />
            </el-select>
            <el-select 
              v-if="isSuperAdmin"
              v-model="filterAdmin" 
              placeholder="归属管理员" 
              clearable 
              filterable
              style="width: 160px; margin-right: 10px;"
            >
              <el-option 
                v-for="admin in adminList" 
                :key="admin.id" 
                :label="admin.username" 
                :value="admin.id" 
              />
            </el-select>
            <el-select v-model="filterAction" placeholder="操作类型" clearable style="width: 120px; margin-right: 10px;">
              <el-option label="创建" value="create" />
              <el-option label="启动" value="start" />
              <el-option label="停止" value="stop" />
              <el-option label="删除" value="delete" />
              <el-option label="自动停止" value="auto_stop" />
            </el-select>
            <el-button type="primary" @click="handleQuery">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </div>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="user_name" label="用户" min-width="120" />
        <el-table-column prop="admin_name" label="归属管理员" min-width="120" />
        <el-table-column prop="action" label="操作" width="100">
          <template #default="{ row }">
            <el-tag :type="getActionType(row.action)">{{ getActionText(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action_status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.action_status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.action_status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="启动时间" width="170">
          <template #default="{ row }">
            {{ row.started_at ? formatDateTime(row.started_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="stopped_at" label="停止时间" width="170">
          <template #default="{ row }">
            {{ row.stopped_at ? formatDateTime(row.stopped_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_minutes" label="使用时长" width="100">
          <template #default="{ row }">
            <span v-if="row.duration_minutes">{{ row.duration_minutes }} 分钟</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="费用(元)" width="100">
          <template #default="{ row }">
            <span v-if="row.cost" class="cost-value">¥{{ row.cost.toFixed(2) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        <el-table-column prop="created_at" label="记录时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next"
        @change="fetchLogs"
        class="pagination"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getContainerLogs, getUserList, getAdminList } from '@/api/index'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()
const loading = ref(false)
const logs = ref([])
const filterAction = ref('')
const filterUser = ref('')
const filterAdmin = ref('')
const userList = ref([])
const adminList = ref([])

const isSuperAdmin = computed(() => adminStore.role === 'super_admin')

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const getActionType = (action) => {
  const map = {
    create: 'primary',
    start: 'success',
    stop: 'warning',
    delete: 'danger',
    auto_stop: 'info'
  }
  return map[action] || 'info'
}

const getActionText = (action) => {
  const map = {
    create: '创建',
    start: '启动',
    stop: '停止',
    delete: '删除',
    auto_stop: '自动停止'
  }
  return map[action] || action
}

const formatDateTime = (datetime) => {
  if (!datetime) return '-'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    if (filterAction.value) {
      params.action = filterAction.value
    }
    if (filterUser.value) {
      params.user_id = filterUser.value
    }
    if (isSuperAdmin.value && filterAdmin.value) {
      params.admin_id = filterAdmin.value
    }

    const res = await getContainerLogs(params)
    if (res.code === 200) {
      logs.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    loading.value = false
  }
}

const fetchUserList = async () => {
  try {
    const params = isSuperAdmin.value ? { page: 1, page_size: 1000 } : {}
    const res = await getUserList(params)
    if (res.code === 200) {
      userList.value = res.data.items || []
    }
  } catch (error) {
    console.error('获取用户列表失败', error)
  }
}

const fetchAdminList = async () => {
  if (!isSuperAdmin.value) return
  try {
    const res = await getAdminList({ page: 1, page_size: 1000 })
    if (res.code === 200) {
      adminList.value = res.data.items || []
    }
  } catch (error) {
    console.error('获取管理员列表失败', error)
  }
}

const handleQuery = () => {
  pagination.page = 1
  fetchLogs()
}

const handleReset = () => {
  filterAction.value = ''
  filterUser.value = ''
  filterAdmin.value = ''
  pagination.page = 1
  fetchLogs()
}

onMounted(() => {
  fetchUserList()
  fetchAdminList()
  fetchLogs()
})
</script>

<style scoped>
.logs-page {
  padding: 20px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-actions {
  display: flex;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

.cost-value {
  color: #F56C6C;
  font-weight: bold;
}
</style>
