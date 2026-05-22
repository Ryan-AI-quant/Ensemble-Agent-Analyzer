/**
 * 侧边栏组件
 */

import { useAppStore } from '@/stores'
import type { ViewType } from '@/types'
import clsx from 'clsx'

interface NavItem {
  id: ViewType
  label: string
  icon: React.ReactNode
}

const navItems: NavItem[] = [
  {
    id: 'chat',
    label: '对话',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    id: 'news',
    label: '新闻',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
      </svg>
    ),
  },
  {
    id: 'settings',
    label: '设置',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
]

export function Sidebar() {
  const { currentView, setCurrentView } = useAppStore()

  return (
    <aside className="w-full md:w-16 lg:w-20 bg-white border-b md:border-b-0 md:border-r border-gray-200 flex md:flex-col h-auto md:h-full">
      {/* Logo */}
      <div className="h-14 md:h-16 flex items-center justify-center border-b border-gray-100">
        <img src="/icon2.jpg" alt="Ensemble-Agent-Analyzer" className="w-8 h-8 md:w-10 md:h-10 rounded-xl object-cover" />
      </div>

      {/* Navigation - 移动端横向滚动，桌面端纵向 */}
      <nav className="flex-1 py-2 md:py-4 px-2 md:px-2 space-y-0 md:space-y-2 flex md:flex-col overflow-x-auto md:overflow-visible scrollbar-hide">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setCurrentView(item.id)}
            className={clsx(
              'flex-shrink-0 w-full md:w-auto flex md:flex-col items-center justify-center py-2 md:py-3 px-3 md:px-2 rounded-xl transition-all duration-200 min-w-[80px] md:min-w-0',
              currentView === item.id
                ? 'bg-primary-50 text-primary-600'
                : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
            )}
          >
            {item.icon}
            <span className="ml-2 md:ml-0 md:mt-1.5 text-xs font-medium whitespace-nowrap">{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Footer - 移动端隐藏 */}
      <div className="hidden md:block p-3 border-t border-gray-100">
        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center mx-auto">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>
    </aside>
  )
}
