import { useState, useRef, useEffect } from 'react'
import {
  Send, Sparkles, User, RotateCcw, Copy, ThumbsUp, ThumbsDown,
  TrendingUp, Users, DollarSign, AlertTriangle, ChevronRight,
  Database, Loader2,
} from 'lucide-react'
import { clsx } from 'clsx'
import GlassCard from '../components/common/GlassCard'

// ─── Types ───

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: DataSource[]
  insights?: InsightCard[]
  loading?: boolean
}

interface DataSource {
  type: 'role' | 'function' | 'skill' | 'task'
  name: string
  detail: string
}

interface InsightCard {
  label: string
  value: string
  delta?: string
  sentiment: 'positive' | 'negative' | 'neutral'
  icon: 'headcount' | 'cost' | 'risk' | 'trend'
}

// ─── Suggested Prompts ───

const SUGGESTED_PROMPTS = [
  {
    label: 'Workforce Risk',
    prompt: 'Which roles are most at risk of automation in the next 12 months?',
    icon: AlertTriangle,
    color: 'text-destructive',
  },
  {
    label: 'Cost Savings',
    prompt: 'What are the top cost-saving opportunities across all functions?',
    icon: DollarSign,
    color: 'text-warning',
  },
  {
    label: 'Skill Gaps',
    prompt: 'What are the critical skill gaps that need to be addressed?',
    icon: TrendingUp,
    color: 'text-primary',
  },
  {
    label: 'HC Summary',
    prompt: 'Give me a headcount breakdown by function with automation potential.',
    icon: Users,
    color: 'text-success',
  },
]

// ─── Icon Map ───

const INSIGHT_ICONS = {
  headcount: Users,
  cost: DollarSign,
  risk: AlertTriangle,
  trend: TrendingUp,
}

// ─── Mock responses for demo ───

