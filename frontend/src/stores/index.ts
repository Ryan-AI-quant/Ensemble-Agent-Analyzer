/**
 * Zustand 状态管理
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ViewType, NewsItem, MindMapResponse, ChatMessage, SystemSettings, BackendType } from '@/types'

// 应用状态
interface AppState {
  currentView: ViewType
  setCurrentView: (view: ViewType) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentView: 'chat',
  setCurrentView: (view) => set({ currentView: view }),
}))

// 系统设置状态
interface SettingsState {
  settings: SystemSettings
  updateSettings: (settings: Partial<SystemSettings>) => void
  resetSettings: () => void
}

const defaultSettings: SystemSettings = {
  backendType: 'local',
  llmModel: '',
  apiBaseUrl: 'http://localhost:8000',
  mindmapLayout: 'radial',
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: defaultSettings,
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),
      resetSettings: () => set({ settings: defaultSettings }),
    }),
    {
      name: 'agent-news-settings',
    }
  )
)

// 新闻状态
interface NewsState {
  selectedNews: NewsItem | null
  selectedNewsId: string | null
  currentMindmap: MindMapResponse | null
  isLoadingMindmap: boolean
  categories: string[]
  selectedCategory: string | null
  useAnalysisForMindmap: boolean
  customNewsInput: string
  showCustomNewsInput: boolean

  setSelectedNews: (news: NewsItem | null) => void
  setSelectedNewsId: (id: string | null) => void
  setCurrentMindmap: (mindmap: MindMapResponse | null) => void
  setIsLoadingMindmap: (loading: boolean) => void
  setCategories: (categories: string[]) => void
  setSelectedCategory: (category: string | null) => void
  setUseAnalysisForMindmap: (use: boolean) => void
  setCustomNewsInput: (input: string) => void
  setShowCustomNewsInput: (show: boolean) => void
  clearNewsState: () => void
}

export const useNewsStore = create<NewsState>((set) => ({
  selectedNews: null,
  selectedNewsId: null,
  currentMindmap: null,
  isLoadingMindmap: false,
  categories: [],
  selectedCategory: null,
  useAnalysisForMindmap: false,
  customNewsInput: '',
  showCustomNewsInput: false,

  setSelectedNews: (news) => set({ selectedNews: news }),
  setSelectedNewsId: (id) => set({ selectedNewsId: id }),
  setCurrentMindmap: (mindmap) => set({ currentMindmap: mindmap }),
  setIsLoadingMindmap: (loading) => set({ isLoadingMindmap: loading }),
  setCategories: (categories) => set({ categories }),
  setSelectedCategory: (category) => set({ selectedCategory: category }),
  setUseAnalysisForMindmap: (use) => set({ useAnalysisForMindmap: use }),
  setCustomNewsInput: (input) => set({ customNewsInput: input }),
  setShowCustomNewsInput: (show) => set({ showCustomNewsInput: show }),
  clearNewsState: () => set({
    selectedNews: null,
    selectedNewsId: null,
    currentMindmap: null,
    isLoadingMindmap: false,
    customNewsInput: '',
    showCustomNewsInput: false,
  }),
}))

// 聊天状态
interface ChatState {
  messages: ChatMessage[]
  sessionId: string
  isTyping: boolean
  suggestions: string[]

  addMessage: (message: ChatMessage) => void
  updateLastMessage: (updater: (msg: ChatMessage) => ChatMessage) => void
  setMessages: (messages: ChatMessage[]) => void
  clearMessages: () => void
  setSessionId: (id: string) => void
  setIsTyping: (typing: boolean) => void
  setSuggestions: (suggestions: string[]) => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: 'default',
  isTyping: false,
  suggestions: [],

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message],
  })),
  updateLastMessage: (updater) => set((state) => {
    if (state.messages.length === 0) return state
    const newMessages = [...state.messages]
    newMessages[newMessages.length - 1] = updater(newMessages[newMessages.length - 1])
    return { messages: newMessages }
  }),
  setMessages: (messages) => set({ messages }),
  clearMessages: () => set({ messages: [], suggestions: [] }),
  setSessionId: (id) => set({ sessionId: id }),
  setIsTyping: (typing) => set({ isTyping: typing }),
  setSuggestions: (suggestions) => set({ suggestions }),
}))
