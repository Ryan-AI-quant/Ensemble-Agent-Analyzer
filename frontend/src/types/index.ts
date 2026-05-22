/**
 * TypeScript 类型定义
 */

// 重要性评分
export interface ImportanceScore {
  total: number
  source_weight: number
  keyword_weight: number
  recency_weight: number
  sentiment_weight: number
}

// 新闻条目
export interface NewsItem {
  id: string
  title: string
  summary: string
  content?: string
  source: string
  url: string
  published_at: string
  importance_score: ImportanceScore
  image_url?: string
  category: string
  keywords: string[]
  sentiment: 'positive' | 'negative' | 'neutral'
}

// 新闻列表响应
export interface NewsListResponse {
  items: NewsItem[]
  total: number
  page: number
  page_size: number
  categories: string[]
}

// 思维导图节点
export interface MindMapNode {
  id: string
  text: string
  children: MindMapNode[]
  expand: boolean
  color?: string
  font_size?: number
  level: number
}

// 思维导图响应
export interface MindMapResponse {
  news_id: string
  root: MindMapNode
  layout: string
  total_nodes: number
  analysis_text?: string  // AI分析的文字内容
}

// 聊天消息角色
export type MessageRole = 'user' | 'assistant' | 'system'

// 聊天消息
export interface ChatMessage {
  role: MessageRole
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

// 聊天请求
export interface ChatRequest {
  message: string
  session_id: string
  context?: ChatMessage[]
}

// 聊天响应
export interface ChatResponse {
  message: ChatMessage
  session_id: string
  suggestions: string[]
}

// 布局选项
export interface LayoutOption {
  id: string
  name: string
  description: string
}

// 视图类型
export type ViewType = 'chat' | 'news' | 'settings'

// 健康状态
export interface HealthStatus {
  status: string
  version: string
  openclaw_connected: boolean
  services: Record<string, boolean>
}

// 后端类型
export type BackendType = 'openclaw' | 'hermes' | 'local'

// 系统设置
export interface SystemSettings {
  backendType: BackendType
  llmModel: string
  apiBaseUrl: string
  mindmapLayout: string
}

// 分析并生成思维导图请求
export interface AnalyzeAndGenerateRequest {
  title?: string
  content: string
  news_id?: string
  backend_type?: BackendType
}

// 分析结果
export interface NewsAnalysisResult {
  title: string
  summary: string
  key_points: string[]
  impact_analysis: string[]
  related_entities: Array<{ name: string; type: string; relation: string }>
  sentiment: string
  confidence: number
  categories: string[]
  source_analysis: Record<string, any>
  generated_at: string
}

// 分析并生成思维导图响应
export interface AnalyzeAndGenerateResponse {
  analysis: NewsAnalysisResult
  mindmap: MindMapResponse
  used_backend: string
  analysis_text?: string  // AI分析的文字内容（短中长期影响）
}

// 后端配置信息
export interface BackendConfig {
  current_backend: string
  backend_type: string
  openclaw: {
    api_url: string
    model: string
    configured: boolean
  }
  hermes: {
    api_url: string
    model: string
    configured: boolean
  }
  local: {
    enabled: boolean
  }
}
