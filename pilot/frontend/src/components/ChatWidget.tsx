import { useState, useRef, useEffect } from 'react'
import { X, Send, Bot, User, Minimize2, Loader2, AlertCircle, RefreshCw } from 'lucide-react'

interface Message {
  id: string
  role: 'assistant' | 'user'
  content: string
  timestamp: Date
  isError?: boolean
}

interface ChatWidgetProps {
  isOpen: boolean
  onClose: () => void
}

// Fallback ответы для graceful degradation
const FALLBACK_RESPONSES = [
  'Отличный выбор! Расскажите подробнее — какой бюджет вы рассматриваете?',
  'Понял вас. А есть ли предпочтения по стране-производителю? Корея, Япония, Германия?',
  'Хорошо! Какой тип кузова вам интересен — седан, кроссовер, внедорожник?',
  'Записал. А в какие сроки планируете покупку?',
  'Отлично! Оставьте, пожалуйста, ваш номер телефона, и наш менеджер свяжется с вами для обсуждения деталей.',
]

export default function ChatWidget({ isOpen, onClose }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Здравствуйте! 👋 Я ИИ-консультант АвтоИмпорт Pro. Помогу подобрать автомобиль из-за рубежа под ваши пожелания.\n\nРасскажите, какой автомобиль вы ищете? Интересует конкретная марка/модель или хотите подобрать по параметрам?',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [errorCount, setErrorCount] = useState(0)
  const [showRetry, setShowRetry] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (isOpen && !isMinimized) {
      inputRef.current?.focus()
    }
  }, [isOpen, isMinimized])

  const sendMessage = async (retryMessage?: string) => {
    const messageToSend = retryMessage || input.trim()
    if (!messageToSend || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageToSend,
      timestamp: new Date(),
    }

    if (!retryMessage) {
      setMessages(prev => [...prev, userMessage])
      setInput('')
    }
    
    setIsLoading(true)
    setShowRetry(false)

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30s timeout

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageToSend,
          history: messages.map(m => ({ role: m.role, content: m.content })),
          session_id: sessionId,
        }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `HTTP ${response.status}`)
      }

      const data = await response.json()
      
      // Сохраняем session_id
      if (data.session_id) {
        setSessionId(data.session_id)
      }

      // Сбрасываем счётчик ошибок при успехе
      setErrorCount(0)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        isError: !!data.error,
      }

      setMessages(prev => [...prev, assistantMessage])
      
    } catch (error) {
      console.error('Chat error:', error)
      
      const newErrorCount = errorCount + 1
      setErrorCount(newErrorCount)
      
      let errorMessage: string
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          errorMessage = 'Запрос занял слишком много времени. Попробуйте ещё раз.'
          setShowRetry(true)
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          errorMessage = 'Не удалось подключиться к серверу. Проверьте интернет-соединение.'
          setShowRetry(true)
        } else {
          errorMessage = error.message || 'Произошла ошибка. Попробуйте ещё раз.'
        }
      } else {
        errorMessage = 'Произошла непредвиденная ошибка.'
      }
      
      // После 3 ошибок используем fallback
      if (newErrorCount >= 3) {
        const fallbackIndex = Math.min(
          messages.filter(m => m.role === 'user').length - 1,
          FALLBACK_RESPONSES.length - 1
        )
        errorMessage = FALLBACK_RESPONSES[Math.max(0, fallbackIndex)]
      }
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: errorMessage,
        timestamp: new Date(),
        isError: newErrorCount < 3,
      }
      
      setMessages(prev => [...prev, assistantMessage])
      
    } finally {
      setIsLoading(false)
    }
  }

  const handleRetry = () => {
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user')
    if (lastUserMessage) {
      // Удаляем последнее сообщение об ошибке
      setMessages(prev => prev.slice(0, -1))
      sendMessage(lastUserMessage.content)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!isOpen) return null

  if (isMinimized) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={() => setIsMinimized(false)}
          className="flex items-center gap-3 px-5 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-full shadow-2xl hover:scale-105 transition-transform"
        >
          <Bot className="w-5 h-5" />
          <span className="font-medium">Продолжить чат</span>
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
        </button>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 md:p-6 pointer-events-none">
      <div className="w-full max-w-md h-[600px] max-h-[80vh] flex flex-col bg-slate-900 rounded-2xl shadow-2xl overflow-hidden pointer-events-auto border border-white/10 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-gradient-to-r from-primary-600 to-primary-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">ИИ-Консультант</h3>
              <div className="flex items-center gap-2 text-xs text-primary-200">
                <span className={`w-2 h-2 rounded-full ${errorCount >= 3 ? 'bg-yellow-400' : 'bg-green-400'}`} />
                {errorCount >= 3 ? 'Ограниченный режим' : 'Онлайн'}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMinimized(true)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <Minimize2 className="w-5 h-5 text-white" />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map(message => (
            <div
              key={message.id}
              className={`flex gap-3 message-animate ${
                message.role === 'user' ? 'flex-row-reverse' : ''
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.role === 'assistant'
                    ? message.isError 
                      ? 'bg-gradient-to-br from-yellow-500 to-orange-500'
                      : 'bg-gradient-to-br from-primary-500 to-primary-600'
                    : 'bg-gradient-to-br from-accent to-orange-500'
                }`}
              >
                {message.role === 'assistant' ? (
                  message.isError ? (
                    <AlertCircle className="w-4 h-4 text-white" />
                  ) : (
                    <Bot className="w-4 h-4 text-white" />
                  )
                ) : (
                  <User className="w-4 h-4 text-white" />
                )}
              </div>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === 'assistant'
                    ? message.isError
                      ? 'bg-yellow-900/30 text-yellow-100 rounded-tl-sm border border-yellow-700/50'
                      : 'bg-slate-800 text-gray-100 rounded-tl-sm'
                    : 'bg-gradient-to-r from-accent to-orange-500 text-white rounded-tr-sm'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {message.content}
                </p>
                <p
                  className={`text-xs mt-2 ${
                    message.role === 'assistant' 
                      ? message.isError ? 'text-yellow-400/60' : 'text-gray-500' 
                      : 'text-white/60'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3 message-animate">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                </div>
              </div>
            </div>
          )}

          {/* Retry Button */}
          {showRetry && !isLoading && (
            <div className="flex justify-center">
              <button
                onClick={handleRetry}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600/20 text-primary-400 rounded-lg hover:bg-primary-600/30 transition-colors text-sm"
              >
                <RefreshCw className="w-4 h-4" />
                Попробовать снова
              </button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-white/10">
          <div className="flex gap-3">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Введите сообщение..."
              className="flex-1 px-4 py-3 bg-slate-800 text-white rounded-xl border border-white/10 focus:border-primary-500 focus:outline-none placeholder-gray-500 text-sm"
              disabled={isLoading}
              maxLength={2000}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="px-4 py-3 bg-gradient-to-r from-accent to-orange-500 text-white rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Powered by AI • АвтоИмпорт Pro
          </p>
        </div>
      </div>
    </div>
  )
}
