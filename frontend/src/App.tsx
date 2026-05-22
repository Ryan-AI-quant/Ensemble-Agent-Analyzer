/**
 * Agent News System - 主应用组件
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAppStore, useSettingsStore } from '@/stores'
import { Sidebar, Header } from '@/components/Layout'
import { ChatWindow } from '@/components/Chat'
import { NewsPanel, NewsPanel as NewsPanelComponent } from '@/components/News'
import { MindMapView } from '@/components/MindMap'
import { AnalysisTextView } from '@/components/MindMap/AnalysisTextView'
import { mindmapApi } from '@/services/api'
import { useState, useEffect } from 'react'

// 创建 Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function MainContent() {
  const { currentView } = useAppStore()

  const isNewsView = currentView === 'news'

  return (
    <div className="h-screen flex flex-col md:flex-row bg-gray-50">
      {/* 侧边栏 - 移动端固定在顶部，桌面端在左侧 */}
      <Sidebar />

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        {/* 头部 */}
        <Header />

        {/* 桌面端：新闻视图固定高度不滚动，其他视图允许滚动 */}
        {/* 移动端：所有视图都允许滚动 */}
        <main className={`flex-1 min-h-0 ${
          isNewsView
            ? 'md:overflow-hidden overflow-y-auto overflow-x-hidden'
            : 'overflow-y-auto overflow-x-hidden'
        }`}>
          {currentView === 'chat' && <ChatWindow />}
          {currentView === 'settings' && <SettingsView />}
          {currentView === 'news' && (
            <>
              {/* ===== 桌面端：固定视口高度，左右布局 ===== */}
              <div className="hidden md:flex h-full">
                {/* 左侧新闻列表 - 固定宽度 */}
                <div className="w-96 border-r border-gray-200 bg-white overflow-y-auto flex-shrink-0">
                  <NewsPanel />
                </div>
                {/* 右侧：分析文本(上) + 思维导图(下) */}
                <div className="flex-1 flex flex-col min-h-0 min-w-0">
                  <div className="h-[35%] border-b border-gray-200 bg-white overflow-y-auto p-4 flex-shrink-0">
                    <AnalysisTextView />
                  </div>
                  <div className="flex-1 min-h-0 min-w-0">
                    <MindMapView />
                  </div>
                </div>
              </div>

              {/* ===== 移动端：流式布局，允许整页滚动 ===== */}
              <div className="md:hidden">
                {/* 新闻列表 */}
                <div className="border-b border-gray-200 bg-white">
                  <NewsPanel />
                </div>
                {/* 分析文本 */}
                <div className="border-b border-gray-200 bg-white p-4">
                  <AnalysisTextView />
                </div>
                {/* 思维导图 - 固定高度确保 ReactFlow 能正确计算尺寸 */}
                <div style={{ height: '60vh' }}>
                  <MindMapView />
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}

// 设置视图
function SettingsView() {
  const { settings, updateSettings } = useSettingsStore()
  const [localSettings, setLocalSettings] = useState(settings)
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  // 当本地设置变化时更新
  useEffect(() => {
    setLocalSettings(settings)
  }, [settings])

  // 保存设置
  const handleSave = async () => {
    setIsSaving(true)
    setSaveMessage('')

    try {
      // 先调用后端API更新设置
      await mindmapApi.updateSettings({
        backend_type: localSettings.backendType,
        llm_model: localSettings.llmModel,
      })

      // 更新全局设置
      updateSettings(localSettings)

      setSaveMessage('✅ 设置已保存并应用')
      setTimeout(() => setSaveMessage(''), 3000)
    } catch (error) {
      console.error('保存设置失败:', error)
      setSaveMessage('❌ 保存失败，请检查网络连接')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">系统设置</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                AI Agent 类型
              </label>
              <select
                value={localSettings.backendType}
                onChange={(e) => setLocalSettings({ ...localSettings, backendType: e.target.value as 'openclaw' | 'hermes' | 'local' })}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="openclaw">OpenClaw</option>
                <option value="hermes">Hermes</option>
                <option value="local">本地分析</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                选择用于对话和分析的AI Agent
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                LLM 模型
              </label>
              <input
                type="text"
                value={localSettings.llmModel}
                onChange={(e) => setLocalSettings({ ...localSettings, llmModel: e.target.value })}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="输入模型名称（如 gpt-4, claude-3, llama3 等）"
              />
              <p className="mt-1 text-xs text-gray-500">
                指定要使用的LLM模型名称
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                思维导图布局
              </label>
              <select
                value={localSettings.mindmapLayout}
                onChange={(e) => setLocalSettings({ ...localSettings, mindmapLayout: e.target.value })}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="radial">放射状布局</option>
                <option value="horizontal">水平布局</option>
                <option value="vertical">垂直布局</option>
              </select>
            </div>

            {saveMessage && (
              <div className={`p-3 rounded-lg text-sm ${
                saveMessage.includes('✅') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {saveMessage}
              </div>
            )}

            <div className="pt-4">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? '保存中...' : '保存设置'}
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">About</h2>
          <div className="space-y-2 text-sm text-gray-600">
            <p><strong>Ensemble-Agent-Analyzer</strong></p>
            <p>Version: 1.0.0</p>
            <p>author: Ryan-AI-quant</p>
            <p className="pt-2">
              A Multi-Agent Framework Integration System for News Sentiment Analysis with Industry Chain Visualization.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// 应用入口
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainContent />
    </QueryClientProvider>
  )
}

export default App
