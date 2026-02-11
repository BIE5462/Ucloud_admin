<template>
  <div class="logs-page">
    <el-card>
      <template #header>
        <div class="header-actions">
          <el-tabs v-model="activeTab" @tab-change="handleTabChange">
            <el-tab-pane label="容器操作日志" name="container" />
            <el-tab-pane label="余额变化日志" name="balance" />
          </el-tabs>
        </div>
      </template>

      <div v-if="activeTab === 'container'">
        <div class="filter-actions">
          <el-select
            v-model="containerFilter.user_id"
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
            v-model="containerFilter.admin_id"
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
          <el-select v-model="containerFilter.action" placeholder="操作类型" clearable style="width: 120px; margin-right: 10px;">
            <el-option label="创建" value="create" />
            <el-option label="启动" value="start" />
            <el-option label="停止" value="stop" />
            <el-option label="删除" value="delete" />
            <el-option label="自动停止" value="auto_stop" />
          </el-select>
          <el-button type="primary" @click="handleContainerQuery">查询</el-button>
          <el-button @click="handleContainerReset">重置</el-button>
          <el-button type="success" @click="exportContainerLogs" style="margin-left: auto;">导出CSV</el-button>
        </div>

        <el-table :data="containerLogs" v-loading="containerLoading" border>
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
          v-model:current-page="containerPagination.page"
          v-model:page-size="containerPagination.page_size"
          :total="containerPagination.total"
          layout="total, sizes, prev, pager, next"
          @change="fetchContainerLogs"
          class="pagination"
        />
      </div>

      <div v-else>
        <div class="filter-actions">
          <el-select
            v-model="balanceFilter.account_type"
            placeholder="账户类型"
            clearable
            style="width: 120px; margin-right: 10px;"
          >
            <el-option label="管理员" value="admin" />
            <el-option label="用户" value="user" />
          </el-select>
          <el-select
            v-model="balanceFilter.change_type"
            placeholder="变动类型"
            clearable
            style="width: 120px; margin-right: 10px;"
          >
            <el-option label="充值" value="recharge" />
            <el-option label="扣费" value="deduct" />
            <el-option label="消费" value="consume" />
            <el-option label="退款" value="refund" />
          </el-select>
          <el-date-picker
            v-model="balanceFilter.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px; margin-right: 10px;"
          />
          <el-button type="primary" @click="handleBalanceQuery">查询</el-button>
          <el-button @click="handleBalanceReset">重置</el-button>
          <el-button type="success" @click="exportBalanceLogs" style="margin-left: auto;">导出CSV</el-button>
        </div>

        <el-table :data="balanceLogs" v-loading="balanceLoading" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="account_name" label="账户名称" min-width="120" />
          <el-table-column prop="account_type" label="账户类型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.account_type === 'admin' ? '管理员' : '用户' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="change_type" label="变动类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getBalanceChangeType(row.change_type)">{{ getBalanceChangeText(row.change_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="变动金额" width="120">
            <template #default="{ row }">
              <span :class="row.amount >= 0 ? 'income-value' : 'expense-value'">
                {{ row.amount >= 0 ? '+' : '' }}¥{{ row.amount.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="balance_before" label="变动前余额" width="120">
            <template #default="{ row }">
              ¥{{ row.balance_before.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="balance_after" label="变动后余额" width="120">
            <template #default="{ row }">
              ¥{{ row.balance_after.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="100">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ getSourceText(row.source) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="operator_name" label="操作人" width="120" />
          <el-table-column prop="remark" label="备注" min-width="150" />
          <el-table-column prop="created_at" label="时间" width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="balancePagination.page"
          v-model:page-size="balancePagination.page_size"
          :total="balancePagination.total"
          layout="total, sizes, prev, pager, next"
          @change="fetchBalanceLogs"
          class="pagination"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getContainerLogs, getBalanceLogs, getUserList, getAdminList } from '@/api/index'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

const activeTab = ref('container')

const isSuperAdmin = computed(() => adminStore.role === 'super_admin')

const containerLoading = ref(false)
const containerLogs = ref([])
const containerFilter = reactive({
  user_id: '',
  admin_id: '',
  action: ''
})
const containerPagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const balanceLoading = ref(false)
const balanceLogs = ref([])
const balanceFilter = reactive({
  account_type: '',
  change_type: '',
  dateRange: []
})
const balancePagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const userList = ref([])
const adminList = ref([])

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

const getBalanceChangeType = (type) => {
  const map = {
    recharge: 'success',
    deduct: 'danger',
    consume: 'warning',
    refund: 'primary'
  }
  return map[type] || 'info'
}

const getBalanceChangeText = (type) => {
  const map = {
    recharge: '充值',
    deduct: '扣费',
    consume: '消费',
    refund: '退款'
  }
  return map[type] || type
}

const getSourceText = (source) => {
  const map = {
    manual: '手动',
    system: '系统',
    auto: '自动'
  }
  return map[source] || source || '-'
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

const handleTabChange = (tab) => {
  if (tab === 'container' && containerLogs.value.length === 0) {
    fetchContainerLogs()
  } else if (tab === 'balance' && balanceLogs.value.length === 0) {
    fetchBalanceLogs()
  }
}

const fetchContainerLogs = async () => {
  containerLoading.value = true
  try {
    const params = {
      page: containerPagination.page,
      page_size: containerPagination.page_size
    }
    if (containerFilter.user_id) {
      params.user_id = containerFilter.user_id
    }
    if (isSuperAdmin.value && containerFilter.admin_id) {
      params.admin_id = containerFilter.admin_id
    }
    if (containerFilter.action) {
      params.action = containerFilter.action
    }

    const res = await getContainerLogs(params)
    if (res.code === 200) {
      containerLogs.value = res.data.items
      containerPagination.total = res.data.total
    }
  } catch (error) {
    ElMessage.error('获取容器日志失败')
  } finally {
    containerLoading.value = false
  }
}

const fetchBalanceLogs = async () => {
  balanceLoading.value = true
  try {
    const params = {
      page: balancePagination.page,
      page_size: balancePagination.page_size
    }
    if (balanceFilter.account_type) {
      params.account_type = balanceFilter.account_type
    }
    if (balanceFilter.change_type) {
      params.change_type = balanceFilter.change_type
    }
    if (balanceFilter.dateRange && balanceFilter.dateRange.length === 2) {
      params.start_date = balanceFilter.dateRange[0]
      params.end_date = balanceFilter.dateRange[1]
    }

    const res = await getBalanceLogs(params)
    if (res.code === 200) {
      balanceLogs.value = res.data.items
      balancePagination.total = res.data.total
    }
  } catch (error) {
    ElMessage.error('获取余额日志失败')
  } finally {
    balanceLoading.value = false
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

const handleContainerQuery = () => {
  containerPagination.page = 1
  fetchContainerLogs()
}

const handleContainerReset = () => {
  containerFilter.user_id = ''
  containerFilter.admin_id = ''
  containerFilter.action = ''
  containerPagination.page = 1
  fetchContainerLogs()
}

const handleBalanceQuery = () => {
  balancePagination.page = 1
  fetchBalanceLogs()
}

const handleBalanceReset = () => {
  balanceFilter.account_type = ''
  balanceFilter.change_type = ''
  balanceFilter.dateRange = []
  balancePagination.page = 1
  fetchBalanceLogs()
}

const formatDate = (date) => {
  if (!date) return ''
  const d = new Date(date)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const downloadCSV = (data, filename) => {
  if (!data || data.length === 0) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  const headers = Object.keys(data[0])
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(h => {
      const val = row[h]
      if (val === null || val === undefined) return ''
      const str = String(val)
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`
      }
      return str
    }).join(','))
  ].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
  ElMessage.success('导出成功')
}

const exportContainerLogs = async () => {
  containerLoading.value = true
  try {
    const params = { page: 1, page_size: containerPagination.total || 10000 }
    if (containerFilter.user_id) params.user_id = containerFilter.user_id
    if (isSuperAdmin.value && containerFilter.admin_id) params.admin_id = containerFilter.admin_id
    if (containerFilter.action) params.action = containerFilter.action
    const res = await getContainerLogs(params)
    if (res.code === 200 && res.data.items) {
      const exportData = res.data.items.map(item => ({
        ID: item.id,
        用户: item.user_name,
        归属管理员: item.admin_name,
        操作: getActionText(item.action),
        状态: item.action_status === 'success' ? '成功' : '失败',
        启动时间: item.started_at ? formatDate(item.started_at) : '-',
        停止时间: item.stopped_at ? formatDate(item.stopped_at) : '-',
        使用时长: item.duration_minutes ? `${item.duration_minutes} 分钟` : '-',
        费用: item.cost ? `¥${item.cost.toFixed(2)}` : '-',
        IP地址: item.ip_address || '-',
        记录时间: formatDate(item.created_at)
      }))
      downloadCSV(exportData, `容器操作日志_${new Date().toISOString().slice(0, 10)}.csv`)
    }
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    containerLoading.value = false
  }
}

const exportBalanceLogs = async () => {
  balanceLoading.value = true
  try {
    const params = { page: 1, page_size: balancePagination.total || 10000 }
    if (balanceFilter.account_type) params.account_type = balanceFilter.account_type
    if (balanceFilter.change_type) params.change_type = balanceFilter.change_type
    if (balanceFilter.dateRange && balanceFilter.dateRange.length === 2) {
      params.start_date = balanceFilter.dateRange[0]
      params.end_date = balanceFilter.dateRange[1]
    }
    const res = await getBalanceLogs(params)
    if (res.code === 200 && res.data.items) {
      const exportData = res.data.items.map(item => ({
        ID: item.id,
        账户名称: item.account_name,
        账户类型: item.account_type === 'admin' ? '管理员' : '用户',
        变动类型: getBalanceChangeText(item.change_type),
        变动金额: `¥${item.amount.toFixed(2)}`,
        变动前余额: `¥${item.balance_before.toFixed(2)}`,
        变动后余额: `¥${item.balance_after.toFixed(2)}`,
        来源: getSourceText(item.source),
        操作人: item.operator_name || '-',
        备注: item.remark || '-',
        时间: formatDate(item.created_at)
      }))
      downloadCSV(exportData, `余额变动日志_${new Date().toISOString().slice(0, 10)}.csv`)
    }
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    balanceLoading.value = false
  }
}

onMounted(() => {
  fetchUserList()
  fetchAdminList()
  fetchContainerLogs()
})
</script>

<style scoped>
.logs-page {
  padding: 20px;
}

.header-actions {
  width: 100%;
}

.filter-actions {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

.cost-value {
  color: #F56C6C;
  font-weight: bold;
}

.income-value {
  color: #67C23A;
  font-weight: bold;
}

.expense-value {
  color: #F56C6C;
  font-weight: bold;
}
</style>
