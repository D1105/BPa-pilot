import { useState, useEffect, useRef } from 'react'
import { 
  Users, MessageSquare, TrendingUp, Clock, Phone, Car, 
  DollarSign, MapPin, Calendar, ChevronRight, RefreshCw,
  Flame, Thermometer, Snowflake, X, Play, Send, Award,
  Target, UserCheck, Loader2, RotateCcw, Skull, AlertCircle
} from 'lucide-react'

interface Lead {
  id: number
  session_id: string
  name: string | null
  phone: string | null
  car_brand: string | null
  car_model: string | null
  budget_min: number | null
  budget_max: number | null
  country: string | null
  timeline: string | null
  status: string
  qualification: string | null
  created_at: string
}

interface Message {
  role: string
  content: string
  created_at: string
}

interface Stats {
  total_leads: number
  hot_leads: number
  warm_leads: number
  cold_leads: number
}

interface SimMessage {
  role: 'manager' | 'client'
  content: string
}

interface Preset {
  id: string
  name: string
  description: string
  difficulty: number
}

interface Evaluation {
  scores: {
    contact: number
    needs_discovery: number
    objection_handling: number
    presentation: number
    closing: number
  }
  strengths: string[]
  improvements: string[]
  overall_score: number
  recommendations: string
}

interface AdminPanelProps {
  isOpen: boolean
  onClose: () => void
}

const API_BASE = import.meta.env.VITE_API_BASE || ''
const apiUrl = (path: string) => (API_BASE ? `${API_BASE}${path}` : path)

