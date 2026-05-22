/**
 * 新闻分析文本展示组件
 */

import { useNewsStore } from '@/stores'

export function AnalysisTextView() {
  const { currentMindmap, selectedNews } = useNewsStore()

  if (!selectedNews) {
    return (
      <div className="flex items-center justify-center text-gray-400 py-8">
        <p>请选择一条新闻查看分析</p>
      </div>
    )
  }

  // 从思维导图数据中提取分析文本（如果存在）
  const analysisText = currentMindmap?.analysis_text || ''

  if (!analysisText) {
    return (
      <div className="flex items-center justify-center text-gray-400 py-8">
        <p>暂无分析内容</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-800 mb-3">📊 新闻影响分析</h3>
      <div className="prose prose-sm max-w-none">
        <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
          {analysisText}
        </div>
      </div>
    </div>
  )
}
