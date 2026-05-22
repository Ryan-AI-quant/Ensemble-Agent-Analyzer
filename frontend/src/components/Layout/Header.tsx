/**
 * 头部组件
 */

import { useAppStore } from '@/stores'

export function Header() {
  const { currentView } = useAppStore()

  const getTitle = () => {
    switch (currentView) {
      case 'chat':
        return 'AI 对话'
      case 'news':
        return '新闻聚合'
      case 'settings':
        return '设置'
      default:
        return 'Agent News'
    }
  }

  const getSubtitle = () => {
    switch (currentView) {
      case 'chat':
        return '与 AI 智能助手对话'
      case 'news':
        return '查看最新新闻和生成思维导图'
      case 'settings':
        return '配置系统设置'
      default:
        return ''
    }
  }

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">{getTitle()}</h1>
        <p className="text-sm text-gray-500">{getSubtitle()}</p>
      </div>

      <div className="ml-auto flex items-center space-x-4">
        {/* Status indicator */}
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-gray-500">系统正常</span>
        </div>
      </div>
    </header>
  )
}