export default function AdminPanel({ isOpen, onClose }: AdminPanelProps) {
  const [leads, setLeads] = useState<Lead[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [conversation, setConversation] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'leads' | 'stats' | 'simulator'>('leads')
  
  // Simulator state
  const [presets, setPresets] = useState<Preset[]>([])
  const [selectedPreset, setSelectedPreset] = useState<string>('medium')
  const [simMessages, setSimMessages] = useState<SimMessage[]>([])
  const [simInput, setSimInput] = useState('')
  const [simSessionId, setSimSessionId] = useState<string | null>(null)
  const [simLoading, setSimLoading] = useState(false)
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [showEvaluation, setShowEvaluation] = useState(false)
  const simMessagesEndRef = useRef<HTMLDivElement>(null)

  const fetchData = async () => {
    setIsLoading(true)
    try {
      const [leadsRes, statsRes] = await Promise.all([
        fetch(apiUrl('/api/leads')),
        fetch(apiUrl('/api/stats')),
      ])
      
      if (leadsRes.ok) {
        const leadsData = await leadsRes.json()
        setLeads(leadsData)
      }
      
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        setStats(statsData)
      }
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchConversation = async (sessionId: string) => {
    try {
      const res = await fetch(apiUrl(`/api/conversations/${sessionId}`))
      if (res.ok) {
        const data = await res.json()
        setConversation(data)
      }
    } catch (error) {
      console.error('Error fetching conversation:', error)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchData()
      fetchPresets()
    }
  }, [isOpen])
  
  useEffect(() => {
    simMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [simMessages])
  
  const fetchPresets = async () => {
    try {
      const res = await fetch(apiUrl('/api/simulator/presets'))
      if (res.ok) {
        const data = await res.json()
        setPresets(data.presets)
      }
    } catch (error) {
      console.error('Error fetching presets:', error)
    }
  }
  
  const startNewSimulation = () => {
    setSimMessages([])
    setSimSessionId(null)
    setEvaluation(null)
    setShowEvaluation(false)
  }
  
  const sendSimMessage = async () => {
    if (!simInput.trim() || simLoading) return
    
    const managerMessage: SimMessage = { role: 'manager', content: simInput.trim() }
    setSimMessages(prev => [...prev, managerMessage])
    setSimInput('')
    setSimLoading(true)
    
    try {
      const res = await fetch(apiUrl('/api/simulator/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: managerMessage.content,
          history: simMessages,
          session_id: simSessionId,
          preset: selectedPreset,
        }),
      })
      
      if (res.ok) {
        const data = await res.json()
        setSimSessionId(data.session_id)
        setSimMessages(prev => [...prev, { role: 'client', content: data.response }])
      }
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setSimLoading(false)
    }
  }
  
  const evaluateSession = async () => {
    if (simMessages.length < 2) return
    
    setSimLoading(true)
    try {
      const res = await fetch(apiUrl('/api/simulator/evaluate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          history: simMessages,
          preset: selectedPreset,
        }),
      })
      
      if (res.ok) {
        const data = await res.json()
        setEvaluation(data)
        setShowEvaluation(true)
      }
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setSimLoading(false)
    }
  }
  
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 40) return 'text-orange-400'
    return 'text-red-400'
  }
  
  const getScoreBar = (score: number) => {
    if (score >= 80) return 'bg-green-500'
    if (score >= 60) return 'bg-yellow-500'
    if (score >= 40) return 'bg-orange-500'
    return 'bg-red-500'
  }

  useEffect(() => {
    if (selectedLead) {
      fetchConversation(selectedLead.session_id)
    }
  }, [selectedLead])

  const getQualificationBadge = (qualification: string | null) => {
    switch (qualification) {
      case 'hot':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/20 text-red-400 text-xs">
            <Flame className="w-3 h-3" /> Горячий
          </span>
        )
      case 'warm':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs">
            <Thermometer className="w-3 h-3" /> Тёплый
          </span>
        )
      case 'cold':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-blue-500/20 text-blue-400 text-xs">
            <Snowflake className="w-3 h-3" /> Холодный
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-500/20 text-gray-400 text-xs">
            Новый
          </span>
        )
    }
  }

  const formatBudget = (min: number | null, max: number | null) => {
    if (!min && !max) return '—'
    if (min && max) return `${(min / 1_000_000).toFixed(1)}–${(max / 1_000_000).toFixed(1)} млн ₽`
    if (max) return `до ${(max / 1_000_000).toFixed(1)} млн ₽`
    if (min) return `от ${(min / 1_000_000).toFixed(1)} млн ₽`
    return '—'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-6xl h-[90vh] bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-white/10 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-white font-display">Админ-панель</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab('leads')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'leads'
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Users className="w-4 h-4 inline mr-2" />
                Лиды
              </button>
              <button
                onClick={() => setActiveTab('stats')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'stats'
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <TrendingUp className="w-4 h-4 inline mr-2" />
                Статистика
              </button>
              <button
                onClick={() => setActiveTab('simulator')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'simulator'
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Target className="w-4 h-4 inline mr-2" />
                Тренажёр
              </button>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              disabled={isLoading}
              className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {activeTab === 'leads' ? (
            <>
              {/* Leads List */}
              <div className="w-1/2 border-r border-white/10 overflow-y-auto">
                {leads.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <Users className="w-12 h-12 mb-4" />
                    <p>Пока нет лидов</p>
                    <p className="text-sm">Начните диалог в чате</p>
                  </div>
                ) : (
                  <div className="divide-y divide-white/5">
                    {leads.map(lead => (
                      <div
                        key={lead.id}
                        onClick={() => setSelectedLead(lead)}
                        className={`p-4 cursor-pointer transition-colors ${
                          selectedLead?.id === lead.id
                            ? 'bg-primary-600/20'
                            : 'hover:bg-white/5'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h3 className="font-medium text-white">
                              {lead.name || `Лид #${lead.session_id}`}
                            </h3>
                            {lead.phone && (
                              <p className="text-sm text-gray-400 flex items-center gap-1">
                                <Phone className="w-3 h-3" /> {lead.phone}
                              </p>
                            )}
                          </div>
                          {getQualificationBadge(lead.qualification)}
                        </div>
                        
                        <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                          {lead.car_brand && (
                            <span className="flex items-center gap-1">
                              <Car className="w-3 h-3" />
                              {lead.car_brand} {lead.car_model || ''}
                            </span>
                          )}
                          {(lead.budget_min || lead.budget_max) && (
                            <span className="flex items-center gap-1">
                              <DollarSign className="w-3 h-3" />
                              {formatBudget(lead.budget_min, lead.budget_max)}
                            </span>
                          )}
                          {lead.country && (
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {lead.country}
                            </span>
                          )}
                        </div>
                        
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-gray-600">
                            {new Date(lead.created_at).toLocaleString('ru-RU')}
                          </span>
                          <ChevronRight className="w-4 h-4 text-gray-600" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Lead Details & Conversation */}
              <div className="w-1/2 overflow-y-auto">
                {selectedLead ? (
                  <div className="p-6">
                    {/* Lead Info */}
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-white">
                          {selectedLead.name || `Лид #${selectedLead.session_id}`}
                        </h3>
                        {getQualificationBadge(selectedLead.qualification)}
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div className="glass rounded-xl p-4">
                          <p className="text-xs text-gray-500 mb-1">Телефон</p>
                          <p className="text-white">{selectedLead.phone || '—'}</p>
                        </div>
                        <div className="glass rounded-xl p-4">
                          <p className="text-xs text-gray-500 mb-1">Автомобиль</p>
                          <p className="text-white">
                            {selectedLead.car_brand 
                              ? `${selectedLead.car_brand} ${selectedLead.car_model || ''}`
                              : '—'}
                          </p>
                        </div>
                        <div className="glass rounded-xl p-4">
                          <p className="text-xs text-gray-500 mb-1">Бюджет</p>
                          <p className="text-white">
                            {formatBudget(selectedLead.budget_min, selectedLead.budget_max)}
                          </p>
                        </div>
                        <div className="glass rounded-xl p-4">
                          <p className="text-xs text-gray-500 mb-1">Страна</p>
                          <p className="text-white">{selectedLead.country || '—'}</p>
                        </div>
                        <div className="glass rounded-xl p-4">
                          <p className="text-xs text-gray-500 mb-1">Сроки</p>
                          <p className="text-white">{selectedLead.timeline || '—'}</p>
                        </div>
                        <div className="glass rounded-xl p-4">
                          <p className="text-xs text-gray-500 mb-1">Статус</p>
                          <p className="text-white capitalize">{selectedLead.status}</p>
                        </div>
                      </div>
                    </div>

                    {/* Conversation */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                        <MessageSquare className="w-4 h-4" />
                        История диалога
                      </h4>
                      <div className="space-y-3">
                        {conversation.map((msg, i) => (
                          <div
                            key={i}
                            className={`p-3 rounded-xl text-sm ${
                              msg.role === 'user'
                                ? 'bg-accent/20 text-orange-200 ml-8'
                                : 'bg-primary-600/20 text-primary-200 mr-8'
                            }`}
                          >
                            <p className="text-xs text-gray-500 mb-1">
                              {msg.role === 'user' ? 'Клиент' : 'ИИ-агент'}
                            </p>
                            <p className="whitespace-pre-wrap">{msg.content}</p>
                          </div>
                        ))}
                        {conversation.length === 0 && (
                          <p className="text-gray-500 text-sm text-center py-4">
                            Нет сообщений
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <MessageSquare className="w-12 h-12 mb-4" />
                    <p>Выберите лид для просмотра</p>
                  </div>
                )}
              </div>
            </>
          ) : activeTab === 'stats' ? (
            /* Stats Tab */
            <div className="flex-1 p-6 overflow-y-auto">
              {stats ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div className="glass rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-primary-500/20 flex items-center justify-center">
                        <Users className="w-6 h-6 text-primary-400" />
                      </div>
                    </div>
                    <p className="text-3xl font-bold text-white font-display">
                      {stats.total_leads}
                    </p>
                    <p className="text-sm text-gray-400">Всего лидов</p>
                  </div>
                  
                  <div className="glass rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center">
                        <Flame className="w-6 h-6 text-red-400" />
                      </div>
                    </div>
                    <p className="text-3xl font-bold text-white font-display">
                      {stats.hot_leads}
                    </p>
                    <p className="text-sm text-gray-400">Горячих</p>
                  </div>
                  
                  <div className="glass rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center">
                        <Thermometer className="w-6 h-6 text-orange-400" />
                      </div>
                    </div>
                    <p className="text-3xl font-bold text-white font-display">
                      {stats.warm_leads}
                    </p>
                    <p className="text-sm text-gray-400">Тёплых</p>
                  </div>
                  
                  <div className="glass rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                        <Snowflake className="w-6 h-6 text-blue-400" />
                      </div>
                    </div>
                    <p className="text-3xl font-bold text-white font-display">
                      {stats.cold_leads}
                    </p>
                    <p className="text-sm text-gray-400">Холодных</p>
                  </div>

                  {/* Conversion Funnel */}
                  <div className="col-span-full glass rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Воронка конверсии</h3>
                    <div className="space-y-3">
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-400 w-32">Всего лидов</span>
                        <div className="flex-1 h-8 bg-white/5 rounded-lg overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-primary-500 to-primary-600"
                            style={{ width: '100%' }}
                          />
                        </div>
                        <span className="text-white font-medium w-12 text-right">{stats.total_leads}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-400 w-32">Квалифицированы</span>
                        <div className="flex-1 h-8 bg-white/5 rounded-lg overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-orange-500 to-red-500"
                            style={{ width: `${stats.total_leads ? ((stats.hot_leads + stats.warm_leads) / stats.total_leads * 100) : 0}%` }}
                          />
                        </div>
                        <span className="text-white font-medium w-12 text-right">{stats.hot_leads + stats.warm_leads}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-400 w-32">Горячие</span>
                        <div className="flex-1 h-8 bg-white/5 rounded-lg overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-red-500 to-red-600"
                            style={{ width: `${stats.total_leads ? (stats.hot_leads / stats.total_leads * 100) : 0}%` }}
                          />
                        </div>
                        <span className="text-white font-medium w-12 text-right">{stats.hot_leads}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full">
                  <RefreshCw className="w-8 h-8 text-gray-500 animate-spin" />
                </div>
              )}
            </div>
          ) : (
            /* Simulator Tab */
            <div className="flex-1 flex overflow-hidden">
              {/* Left Panel - Settings & Chat */}
              <div className="flex-1 flex flex-col border-r border-white/10">
                {/* Preset Selection */}
                <div className="p-4 border-b border-white/10">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-medium text-white flex items-center gap-2">
                      <UserCheck className="w-4 h-4" />
                      Выберите тип клиента
                    </h3>
                    <button
                      onClick={startNewSimulation}
                      className="text-xs text-gray-400 hover:text-white flex items-center gap-1"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Новая сессия
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {presets.map(preset => (
                      <button
                        key={preset.id}
                        onClick={() => {
                          setSelectedPreset(preset.id)
                          startNewSimulation()
                        }}
                        className={`p-3 rounded-xl text-left transition-all ${
                          selectedPreset === preset.id
                            ? 'bg-purple-600/30 border border-purple-500'
                            : 'bg-white/5 border border-transparent hover:bg-white/10'
                        }`}
                      >
                        <div className="font-medium text-white text-sm">{preset.name}</div>
                        <div className="text-xs text-gray-400 mt-1">{preset.description}</div>
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {simMessages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Play className="w-12 h-12 mb-4" />
                      <p className="text-center">Начните диалог с клиентом</p>
                      <p className="text-sm text-center mt-2">
                        Вы — менеджер по продажам.<br/>
                        Попробуйте продать услуги автоимпорта.
                      </p>
                    </div>
                  ) : (
                    simMessages.map((msg, i) => (
                      <div
                        key={i}
                        className={`flex gap-3 ${msg.role === 'manager' ? 'flex-row-reverse' : ''}`}
                      >
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                            msg.role === 'manager'
                              ? 'bg-gradient-to-br from-green-500 to-emerald-600'
                              : 'bg-gradient-to-br from-purple-500 to-pink-600'
                          }`}
                        >
                          {msg.role === 'manager' ? (
                            <UserCheck className="w-4 h-4 text-white" />
                          ) : (
                            <Skull className="w-4 h-4 text-white" />
                          )}
                        </div>
                        <div
                          className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                            msg.role === 'manager'
                              ? 'bg-green-600/20 text-green-100 rounded-tr-sm'
                              : 'bg-purple-600/20 text-purple-100 rounded-tl-sm'
                          }`}
                        >
                          <p className="text-xs text-gray-400 mb-1">
                            {msg.role === 'manager' ? 'Вы (менеджер)' : 'Клиент'}
                          </p>
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    ))
                  )}
                  {simLoading && (
                    <div className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
                        <Skull className="w-4 h-4 text-white" />
                      </div>
                      <div className="bg-purple-600/20 rounded-2xl rounded-tl-sm px-4 py-3">
                        <div className="flex gap-1.5">
                          <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={simMessagesEndRef} />
                </div>
                
                {/* Input Area */}
                <div className="p-4 border-t border-white/10">
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={simInput}
                      onChange={e => setSimInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendSimMessage()}
                      placeholder="Напишите как менеджер..."
                      className="flex-1 px-4 py-3 bg-slate-800 text-white rounded-xl border border-white/10 focus:border-purple-500 focus:outline-none placeholder-gray-500 text-sm"
                      disabled={simLoading}
                    />
                    <button
                      onClick={sendSimMessage}
                      disabled={!simInput.trim() || simLoading}
                      className="px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                  {simMessages.length >= 4 && (
                    <button
                      onClick={evaluateSession}
                      disabled={simLoading}
                      className="w-full mt-3 py-3 bg-gradient-to-r from-amber-500 to-orange-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50"
                    >
                      <Award className="w-5 h-5" />
                      Получить оценку
                    </button>
                  )}
                </div>
              </div>
              
              {/* Right Panel - Evaluation */}
              <div className="w-80 p-4 overflow-y-auto">
                {showEvaluation && evaluation ? (
                  <div className="space-y-4">
                    <div className="text-center">
                      <div className={`text-5xl font-bold font-display ${getScoreColor(evaluation.overall_score)}`}>
                        {evaluation.overall_score}
                      </div>
                      <div className="text-gray-400 text-sm mt-1">Общая оценка</div>
                    </div>
                    
                    <div className="space-y-3">
                      {[
                        { key: 'contact', label: 'Установление контакта' },
                        { key: 'needs_discovery', label: 'Выявление потребностей' },
                        { key: 'objection_handling', label: 'Работа с возражениями' },
                        { key: 'presentation', label: 'Презентация' },
                        { key: 'closing', label: 'Закрытие сделки' },
                      ].map(({ key, label }) => (
                        <div key={key}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-gray-400">{label}</span>
                            <span className={getScoreColor(evaluation.scores[key as keyof typeof evaluation.scores])}>
                              {evaluation.scores[key as keyof typeof evaluation.scores]}
                            </span>
                          </div>
                          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${getScoreBar(evaluation.scores[key as keyof typeof evaluation.scores])} transition-all`}
                              style={{ width: `${evaluation.scores[key as keyof typeof evaluation.scores]}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <div className="glass rounded-xl p-4">
                      <h4 className="text-green-400 text-sm font-medium mb-2">✅ Сильные стороны</h4>
                      <ul className="text-xs text-gray-300 space-y-1">
                        {evaluation.strengths.map((s, i) => (
                          <li key={i}>• {s}</li>
                        ))}
                      </ul>
                    </div>
                    
                    <div className="glass rounded-xl p-4">
                      <h4 className="text-orange-400 text-sm font-medium mb-2">⚠️ Зоны роста</h4>
                      <ul className="text-xs text-gray-300 space-y-1">
                        {evaluation.improvements.map((s, i) => (
                          <li key={i}>• {s}</li>
                        ))}
                      </ul>
                    </div>
                    
                    <div className="glass rounded-xl p-4">
                      <h4 className="text-primary-400 text-sm font-medium mb-2">💡 Рекомендации</h4>
                      <p className="text-xs text-gray-300">{evaluation.recommendations}</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <Award className="w-12 h-12 mb-4" />
                    <p className="text-center text-sm">
                      Проведите диалог и нажмите<br/>
                      "Получить оценку"
                    </p>
                    <div className="mt-6 text-xs text-gray-600 space-y-2">
                      <p className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        Советы:
                      </p>
                      <ul className="space-y-1 text-gray-500">
                        <li>• Задавайте открытые вопросы</li>
                        <li>• Выявляйте скрытые возражения</li>
                        <li>• Не давите на клиента</li>
                        <li>• Предлагайте решения</li>
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
