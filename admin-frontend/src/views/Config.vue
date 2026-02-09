<template>
  <div class="config-page">
    <el-card>
      <template #header>
        <span>系统配置</span>
      </template>

      <el-form :model="config" label-width="180px" class="config-form">
        <el-form-item label="每分钟价格 (元)">
          <el-input-number 
            v-model="config.price_per_minute" 
            :min="0.01" 
            :precision="2" 
            :step="0.1"
            style="width: 200px"
          />
          <span class="form-tip">云电脑运行每分钟的价格</span>
        </el-form-item>

        <el-form-item label="启动最低余额 (元)">
          <el-input-number 
            v-model="config.min_balance_to_start" 
            :min="0" 
            :precision="2" 
            :step="0.5"
            style="width: 200px"
          />
          <span class="form-tip">启动云电脑所需的最低余额</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <div class="config-info">
        <h4>配置说明</h4>
        <ul>
          <li>价格更新只影响新创建的实例，已创建实例保持创建时的价格（价格快照机制）</li>
          <li>启动最低余额默认为5分钟费用，防止用户频繁启停</li>
          <li>所有价格变动都会被记录在系统日志中</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, updatePrice } from '@/api'

const config = ref({
  price_per_minute: 0.5,
  min_balance_to_start: 2.5,
  auto_stop_threshold: 0
})

const saving = ref(false)

const fetchConfig = async () => {
  const res = await getConfig()
  if (res.code === 200) {
    config.value = res.data
  }
}

const handleSave = async () => {
  if (config.value.price_per_minute <= 0) {
    ElMessage.warning('价格必须大于0')
    return
  }

  saving.value = true
  try {
    await updatePrice({ price_per_minute: config.value.price_per_minute })
    ElMessage.success('配置保存成功')
    fetchConfig()
  } finally {
    saving.value = false
  }
}

onMounted(fetchConfig)
</script>

<style scoped>
.config-page {
  padding: 20px;
}

.config-form {
  max-width: 600px;
}

.form-tip {
  margin-left: 15px;
  color: #666;
  font-size: 14px;
}

.config-info {
  margin-top: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.config-info h4 {
  margin-bottom: 15px;
  color: #333;
}

.config-info ul {
  padding-left: 20px;
  color: #666;
  line-height: 2;
}
</style>
