/**
 * API 服务层
 */

import axios from 'axios'
import type {
  NewsItem,
  NewsListResponse,
  MindMapResponse,
  ChatRequest,
  ChatResponse,
  ChatMessage,
  LayoutOption,
  HealthStatus,
  AnalyzeAndGenerateRequest,
  AnalyzeAndGenerateResponse,
  BackendConfig,
} from '@/types'

const API_BASE = '/api'

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // ✅ 增加到60秒，适应AI分析的响应时间
  headers: {
    'Content-Type': 'application/json',
  },
})

// 新闻 API
export const newsApi = {
  // 获取新闻列表
  getNews: async (
    category?: string,
    page = 1,
    pageSize = 20,
    refresh = false,
    sortBy: 'importance' | 'time' = 'importance'
  ): Promise<NewsListResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      sort_by: sortBy,
      ...(category && { category }),
      ...(refresh && { refresh: 'true' }),
    })
    const response = await apiClient.get<NewsListResponse>(`/news/?${params}`)
    return response.data
  },

  // 获取新闻详情
  getNewsById: async (newsId: string): Promise<NewsItem> => {
    const response = await apiClient.get<NewsItem>(`/news/${newsId}`)
    return response.data
  },

  // 搜索新闻
  searchNews: async (query: string, limit = 10): Promise<NewsItem[]> => {
    const params = new URLSearchParams({ q: query, limit: limit.toString() })
    const response = await apiClient.get<NewsItem[]>(`/news/search/?${params}`)
    return response.data
  },

  // 获取分类
  getCategories: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/news/meta/categories')
    return response.data
  },

  // ✅ 使用Agent重新评分新闻
  rateWithAgent: async (
    category?: string,
    backendType: 'hermes' | 'openclaw' = 'hermes'
  ): Promise<NewsListResponse> => {
    console.log('[NewsAPI] 调用Agent评分:', { category, backendType })
    const response = await apiClient.post<NewsListResponse>('/news/rate-with-agent', {
      category,
      backend_type: backendType,
    })
    console.log('[NewsAPI] Agent评分完成，返回', response.data.total, '条新闻')
    return response.data
  },
}

// 思维导图 API
export const mindmapApi = {
  // 从新闻生成思维导图
  generateFromNews: async (
    newsId: string,
    layout = 'radial',
    useAnalysis = false
  ): Promise<MindMapResponse> => {
    const response = await apiClient.get<MindMapResponse>(
      `/mindmap/from-news/${newsId}`,
      { params: { layout, use_analysis: useAnalysis } }
    )
    return response.data
  },

  // 分析并生成思维导图
  analyzeAndGenerate: async (
    request: AnalyzeAndGenerateRequest
  ): Promise<AnalyzeAndGenerateResponse> => {
    const response = await apiClient.post<AnalyzeAndGenerateResponse>(
      '/mindmap/analyze-and-generate',
      request
    )
    return response.data
  },

  // 从文本生成思维导图
  generateFromText: async (
    title: string,
    content: string,
    layout = 'radial',
    useAnalysis = true
  ): Promise<MindMapResponse> => {
    const response = await apiClient.post<MindMapResponse>('/mindmap/from-text', null, {
      params: { title, content, layout, use_analysis: useAnalysis },
    })
    return response.data
  },

  // 获取布局选项
  getLayouts: async (): Promise<LayoutOption[]> => {
    const response = await apiClient.get<LayoutOption[]>('/mindmap/layouts')
    return response.data
  },

  // 获取后端配置
  getBackendConfig: async (): Promise<BackendConfig> => {
    const response = await apiClient.get<BackendConfig>('/mindmap/backend-config')
    return response.data
  },

  // 切换后端
  switchBackend: async (backendType: 'openclaw' | 'hermes' | 'local'): Promise<{ success: boolean; new_backend: string; backend_type: string }> => {
    const response = await apiClient.post('/mindmap/switch-backend', null, {
      params: { backend_type: backendType }
    })
    return response.data
  },

  // 更新系统设置
  updateSettings: async (settings: { backend_type?: string; llm_model?: string }): Promise<{ success: boolean; message: string; current_backend: string }> => {
    const response = await apiClient.post('/mindmap/update-settings', settings)
    return response.data
  },
}

