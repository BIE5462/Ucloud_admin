<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon size="28" color="#409EFF"><Monitor /></el-icon>
        <span class="logo-text">云电脑管理</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        router
        class="menu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <breadcrumb />
        </div>
        <div class="header-right">
          <span class="admin-name">{{ adminStore.adminInfo?.username }}</span>
          <el-tag v-if="adminStore.isSuperAdmin" type="danger" size="small">超级管理员</el-tag>
          <el-tag v-else type="info" size="small">管理员</el-tag>
          <el-button type="danger" size="small" @click="handleLogout" style="margin-left: 10px">
            退出
          </el-button>
        </div>
      </el-header>
      
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAdminStore } from '@/stores/admin'

const route = useRoute()
const router = useRouter()
const adminStore = useAdminStore()

const menuItems = computed(() => {
  const items = [
    { path: '/dashboard', title: '仪表盘', icon: 'Odometer' },
    { path: '/users', title: '用户管理', icon: 'User' },
  ]

  if (adminStore.isSuperAdmin) {
    items.push(
      { path: '/admins', title: '管理员管理', icon: 'UserFilled' },
      { path: '/logs', title: '日志中心', icon: 'Document' },
      { path: '/config', title: '系统配置', icon: 'Setting' }
    )
  } else {
    items.push(
      { path: '/logs', title: '日志中心', icon: 'Document' }
    )
  }

  return items
})

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    adminStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch {
    // 取消
  }
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.aside {
  background-color: #304156;
  color: #fff;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #1f2d3d;
}

.logo-text {
  margin-left: 10px;
  font-size: 18px;
  font-weight: bold;
  color: #fff;
}

.menu {
  border-right: none;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-name {
  font-weight: bold;
}

.main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
