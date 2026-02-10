<template>
  <div class="dashboard">
    <!-- 数据卡片 -->
    <el-row :gutter="20" class="overview-cards">
      <el-col :span="4" v-for="item in overviewCards" :key="item.title">
        <el-card shadow="hover">
          <div class="card-content">
            <div class="card-title">{{ item.title }}</div>
            <div class="card-value" :style="{ color: item.color }">{{ item.value }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>近7天收入趋势</span>
          </template>
          <div ref="incomeChart" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>容器状态分布</span>
          </template>
          <div ref="statusChart" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 今日统计 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>今日统计</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="6" v-for="item in todayStats" :key="item.label">
              <div class="stat-item">
                <div class="stat-label">{{ item.label }}</div>
                <div class="stat-value">{{ item.value }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { getDashboard } from '@/api'

const incomeChart = ref()
const statusChart = ref()
let incomeChartInstance = null
let statusChartInstance = null

const dashboardData = ref({
  overview: {},
  statistics: {},
  charts: { income_trend: [], container_status: {} }
})

const overviewCards = computed(() => [
  { title: '我的用户', value: dashboardData.value.overview.total_users || 0, color: '#409EFF' },
  { title: '我的容器', value: dashboardData.value.overview.total_containers || 0, color: '#67C23A' },
  { title: '运行中', value: dashboardData.value.overview.running_containers || 0, color: '#E6A23C' },
  { title: '已停止', value: dashboardData.value.overview.stopped_containers || 0, color: '#909399' },
  { title: '我的余额', value: `¥${(dashboardData.value.overview.total_balance || 0).toFixed(2)}`, color: '#F56C6C' },
  { title: '今日收入', value: `¥${(dashboardData.value.overview.today_income || 0).toFixed(2)}`, color: '#409EFF' }
])

const todayStats = computed(() => [
  { label: '今日新用户', value: dashboardData.value.statistics.today_new_users || 0 },
  { label: '今日新容器', value: dashboardData.value.statistics.today_new_containers || 0 },
  { label: '今日运行分钟', value: dashboardData.value.statistics.today_running_minutes || 0 },
  { label: '今日收入', value: `¥${(dashboardData.value.statistics.today_income || 0).toFixed(2)}` }
])

const initCharts = () => {
  // 收入趋势图
  incomeChartInstance = echarts.init(incomeChart.value)
  const incomeData = dashboardData.value.charts.income_trend || []
  incomeChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: incomeData.map(item => item.date)
    },
    yAxis: { type: 'value', name: '收入(元)' },
    series: [{
      data: incomeData.map(item => item.amount),
      type: 'line',
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      }
    }]
  })

  // 状态分布饼图
  statusChartInstance = echarts.init(statusChart.value)
  const statusData = dashboardData.value.charts.container_status || {}
  statusChartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: { show: false },
      data: [
        { value: statusData.running || 0, name: '运行中', itemStyle: { color: '#67C23A' } },
        { value: statusData.stopped || 0, name: '已停止', itemStyle: { color: '#909399' } }
      ]
    }]
  })
}

const fetchData = async () => {
  const res = await getDashboard()
  if (res.code === 200) {
    dashboardData.value = res.data
    initCharts()
  }
}

onMounted(() => {
  fetchData()
  window.addEventListener('resize', () => {
    incomeChartInstance?.resize()
    statusChartInstance?.resize()
  })
})

onUnmounted(() => {
  incomeChartInstance?.dispose()
  statusChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.overview-cards {
  margin-bottom: 20px;
}

.card-content {
  text-align: center;
}

.card-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.card-value {
  font-size: 24px;
  font-weight: bold;
}

.charts-row {
  margin-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
}
</style>
