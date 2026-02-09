<template>
  <div class="logs-page">
    <el-card>
      <template #header>
        <span>日志中心</span>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="容器操作日志" name="container">
          <el-table :data="logs" v-loading="loading" border>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="user_name" label="用户" />
            <el-table-column prop="action" label="操作" width="120">
              <template #default="{ row }">
                <el-tag :type="getActionType(row.action)">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action_status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.action_status === 'success' ? 'success' : 'danger'">
                  {{ row.action_status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="ip_address" label="IP地址" />
            <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="180" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="余额变动日志" name="balance">
          <el-table :data="balanceLogs" v-loading="loading" border>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="user_name" label="用户" />
            <el-table-column prop="change_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.change_type === 'recharge' ? 'success' : 'danger'">
                  {{ row.change_type === 'recharge' ? '充值' : '扣费' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" width="120">
              <template #default="{ row }">
                <span :class="row.amount > 0 ? 'text-success' : 'text-danger'">
                  {{ row.amount > 0 ? '+' : '' }}{{ row.amount.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="balance_before" label="变动前" width="120">
              <template #default="{ row }">{{ row.balance_before.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="balance_after" label="变动后" width="120">
              <template #default="{ row }">{{ row.balance_after.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="operator_name" label="操作人" width="120" />
            <el-table-column prop="description" label="备注" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>

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
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('container')
const loading = ref(false)
const logs = ref([])
const balanceLogs = ref([])
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
    delete: 'danger'
  }
  return map[action] || 'info'
}

const fetchLogs = async () => {
  loading.value = true
  try {
    // 这里应该调用实际的API
    // 模拟数据
    if (activeTab.value === 'container') {
      logs.value = [
        { id: 1, user_name: 'ABC公司', action: 'start', action_status: 'success', ip_address: '192.168.1.1', created_at: '2026-02-09 10:00:00' },
        { id: 2, user_name: 'XYZ公司', action: 'stop', action_status: 'success', ip_address: '192.168.1.2', created_at: '2026-02-09 09:30:00' }
      ]
    } else {
      balanceLogs.value = [
        { id: 1, user_name: 'ABC公司', change_type: 'recharge', amount: 100, balance_before: 0, balance_after: 100, operator_name: 'admin', description: '充值', created_at: '2026-02-09 10:00:00' }
      ]
    }
    pagination.total = 2
  } finally {
    loading.value = false
  }
}

watch(activeTab, fetchLogs)
fetchLogs()
</script>

<style scoped>
.logs-page {
  padding: 20px;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

.text-success {
  color: #67C23A;
}

.text-danger {
  color: #F56C6C;
}
</style>
