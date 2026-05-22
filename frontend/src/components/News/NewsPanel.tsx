/**
 * 新闻面板组件
 */

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { newsApi, mindmapApi } from '@/services/api'
import { useNewsStore, useSettingsStore } from '@/stores'
import type { NewsItem } from '@/types'
import { format } from 'date-fns'
import clsx from 'clsx'
import { useState } from 'react'

export function NewsPanel() {
  const queryClient = useQueryClient()
  const {
    selectedNewsId,
    selectedCategory,
    setSelectedNewsId,
    setSelectedNews,
    setCurrentMindmap,
    setIsLoadingMindmap,
    setCategories,
    categories,
    useAnalysisForMindmap,
    setUseAnalysisForMindmap,
    customNewsInput,
    setCustomNewsInput,
    showCustomNewsInput,
    setShowCustomNewsInput,
  } = useNewsStore()

  const { settings } = useSettingsStore()
  const [hoveredNews, setHoveredNews] = useState<NewsItem | null>(null)
  const [hoverPosition, setHoverPosition] = useState({ x: 0, y: 0 })
  const [sortBy, setSortBy] = useState<'importance' | 'time'>('importance') // 排序方式
  const [isAgentRating, setIsAgentRating] = useState(false) // ✅ Agent评分状态

  // 获取新闻列表
  const { data: newsData, isLoading, isRefetching, refetch } = useQuery({
    queryKey: ['news', selectedCategory, sortBy],
    queryFn: () => newsApi.getNews(selectedCategory || undefined, 1, 20, false, sortBy),
    staleTime: 5 * 60 * 1000, // 5分钟
  })

  // 手动刷新函数
  const handleRefresh = async () => {
    try {
      // 先调用带refresh参数的API强制后端刷新缓存
      await newsApi.getNews(selectedCategory || undefined, 1, 20, true, sortBy)
      // 然后使查询失效并重新获取
      await queryClient.invalidateQueries({ queryKey: ['news', selectedCategory, sortBy] })
      // 使用refetch重新获取数据
      await refetch()
    } catch (error) {
      console.error('刷新新闻失败:', error)
    }
  }

  // ✅ 使用Agent重新评分
  const handleAgentRate = async () => {
    if (isAgentRating) return
    
    setIsAgentRating(true)
    try {
      console.log('[NewsPanel] 开始Agent评分...')
      const result = await newsApi.rateWithAgent(
        selectedCategory || undefined,
        settings.backendType === 'hermes' ? 'hermes' : 'openclaw'
      )
      
      console.log('[NewsPanel] Agent评分完成，更新新闻列表')
      
      // 更新查询数据
      queryClient.setQueryData(['news', selectedCategory, sortBy], result)
      
      alert(`✅ Agent评分完成！共评分 ${result.total} 条新闻`)
    } catch (error) {
      console.error('Agent评分失败:', error)
      alert('❌ Agent评分失败，请检查网络连接或稍后重试')
    } finally {
      setIsAgentRating(false)
    }
  }

  // 设置分类
  useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const cats = await newsApi.getCategories()
      setCategories(cats)
      return cats
    },
  })

  // 处理新闻选择
  const handleNewsSelect = async (news: NewsItem) => {
    setSelectedNewsId(news.id)
    setSelectedNews(news)
    setIsLoadingMindmap(true)

    try {
      // 始终使用 analyzeAndGenerate API，确保获取 analysis_text
      const backendType = useAnalysisForMindmap
        ? (settings.backendType === 'local' ? undefined : settings.backendType)
        : 'local'  // AI分析关闭时使用本地分析

      console.log('[NewsPanel] 调用分析:', {
        useAnalysisForMindmap,
        backendType: settings.backendType,
        effectiveBackend: backendType || 'local',
      })

      const result = await mindmapApi.analyzeAndGenerate({
        title: news.title,
        content: news.content || news.summary,
        news_id: news.id,
        backend_type: backendType,
      })

      // 保存分析文本到store
      if (result.analysis_text) {
        console.log('[NewsPanel] 收到分析文本，长度:', result.analysis_text.length)
        setCurrentMindmap({
          ...result.mindmap,
          analysis_text: result.analysis_text
        })
      } else {
        console.warn('[NewsPanel] 未收到分析文本')
        setCurrentMindmap(result.mindmap)
      }
    } catch (error) {
      console.error('生成思维导图失败:', error)
      setCurrentMindmap(null)
    } finally {
      setIsLoadingMindmap(false)
    }
  }

  // 处理自定义新闻提交
  const handleCustomNewsSubmit = async () => {
    if (!customNewsInput.trim()) {
      alert('请输入新闻内容')
      return
    }

    setIsLoadingMindmap(true)
    try {
      const backendType = useAnalysisForMindmap
        ? (settings.backendType === 'local' ? undefined : settings.backendType)
        : 'local'

      const result = await mindmapApi.analyzeAndGenerate({
        title: '自定义新闻',
        content: customNewsInput,
        backend_type: backendType,
      })

      if (result.analysis_text) {
        setCurrentMindmap({
          ...result.mindmap,
          analysis_text: result.analysis_text
        })
      } else {
        setCurrentMindmap(result.mindmap)
      }
      setCustomNewsInput('')
      setShowCustomNewsInput(false)
    } catch (error) {
      console.error('分析自定义新闻失败:', error)
      alert('分析失败，请重试')
    } finally {
      setIsLoadingMindmap(false)
    }
  }

  // 处理鼠标悬停
  const handleMouseEnter = (news: NewsItem, event: React.MouseEvent) => {
    const rect = event.currentTarget.getBoundingClientRect()
    setHoveredNews(news)
    setHoverPosition({
      x: rect.right + 10,
      y: rect.top,
    })
  }

  const handleMouseLeave = () => {
    setHoveredNews(null)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* 工具栏 */}
      <div className="p-4 border-b bg-white">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800">📰 新闻列表</h2>
          <div className="flex gap-2">
            {/* 排序按钮 */}
            <div className="flex items-center gap-1 bg-gray-100 rounded p-1">
              <button
                onClick={() => setSortBy('importance')}
                className={clsx(
                  'px-2 py-1 text-xs rounded transition-colors',
                  sortBy === 'importance'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:bg-gray-200'
                )}
              >
                按重要性
              </button>
              <button
                onClick={() => setSortBy('time')}
                className={clsx(
                  'px-2 py-1 text-xs rounded transition-colors',
                  sortBy === 'time'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:bg-gray-200'
                )}
              >
                按时间
              </button>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={isRefetching}
              className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 flex items-center gap-2"
            >
              {isRefetching ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  刷新中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  刷新
                </>
              )}
            </button>
            {/* ✅ Agent评分按钮 */}
            <button
              onClick={handleAgentRate}
              disabled={isAgentRating}
              className="px-3 py-1.5 text-sm bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50 flex items-center gap-2"
              title="使用AI Agent对新闻重要性进行智能评分（1-100分）"
            >
              {isAgentRating ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  评分中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI评分
                </>
              )}
            </button>
            <button
              onClick={() => setShowCustomNewsInput(!showCustomNewsInput)}
              className="px-3 py-1.5 text-sm bg-green-500 text-white rounded hover:bg-green-600"
            >
              {showCustomNewsInput ? '取消输入' : '输入新闻'}
            </button>
          </div>
        </div>

        {/* AI分析开关 */}
        <div className="flex items-center gap-2 mb-3 p-2 bg-gray-50 rounded">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={useAnalysisForMindmap}
              onChange={(e) => setUseAnalysisForMindmap(e.target.checked)}
              className="sr-only peer"
            />
            <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            <span className="ml-2 text-sm font-medium text-gray-700">使用AI分析</span>
          </label>
          {useAnalysisForMindmap && (
            <span className="text-xs text-gray-500">
              当前使用: {settings.backendType === 'openclaw' ? 'OpenClaw' : settings.backendType === 'hermes' ? 'Hermes' : '本地分析'}
            </span>
          )}
        </div>

        {/* 分类过滤 */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          <button
            onClick={() => setSelectedNewsId(null)}
            className={clsx(
              'px-3 py-1 text-sm rounded whitespace-nowrap',
              !selectedCategory
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
          >
            全部
          </button>
          {categories?.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedNewsId(null)}
              className={clsx(
                'px-3 py-1 text-sm rounded whitespace-nowrap',
                selectedCategory === cat
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* 自定义新闻输入框 */}
        {showCustomNewsInput && (
          <div className="mt-3 p-3 bg-gray-50 rounded border">
            <textarea
              value={customNewsInput}
              onChange={(e) => setCustomNewsInput(e.target.value)}
              placeholder="在此输入新闻标题和内容..."
              className="w-full p-2 border rounded text-sm min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="mt-2 flex justify-end gap-2">
              <button
                onClick={() => {
                  setCustomNewsInput('')
                  setShowCustomNewsInput(false)
                }}
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={handleCustomNewsSubmit}
                disabled={!customNewsInput.trim()}
                className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              >
                分析并生成思维导图
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 新闻列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {newsData?.items.map((news) => (
          <div
            key={news.id}
            onClick={() => handleNewsSelect(news)}
            onMouseEnter={(e) => handleMouseEnter(news, e)}
            onMouseLeave={handleMouseLeave}
            className={clsx(
              'p-4 rounded-lg border cursor-pointer transition-all relative',
              selectedNewsId === news.id
                ? 'border-blue-500 bg-blue-50 shadow-md'
                : 'border-gray-200 hover:border-blue-300 hover:shadow-sm'
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-800 mb-2 line-clamp-2">
                  {news.title}
                </h3>
                <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                  {news.summary}
                </p>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>{news.source}</span>
                  <span>•</span>
                  <span>{format(new Date(news.published_at), 'yyyy-MM-dd HH:mm')}</span>
                  <span>•</span>
                  <span className="text-blue-600 font-medium">
                    重要性: {news.importance_score.total.toFixed(1)}
                  </span>
                </div>
                {news.keywords && news.keywords.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {news.keywords.slice(0, 3).map((kw, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {news.image_url && (
                <img
                  src={news.image_url}
                  alt=""
                  className="w-20 h-20 object-cover rounded flex-shrink-0"
                />
              )}
            </div>
          </div>
        ))}

        {newsData?.items.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <p>暂无新闻</p>
          </div>
        )}
      </div>

      {/* 新闻详情浮窗 */}
      {hoveredNews && (
        <div
          className="fixed z-50 max-w-md bg-white rounded-lg shadow-xl border border-gray-200 p-4 flex flex-col"
          style={{
            left: Math.min(hoverPosition.x, window.innerWidth - 400),
            top: Math.min(hoverPosition.y, window.innerHeight - 300),
            maxHeight: '80vh', // ✅ 增加到80vh，提供更多空间
          }}
        >
          <h4 className="font-semibold text-gray-800 mb-2 line-clamp-2">{hoveredNews.title}</h4>
          {/* ✅ 优先显示完整内容，其次显示摘要 */}
          <div 
            className="text-sm text-gray-600 mb-3 overflow-y-auto flex-1 pr-2 custom-scrollbar" 
            style={{ 
              maxHeight: '500px', // ✅ 增加到500px
              minHeight: '80px',  // ✅ 增加最小高度
              lineHeight: '1.8',  // ✅ 增加行高提升可读性
            }}
          >
            {hoveredNews.content || hoveredNews.summary || '暂无内容'}
          </div>
          <div className="space-y-2 text-xs mt-auto pt-2 border-t border-gray-100">
            <div className="flex justify-between">
              <span className="text-gray-500">来源:</span>
              <span className="text-gray-700 font-medium">{hoveredNews.source}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">发布时间:</span>
              <span className="text-gray-700">
                {format(new Date(hoveredNews.published_at), 'yyyy-MM-dd HH:mm')}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">重要性评分:</span>
              <span className="text-blue-600 font-bold">
                {hoveredNews.importance_score.total.toFixed(1)}
              </span>
            </div>
            {hoveredNews.keywords && hoveredNews.keywords.length > 0 && (
              <div>
                <span className="text-gray-500 block mb-1">关键词:</span>
                <div className="flex flex-wrap gap-1">
                  {hoveredNews.keywords.map((kw, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