function getMockResponse(query: string): { content: string; sources: DataSource[]; insights: InsightCard[] } {
  const q = query.toLowerCase()

  if (q.includes('risk') || q.includes('automation')) {
    return {
      content: `Based on the current workforce data, I've identified **12 roles** with high automation exposure (>70% task automability). The most impacted functions are **Operations** and **Finance**, where repetitive transaction-processing roles face significant displacement risk.\n\nKey findings:\n- **Data Entry Specialists** — 84% of tasks are automatable with existing tools\n- **Invoice Processing Clerks** — 78% automation potential, 23 FTEs affected\n- **Report Analysts** — 72% of reporting tasks can be automated via BI tools\n\nI recommend prioritizing reskilling programs for these roles and exploring redeployment pathways through the Simulation Lab.`,
      sources: [
        { type: 'role', name: 'Data Entry Specialist', detail: '84% automatable · 45 HC' },
        { type: 'role', name: 'Invoice Processing Clerk', detail: '78% automatable · 23 HC' },
        { type: 'function', name: 'Operations', detail: '6 high-risk roles identified' },
      ],
      insights: [
        { label: 'At-Risk Roles', value: '12', sentiment: 'negative', icon: 'risk' },
        { label: 'Affected HC', value: '156', delta: '8.2%', sentiment: 'negative', icon: 'headcount' },
        { label: 'Potential Savings', value: '$4.2M', sentiment: 'positive', icon: 'cost' },
      ],
    }
  }

  if (q.includes('cost') || q.includes('saving')) {
    return {
      content: `Analyzing savings opportunities across the organization, the **total unrealized value** from automation gaps is estimated at **$12.8M annually**.\n\nTop opportunities by function:\n1. **Operations** — $4.1M in addressable savings (adoption gap: $2.3M)\n2. **Finance & Accounting** — $3.2M potential (28 roles, 340 HC)\n3. **Customer Service** — $2.8M from AI-assisted ticket resolution\n\nThe **adoption gap alone** represents $6.2M — these are savings achievable with tools already deployed but underutilized. This is your fastest path to ROI.`,
      sources: [
        { type: 'function', name: 'Operations', detail: '$4.1M savings potential' },
        { type: 'function', name: 'Finance & Accounting', detail: '$3.2M savings potential' },
        { type: 'function', name: 'Customer Service', detail: '$2.8M savings potential' },
      ],
      insights: [
        { label: 'Total Opportunity', value: '$12.8M', sentiment: 'positive', icon: 'cost' },
        { label: 'Adoption Gap', value: '$6.2M', delta: 'quick wins', sentiment: 'positive', icon: 'trend' },
        { label: 'Functions Impacted', value: '6', sentiment: 'neutral', icon: 'headcount' },
      ],
    }
  }

  if (q.includes('skill') || q.includes('gap')) {
    return {
      content: `The workforce analysis reveals **34 sunset skills** declining in demand and **28 sunrise skills** emerging as critical.\n\n**Critical gaps to address:**\n- **AI/ML Operations** — Only 18% of technical staff have proficiency\n- **Prompt Engineering** — Growing demand across all functions, currently at 12% coverage\n- **Data Governance** — Required for compliance, 45% gap in Finance\n\n**Sunset skills** being displaced:\n- Manual data reconciliation, physical filing, legacy ERP navigation\n\nRecommendation: Launch a targeted upskilling program focusing on the top 5 sunrise skills to reduce the net skill gap by 60% within 6 months.`,
      sources: [
        { type: 'skill', name: 'AI/ML Operations', detail: '18% proficiency · critical' },
        { type: 'skill', name: 'Prompt Engineering', detail: '12% coverage · rising demand' },
        { type: 'skill', name: 'Data Governance', detail: '45% gap in Finance' },
      ],
      insights: [
        { label: 'Sunrise Skills', value: '28', sentiment: 'positive', icon: 'trend' },
        { label: 'Sunset Skills', value: '34', sentiment: 'negative', icon: 'risk' },
        { label: 'Net Skill Gap', value: '42%', sentiment: 'negative', icon: 'headcount' },
      ],
    }
  }

  if (q.includes('headcount') || q.includes('breakdown')) {
    return {
      content: `Here's the current headcount breakdown with automation potential:\n\n| Function | HC | Automation % | Potential FTE Reduction |\n|---|---|---|---|\n| Operations | 480 | 62% | 89 FTEs |\n| Finance & Accounting | 340 | 58% | 64 FTEs |\n| Customer Service | 290 | 54% | 48 FTEs |\n| Sales | 420 | 38% | 32 FTEs |\n| Engineering | 380 | 31% | 24 FTEs |\n| HR | 180 | 45% | 28 FTEs |\n\n**Total workforce**: 2,090 HC across 6 functions. The organization has a blended automation potential of **48%**, with **285 FTEs** potentially freed through full automation adoption.`,
      sources: [
        { type: 'function', name: 'Operations', detail: '480 HC · 62% automatable' },
        { type: 'function', name: 'Finance & Accounting', detail: '340 HC · 58% automatable' },
        { type: 'function', name: 'Customer Service', detail: '290 HC · 54% automatable' },
      ],
      insights: [
        { label: 'Total HC', value: '2,090', sentiment: 'neutral', icon: 'headcount' },
        { label: 'Avg Automation', value: '48%', sentiment: 'neutral', icon: 'trend' },
        { label: 'Freeable FTEs', value: '285', sentiment: 'positive', icon: 'headcount' },
      ],
    }
  }

  // Default
  return {
    content: `I've analyzed the workforce data to answer your question.\n\nBased on the current organization structure with **2,090 employees** across **6 functions**, there are several key areas worth exploring:\n\n- **Automation readiness** varies significantly by function (31% to 62%)\n- **$12.8M** in unrealized automation value has been identified\n- **12 roles** are flagged as high-risk for displacement\n\nWould you like me to dive deeper into any specific area? I can analyze roles, functions, skills, or financial projections in detail.`,
    sources: [
      { type: 'function', name: 'Organization Overview', detail: '2,090 HC · 6 functions' },
    ],
    insights: [
      { label: 'Workforce Size', value: '2,090', sentiment: 'neutral', icon: 'headcount' },
      { label: 'Unrealized Value', value: '$12.8M', sentiment: 'positive', icon: 'cost' },
    ],
  }
}

// ─── Component ───

