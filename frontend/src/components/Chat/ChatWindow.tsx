/**
 * 聊天窗口组件
 */

import { useState, useRef, useEffect } from 'react'
import { useChatStore } from '@/stores'
import { chatApi, WebSocketChatService } from '@/services/api'
import type { ChatMessage } from '@/types'
import clsx from 'clsx'
import { format } from 'date-fns'

// 全局WebSocket服务单例
let globalWsService: WebSocketChatService | null = null

export function ChatWindow() {
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    sessionId,
    isTyping,
    suggestions,
    addMessage,
    updateLastMessage,
    clearMessages,
    setIsTyping,
    setSuggestions,
  } = useChatStore()

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  // 初始化 WebSocket
  useEffect(() => {
    // 如果全局服务不存在或连接已断开，创建/重新连接
    if (!globalWsService || !globalWsService.getConnectionStatus()) {
      console.log('[ChatWindow] 初始化WebSocket连接')
      
      // 如果已有实例但连接断开，先清理
      if (globalWsService) {
        console.log('[ChatWindow] 检测到旧连接已断开，创建新连接')
        try {
          globalWsService.disconnect()
        } catch (e) {
          console.warn('[ChatWindow] 断开旧连接时出错（可忽略）:', e)
        }
        // 等待一小段时间确保完全断开
        globalWsService = null
      }
      
      // 延迟创建新连接，避免与浏览器的清理过程冲突
      const connectTimeout = setTimeout(() => {
        globalWsService = new WebSocketChatService(
          sessionId,
          (data) => {
            if (data.type === 'chunk') {
              // 流式更新 - 更新最后一条助手消息
              updateLastMessage((lastMessage) => ({
                ...lastMessage,
                content: lastMessage.content + (data.content || ''),
              }))
            } else if (data.type === 'done') {
              setIsTyping(false)
              if (data.suggestions) {
                setSuggestions(data.suggestions)
              }
            } else if (data.type === 'error') {
              setIsTyping(false)
              // 只有在有用户消息后才显示错误（即发送消息时的错误）
              const hasUserMessages = useChatStore.getState().messages.some(m => m.role === 'user')
              if (hasUserMessages) {
                addMessage({
                  role: 'assistant',
                  content: `错误: ${data.error}`,
                  timestamp: new Date().toISOString(),
                })
              } else {
                // 静默处理连接阶段的错误
                console.debug('[ChatWindow] WebSocket连接阶段错误（已忽略）:', data.error)
              }
            }
          }
        )

        globalWsService.connect()
      }, 100) // 延迟100ms
      
      return () => {
        clearTimeout(connectTimeout)
      }
    } else {
      console.log('[ChatWindow] WebSocket连接已存在且正常，复用连接')
    }

    // 清理函数：不关闭WebSocket，保持连接以便其他页面使用
    return () => {
      // 不再断开连接，让WebSocket在整个应用生命周期中保持
    }
  }, [sessionId]) // 只在sessionId变化时重新创建

  // 发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || isTyping) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    }

    addMessage(userMessage)
    setInputValue('')
    setIsTyping(true)
    setSuggestions([])

    // 添加空的助手消息用于流式更新
    addMessage({
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    })

    // 通过 WebSocket 发送
    if (globalWsService) {
      globalWsService.sendMessage(userMessage.content, messages.slice(0, -2))
    }
  }

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 清除对话
  const handleClear = () => {
    clearMessages()
    chatApi.clearHistory(sessionId)
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">开始对话</h3>
            <p className="text-sm text-gray-500 max-w-sm">
              告诉我想了解什么，或者直接询问关于新闻或思维导图的问题
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={clsx(
              'flex animate-fade-in',
              message.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={clsx(
                'max-w-[80%] rounded-2xl px-4 py-3',
                message.role === 'user'
                  ? 'bg-primary-600 text-white rounded-br-md'
                  : 'bg-white text-gray-800 rounded-bl-md shadow-sm'
              )}
            >
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
              <p
                className={clsx(
                  'text-xs mt-1',
                  message.role === 'user' ? 'text-primary-200' : 'text-gray-400'
                )}
              >
                {format(new Date(message.timestamp), 'HH:mm')}
              </p>
            </div>
          </div>
        ))}

        {/* 正在输入指示器 */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white rounded-2xl rounded-bl-md shadow-sm px-4 py-3">
              <div className="flex space-x-1">
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 建议回复 */}
      {suggestions.length > 0 && !isTyping && (
        <div className="px-4 pb-2">
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => setInputValue(suggestion)}
                className="px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-full text-gray-600 hover:bg-gray-50 hover:border-primary-300 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 输入区域 */}
      <div className="p-4 bg-white border-t border-gray-200">
        <div className="flex items-end space-x-3">
          <div className="flex-1 relative">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
              className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              rows={1}
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
          </div>

          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isTyping}
            className="p-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>

          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="p-3 text-gray-400 hover:text-gray-600 transition-colors"
              title="清除对话"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
