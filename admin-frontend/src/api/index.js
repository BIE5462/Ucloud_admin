import axios from 'axios'
import { ElMessage, ElNotification } from 'element-plus'
import { useAdminStore } from '@/stores/admin'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 错误详情展示函数
const showErrorDetail = (errorInfo) => {
  const { title, message, details, requestId, errorType } = errorInfo
  
  // 构建详细错误信息HTML
  let description = message
  
  if (details) {
    description += '\n\n详细信息：'
    if (details.error_class) {
      description += `\n错误类型: ${details.error_class}`
    }
    if (details.error_message) {
      description += `\n错误信息: ${details.error_message}`
    }
    if (details.traceback && Array.isArray(details.traceback)) {
      description += '\n\n堆栈跟踪：\n' + details.traceback.slice(0, 10).join('\n')
    }
  }
  
  if (requestId) {
    description += `\n\n请求ID: ${requestId}`
  }
  
  if (errorType) {
    description += `\n错误分类: ${errorType}`
  }
  
  ElNotification({
    title: title || '请求失败',
    message: description,
    type: 'error',
    duration: 0, // 不自动关闭
    showClose: true,
    dangerouslyUseHTMLString: false
  })
}

// 获取错误类型描述
const getErrorTypeDescription = (status, code) => {
  const errorTypes = {
    400: '请求参数错误',
    401: '未授权访问',
    403: '权限不足',
    404: '资源不存在',
    408: '请求超时',
    409: '资源冲突',
    422: '验证错误',
    429: '请求过于频繁',
    500: '服务器内部错误',
    502: '网关错误',
    503: '服务不可用',
    504: '网关超时'
  }
  return errorTypes[status] || `错误 (${status || code})`
}

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const adminStore = useAdminStore()
    if (adminStore.token) {
      config.headers.Authorization = `Bearer ${adminStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 200) {
      // 构建详细错误信息
      const errorInfo = {
        title: `业务错误 - ${getErrorTypeDescription(res.code)}`,
        message: res.message || '请求失败',
        requestId: res.request_id,
        errorType: res.error_type,
        details: res.detail
      }
      
      showErrorDetail(errorInfo)
      
      if (res.code === 401) {
        const adminStore = useAdminStore()
        adminStore.logout()
        router.push('/login')
      }
      return Promise.reject(new Error(res.message))
    }
    return res
  },
  (error) => {
    // 处理不同类型的错误
    if (error.code === 'ECONNABORTED') {
      showErrorDetail({
        title: '请求超时',
        message: `请求超时（${api.defaults.timeout / 1000}秒），服务器响应过慢或网络不稳定`,
        errorType: 'timeout'
      })
    } else if (!error.response) {
      showErrorDetail({
        title: '网络错误',
        message: '无法连接到服务器，请检查网络连接或服务器状态',
        errorType: 'network_error'
      })
    } else {
      const { status, data } = error.response
      const errorInfo = {
        title: `HTTP错误 - ${getErrorTypeDescription(status)}`,
        message: data?.message || `HTTP ${status} 错误`,
        requestId: data?.request_id,
        errorType: data?.error_type || 'http_error',
        details: data?.detail
      }
      
      showErrorDetail(errorInfo)
      
      if (status === 401) {
        const adminStore = useAdminStore()
        adminStore.logout()
        router.push('/login')
      }
    }
    
    return Promise.reject(error)
  }
)

// 认证相关
export const login = (username, password) => 
  api.post('/auth/admin/login', { username, password })

export const logout = () => 
  api.post('/auth/logout')

// 仪表盘
export const getDashboard = () => 
  api.get('/admin/dashboard')

// 用户管理
export const getUserList = (params) => 
  api.get('/admin/users', { params })

export const createUser = (data) => 
  api.post('/admin/users', data)

export const updateUser = (id, data) => 
  api.put(`/admin/users/${id}`, data)

export const resetUserPassword = (id, data) => 
  api.post(`/admin/users/${id}/reset-password`, data)

export const changeUserBalance = (id, data) =>
  api.post(`/admin/users/${id}/balance`, data)

export const getUserDetail = (id) =>
  api.get(`/admin/users/${id}`)

export const deleteUser = (id) =>
  api.delete(`/admin/users/${id}`)

// 管理员管理
export const getAdminList = (params) => 
  api.get('/admin/admins', { params })

export const createAdmin = (data) => 
  api.post('/admin/admins', data)

export const updateAdmin = (id, data) => 
  api.put(`/admin/admins/${id}`, data)

export const deleteAdmin = (id) => 
  api.delete(`/admin/admins/${id}`)

export const resetAdminPassword = (id, data) => 
  api.post(`/admin/admins/${id}/reset-password`, data)

// 系统配置
export const getConfig = () => 
  api.get('/admin/config')

export const updatePrice = (data) => 
  api.put('/admin/config/price', data)

export default api