export default function Nova() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (text?: string) => {
    const query = text ?? input.trim()
    if (!query || isTyping) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date(),
    }

    const loadingMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      loading: true,
    }

    setMessages((prev) => [...prev, userMsg, loadingMsg])
    setInput('')
    setIsTyping(true)

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 1200 + Math.random() * 800))

    const response = getMockResponse(query)

    setMessages((prev) =>
      prev.map((m) =>
        m.id === loadingMsg.id
          ? { ...m, content: response.content, sources: response.sources, insights: response.insights, loading: false }
          : m
      )
    )
    setIsTyping(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleReset = () => {
    setMessages([])
    setIsTyping(false)
    setInput('')
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="h-full flex flex-col max-w-5xl mx-auto">
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {isEmpty ? (
          /* Empty State — Welcome + Suggested Prompts */
          <div className="flex flex-col items-center justify-center h-full px-4">
            {/* Nova Identity */}
            <div className="relative mb-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/30 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-primary" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-success border-2 border-background flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
              </div>
            </div>

            <h2 className="text-xl font-bold text-foreground mb-1">Nova</h2>
            <p className="text-sm text-muted-foreground mb-1">Workforce Twin Assistant</p>
            <p className="text-xs text-muted-foreground/70 mb-8 text-center max-w-md">
              Ask me anything about your workforce — roles, automation gaps, costs, skills, or transformation impact.
              I query the organization graph in real time.
            </p>

            {/* Data Status Indicator */}
            <div className="flex items-center gap-2 mb-8 px-3 py-1.5 rounded-full bg-muted/30 border border-border/50">
              <Database className="w-3 h-3 text-success" />
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Connected to Organization Graph</span>
              <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            </div>

            {/* Suggested Prompts */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl">
              {SUGGESTED_PROMPTS.map((sp) => (
                <button
                  key={sp.label}
                  onClick={() => handleSend(sp.prompt)}
                  className="group glass-inner rounded-xl p-4 text-left hover:bg-muted/40 transition-all duration-200 border border-border/30 hover:border-primary/30"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <sp.icon className={clsx('w-4 h-4', sp.color)} />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{sp.label}</span>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">{sp.prompt}</p>
                  <div className="flex items-center gap-1 mt-2 text-primary/0 group-hover:text-primary/60 transition-colors">
                    <span className="text-[10px]">Ask Nova</span>
                    <ChevronRight className="w-3 h-3" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Messages */
          <div className="space-y-6 py-4 px-2">
            {messages.map((msg) => (
              <div key={msg.id} className={clsx('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                {msg.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/30 flex items-center justify-center mt-1">
                    <Sparkles className="w-4 h-4 text-primary" />
                  </div>
                )}

                <div className={clsx('max-w-[75%]', msg.role === 'user' ? 'order-1' : '')}>
                  {/* Message Bubble */}
                  <div
                    className={clsx(
                      'rounded-2xl px-4 py-3 text-sm leading-relaxed',
                      msg.role === 'user'
                        ? 'bg-primary/15 border border-primary/20 text-foreground'
                        : 'glass-inner border border-border/30 text-foreground'
                    )}
                  >
                    {msg.loading ? (
                      <div className="flex items-center gap-2 py-1">
                        <Loader2 className="w-4 h-4 text-primary animate-spin" />
                        <span className="text-muted-foreground text-xs">Querying organization data...</span>
                      </div>
                    ) : (
                      <div className="nova-markdown">
                        {msg.content.split('\n').map((line, i) => {
                          // Simple markdown-ish rendering
                          if (line.startsWith('|')) {
                            // Table row
                            const cells = line.split('|').filter(Boolean).map((c) => c.trim())
                            if (line.includes('---')) return null
                            return (
                              <div key={i} className="grid gap-2 py-1 text-xs font-mono" style={{ gridTemplateColumns: `repeat(${cells.length}, 1fr)` }}>
                                {cells.map((cell, j) => (
                                  <span key={j} className={j === 0 ? 'text-foreground font-medium' : 'text-muted-foreground text-right'}>
                                    {cell}
                                  </span>
                                ))}
                              </div>
                            )
                          }
                          if (line.startsWith('- ')) {
                            return (
                              <div key={i} className="flex items-start gap-2 py-0.5 pl-1">
                                <span className="text-primary mt-1.5 w-1 h-1 rounded-full bg-primary flex-shrink-0" />
                                <span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.*?)\*\*/g, '<strong class="text-foreground">$1</strong>') }} />
                              </div>
                            )
                          }
                          if (line.match(/^\d+\.\s/)) {
                            return (
                              <div key={i} className="flex items-start gap-2 py-0.5 pl-1">
                                <span className="text-primary font-mono text-xs mt-0.5 flex-shrink-0">{line.match(/^(\d+)\./)?.[1]}.</span>
                                <span dangerouslySetInnerHTML={{ __html: line.replace(/^\d+\.\s/, '').replace(/\*\*(.*?)\*\*/g, '<strong class="text-foreground">$1</strong>') }} />
                              </div>
                            )
                          }
                          if (!line.trim()) return <div key={i} className="h-2" />
                          return (
                            <p key={i} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong class="text-foreground">$1</strong>') }} />
                          )
                        })}
                      </div>
                    )}
                  </div>

                  {/* Insight Cards — below assistant messages */}
                  {msg.role === 'assistant' && !msg.loading && msg.insights && msg.insights.length > 0 && (
                    <div className="flex gap-2 mt-3 flex-wrap">
                      {msg.insights.map((insight, i) => {
                        const Icon = INSIGHT_ICONS[insight.icon]
                        return (
                          <div
                            key={i}
                            className={clsx(
                              'flex items-center gap-2 px-3 py-2 rounded-lg border text-xs',
                              insight.sentiment === 'positive' && 'bg-success/5 border-success/20',
                              insight.sentiment === 'negative' && 'bg-destructive/5 border-destructive/20',
                              insight.sentiment === 'neutral' && 'bg-muted/30 border-border/30'
                            )}
                          >
                            <Icon className={clsx(
                              'w-3.5 h-3.5',
                              insight.sentiment === 'positive' && 'text-success',
                              insight.sentiment === 'negative' && 'text-destructive',
                              insight.sentiment === 'neutral' && 'text-muted-foreground'
                            )} />
                            <div>
                              <div className="text-muted-foreground text-[10px] uppercase tracking-wider">{insight.label}</div>
                              <div className="font-mono font-bold text-foreground">{insight.value}</div>
                            </div>
                            {insight.delta && (
                              <span className="text-[10px] text-muted-foreground ml-1">{insight.delta}</span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {/* Sources */}
                  {msg.role === 'assistant' && !msg.loading && msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3">
                      <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 flex items-center gap-1">
                        <Database className="w-3 h-3" />
                        Sources
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.sources.map((src, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-muted/20 border border-border/30 text-[11px] text-muted-foreground"
                          >
                            <span className={clsx(
                              'w-1.5 h-1.5 rounded-full',
                              src.type === 'role' && 'bg-primary',
                              src.type === 'function' && 'bg-accent',
                              src.type === 'skill' && 'bg-success',
                              src.type === 'task' && 'bg-warning'
                            )} />
                            <span className="font-medium text-foreground">{src.name}</span>
                            <span className="text-muted-foreground/70">· {src.detail}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Action bar — assistant only */}
                  {msg.role === 'assistant' && !msg.loading && (
                    <div className="flex items-center gap-1 mt-2">
                      <button
                        onClick={() => copyToClipboard(msg.content)}
                        className="p-1.5 rounded-md hover:bg-muted/40 text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                        title="Copy"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded-md hover:bg-muted/40 text-muted-foreground/50 hover:text-muted-foreground transition-colors" title="Helpful">
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded-md hover:bg-muted/40 text-muted-foreground/50 hover:text-muted-foreground transition-colors" title="Not helpful">
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className={clsx('text-[10px] text-muted-foreground/40 mt-1', msg.role === 'user' ? 'text-right' : '')}>
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-muted/40 border border-border/30 flex items-center justify-center mt-1">
                    <User className="w-4 h-4 text-muted-foreground" />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 p-4 border-t border-border/50">
        {/* Reset button */}
        {messages.length > 0 && (
          <div className="flex justify-center mb-3">
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] text-muted-foreground hover:text-foreground bg-muted/20 hover:bg-muted/40 border border-border/30 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              New conversation
            </button>
          </div>
        )}

        <div className="glass-inner rounded-2xl border border-border/40 focus-within:border-primary/40 focus-within:glow-border transition-all">
          <div className="flex items-end gap-2 p-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Nova about your workforce..."
              rows={1}
              className="flex-1 bg-transparent border-none outline-none resize-none text-sm text-foreground placeholder:text-muted-foreground/50 min-h-[24px] max-h-[120px]"
              style={{ height: 'auto' }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement
                target.style.height = 'auto'
                target.style.height = `${Math.min(target.scrollHeight, 120)}px`
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isTyping}
              className={clsx(
                'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all',
                input.trim() && !isTyping
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-muted/30 text-muted-foreground/30 cursor-not-allowed'
              )}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="px-3 pb-2 flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground/40">
              Nova reads from your organization's workforce graph database
            </span>
            <span className="text-[10px] text-muted-foreground/30">
              ↵ to send
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