// 聊天 API
export const chatApi = {
  // 发送消息
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/chat/message', request)
    return response.data
  },

  // 获取会话历史
  getHistory: async (sessionId: string): Promise<ChatMessage[]> => {
    const response = await apiClient.get<ChatMessage[]>(`/chat/history/${sessionId}`)
    return response.data
  },

  // 清除会话历史
  clearHistory: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/chat/history/${sessionId}`)
  },

  // 获取连接状态
  getStatus: async (): Promise<{ connected: boolean; model: string }> => {
    const response = await apiClient.get('/chat/status')
    return response.data
  },
}

// 系统 API
export const systemApi = {
  // 健康检查
  healthCheck: async (): Promise<HealthStatus> => {
    const response = await apiClient.get<HealthStatus>('/health')
    return response.data
  },

  // 获取API信息
  getInfo: async (): Promise<{ name: string; version: string }> => {
    const response = await apiClient.get('/api/info')
    return response.data
  },
}

// WebSocket 聊天服务
export class WebSocketChatService {
  private ws: WebSocket | null = null
  private sessionId: string
  private onMessage: (data: { type: string; content?: string; error?: string }) => void
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private isConnected = false
  private hasEverConnected = false

  constructor(
    sessionId: string,
    onMessage: (data: { type: string; content?: string; error?: string }) => void
  ) {
    this.sessionId = sessionId
    this.onMessage = onMessage
  }

  connect(): void {
    // 使用环境变量或默认的后端地址
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const wsProtocol = backendUrl.startsWith('https') ? 'wss:' : 'ws:'
    const wsHost = backendUrl.replace(/^https?:\/\//, '')
    const wsUrl = `${wsProtocol}//${wsHost}/api/chat/ws/${this.sessionId}`

    console.log('[WebSocket] 尝试连接到:', wsUrl)
    
    try {
      this.ws = new WebSocket(wsUrl)
      
      // 设置连接超时
      const connectionTimeout = setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
          console.error('[WebSocket] ⏱️ 连接超时（5秒）')
          console.error('[WebSocket] 请检查：')
          console.error('  1. 后端服务是否正在运行？')
          console.error('  2. 后端地址是否正确？当前地址:', wsUrl)
          console.error('  3. 防火墙是否阻止了WebSocket连接？')
          this.ws.close()
          // 只在从未成功连接过时才通知用户
          if (!this.hasEverConnected) {
            this.onMessage({ type: 'error', error: '连接超时，请检查后端服务是否运行在 http://localhost:8000' })
          }
        }
      }, 10000) // 增加到10秒超时

      this.ws.onopen = () => {
        clearTimeout(connectionTimeout)
        this.isConnected = true
        this.hasEverConnected = true
        console.log('[WebSocket] ✅ 连接成功', wsUrl)
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('[WebSocket] 收到消息:', data.type)
          this.onMessage(data)
        } catch (error) {
          console.error('[WebSocket] 消息解析失败:', error)
          this.onMessage({ type: 'error', error: '消息解析失败' })
        }
      }

      this.ws.onerror = (error) => {
        clearTimeout(connectionTimeout)
        console.error('[WebSocket] ❌ 连接错误:', error)
        console.error('[WebSocket] WebSocket状态:', this.ws?.readyState)
        
        // 只在从未成功连接过且不是重连过程中才显示错误
        if (!this.hasEverConnected && this.reconnectAttempts === 0) {
          console.error('[WebSocket] 可能原因:')
          console.error('  1. 后端服务未启动')
          console.error('  2. 防火墙阻止了WebSocket连接')
          console.error('  3. 端口被占用')
          // 不在这里调用 onMessage，等待重连结果
        }
      }

      this.ws.onclose = (event) => {
        clearTimeout(connectionTimeout)
        this.isConnected = false
        console.log('[WebSocket] 连接关闭', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        })
        
        // 根据关闭代码提供建议
        if (event.code === 1006) {
          console.error('[WebSocket] 异常关闭 - 可能是网络问题或服务未运行')
        }
        
        // 尝试重连
        this.attemptReconnect()
      }
    } catch (error) {
      console.error('[WebSocket] 创建WebSocket失败:', error)
      if (!this.hasEverConnected) {
        this.onMessage({ type: 'error', error: '无法创建WebSocket连接' })
      }
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`[WebSocket] 🔄 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      setTimeout(() => {
        this.connect()
      }, 2000 * this.reconnectAttempts)
    } else {
      console.error('[WebSocket] ❌ 达到最大重连次数，放弃重连')
      // 不在这里显示错误消息，只在控制台记录
      // 用户会在下次发送消息时看到"连接未建立"的提示
    }
  }

  sendMessage(message: string, context?: ChatMessage[]): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ message, context }))
    } else {
      console.error('[WebSocket] ❌ 无法发送消息，连接未建立')
      this.onMessage({ type: 'error', error: '连接未建立，请稍后重试' })
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
      this.isConnected = false
    }
  }

  getConnectionStatus(): boolean {
    return this.isConnected
  }
}

export { apiClient }
