import { useMemo, useState } from 'react'
import './App.css'

type Citation = {
  document: string
  section: string
}

type ChatResponse = {
  answer: string
  citations: Citation[]
  confidence: number
  access_scope: string
}

type AdminMetrics = {
  total_queries: number
  denied_scope_queries: number
  blocked_injection_queries: number
  low_confidence_fallbacks: number
}

type Message = {
  id: number
  kind: 'me' | 'bot'
  text: string
  botLabel?: string
  payload?: {
    module: string
    question: string
    answer: string
    citations: string[]
  }
}

const quickPrompts: Record<string, string[]> = {
  hr: [
    'When is a medical certificate required?',
    'How many days before leave should I apply?',
  ],
  it: [
    'What is the minimum password length?',
    'How do I reset VPN credentials?',
  ],
  policy: [
    'What are the general leave rules?',
    'Who approves policy exceptions?',
  ],
  manager: [
    'How should managers approve leave?',
    'What manager workflows are documented?',
  ],
}

function App() {
  const [username, setUsername] = useState('hr_admin')
  const [password, setPassword] = useState('hr123')
  const [moduleName, setModuleName] = useState('hr')
  const [question, setQuestion] = useState('')
  const [token, setToken] = useState('')
  const [role, setRole] = useState('')
  const [loginState, setLoginState] = useState('Not logged in')
  const [messages, setMessages] = useState<Message[]>([])
  const [metrics, setMetrics] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false)
  const [toast, setToast] = useState('')

  const quickList = useMemo(() => quickPrompts[moduleName] || [], [moduleName])
  const parsedMetrics = useMemo(() => {
    if (!metrics || metrics.startsWith('Login') || metrics.startsWith('Metrics') || metrics.startsWith('Failed')) {
      return null
    }
    try {
      return JSON.parse(metrics) as AdminMetrics
    } catch {
      return null
    }
  }, [metrics])

  const pushMessage = (message: Omit<Message, 'id'>, owner = username.trim().toLowerCase()) => {
    setMessages((prev) => {
      const next = [...prev, { id: prev.length + 1, ...message }]
      localStorage.setItem(`chat_history_${owner}`, JSON.stringify(next))
      return next
    })
  }

  const normalizeHistory = (history: Message[]): Message[] => {
    return history.map((item, index) => {
      const fallbackLabel = item.payload?.module ? item.payload.module.toUpperCase() : 'BOT'
      return {
        id: index + 1,
        kind: item.kind,
        text: item.text,
        botLabel: item.kind === 'bot' ? item.botLabel || fallbackLabel : undefined,
        payload: item.payload,
      }
    })
  }

  const showToast = (text: string) => {
    setToast(text)
    window.setTimeout(() => setToast(''), 2400)
  }

  const login = async () => {
    setIsLoggingIn(true)
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })

      if (!response.ok) {
        setLoginState('Login failed')
        showToast('Login failed. Please check credentials.')
        return
      }

      const data = await response.json()
      const owner = username.trim().toLowerCase()
      const history = localStorage.getItem(`chat_history_${owner}`)
      setMessages(history ? normalizeHistory(JSON.parse(history) as Message[]) : [])
      setToken(data.access_token)
      setRole(data.role)
      setLoginState(`Logged in as ${username} (${data.role})`)
      pushMessage(
        {
          kind: 'bot',
          text: `Session ready for ${data.role}.`,
          botLabel: data.role.toUpperCase(),
        },
        owner,
      )
    } catch (error) {
      showToast('Network error while logging in.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  const askAssistant = async () => {
    if (!token) {
      pushMessage({ kind: 'bot', text: 'Please login first.' })
      return
    }
    if (!question.trim()) {
      return
    }

    const asked = question.trim()
    pushMessage({ kind: 'me', text: asked })
    setQuestion('')
    setIsAsking(true)

    try {
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question: asked, module: moduleName }),
      })

      if (!response.ok) {
        const err = await response.json()
        pushMessage({
          kind: 'bot',
          text: `Request failed: ${err.detail || response.statusText}`,
        })
        showToast('Chat request failed.')
        return
      }

      const data = (await response.json()) as ChatResponse
      const citationText = data.citations.map((item) => `${item.document} / ${item.section}`)
      pushMessage({
        kind: 'bot',
        text: data.answer,
        botLabel: moduleName.toUpperCase(),
        payload: {
          module: moduleName,
          question: asked,
          answer: data.answer,
          citations: citationText,
        },
      })
    } catch {
      showToast('Network error while asking assistant.')
    } finally {
      setIsAsking(false)
    }
  }

  const submitFeedback = async (helpful: boolean, payload: NonNullable<Message['payload']>) => {
    if (!token) {
      return
    }

    const response = await fetch('/api/v1/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        module: payload.module,
        question: payload.question,
        answer: payload.answer,
        citations: payload.citations,
        helpful,
        comment: '',
      }),
    })
    if (!response.ok) {
      showToast('Feedback save failed.')
      return
    }
    showToast('Feedback saved.')
  }

  const fetchMetrics = async () => {
    if (!token) {
      setMetrics('Login required.')
      return
    }

    setIsLoadingMetrics(true)
    try {
      const response = await fetch('/api/v1/admin/metrics', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) {
        setMetrics('Metrics available only for admin users.')
        return
      }

      const data = await response.json()
      setMetrics(JSON.stringify(data, null, 2))
    } catch {
      setMetrics('Failed to load metrics.')
    } finally {
      setIsLoadingMetrics(false)
    }
  }

  const clearHistory = () => {
    const owner = username.trim().toLowerCase()
    localStorage.removeItem(`chat_history_${owner}`)
    setMessages([])
  }

  return (
    <div className="pageShell">
      <div className="sideDecor left" aria-hidden="true">
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <rect x="16" y="10" width="32" height="44" rx="6" />
          <circle cx="32" cy="24" r="7" />
          <path d="M23 41c2.5-4.5 6.5-6.5 9-6.5S38.5 36.5 41 41" />
        </svg>
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <rect x="12" y="22" width="40" height="28" rx="4" />
          <path d="M24 22v-6h16v6" />
          <path d="M12 34h40" />
        </svg>
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <rect x="14" y="12" width="36" height="40" rx="4" />
          <path d="M23 12v-4h18v4" />
          <path d="M22 24h20M22 31h20M22 38h14" />
        </svg>
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <rect x="10" y="18" width="44" height="26" rx="3" />
          <path d="M24 50h16" />
          <path d="M28 44v6M36 44v6" />
        </svg>
      </div>
      <div className="sideDecor right" aria-hidden="true">
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <rect x="15" y="10" width="34" height="44" rx="2" />
          <path d="M24 18h4M36 18h4M24 26h4M36 26h4M24 34h4M36 34h4M24 42h4M36 42h4" />
          <path d="M30 54v-8h4v8" />
        </svg>
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <path d="M14 46h36" />
          <path d="M18 46V22h28v24" />
          <path d="M24 22v-7h16v7" />
          <circle cx="28" cy="33" r="2" />
          <circle cx="36" cy="33" r="2" />
        </svg>
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <circle cx="24" cy="22" r="6" />
          <circle cx="40" cy="22" r="6" />
          <path d="M16 40c2-5 5.5-8 8-8s6 3 8 8" />
          <path d="M32 40c2-5 5.5-8 8-8s6 3 8 8" />
        </svg>
        <svg className="sideIcon" viewBox="0 0 64 64" fill="none">
          <rect x="14" y="16" width="36" height="26" rx="4" />
          <path d="M22 48h20" />
          <path d="M27 42v6M37 42v6" />
        </svg>
      </div>

      <div className="app">
        {toast ? <div className="toast">{toast}</div> : null}
        <header className="hero">
        <div className="heroTop">
          <div>
            <p className="eyebrow">Enterprise RAG Console</p>
            <h1>Private Company Assistant</h1>
            <p>Role-aware chat with citations, feedback loops, and admin signals.</p>
          </div>
          <div className="heroPills">
            <span className="pill">role={role || 'guest'}</span>
          </div>
        </div>
        <div className="heroStats">
          <div className="statCard">
            <strong>{messages.length}</strong>
            <span>Messages</span>
          </div>
          <div className="statCard">
            <strong>{moduleName.toUpperCase()}</strong>
            <span>Current Module</span>
          </div>
          <div className="statCard">
            <strong>{token ? 'Active' : 'Idle'}</strong>
            <span>Session State</span>
          </div>
        </div>
      </header>

        <div className="layout">
        <aside className="sidebar">
          <p className="sectionTitle">Session</p>
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button onClick={login} disabled={isLoggingIn}>{isLoggingIn ? 'Logging in...' : 'Login'}</button>
          <button className="secondary" onClick={clearHistory}>Clear Chat History</button>
          <p className="meta">{loginState}</p>

          <p className="sectionTitle">Module</p>
          <select value={moduleName} onChange={(e) => setModuleName(e.target.value)}>
            <option value="hr">hr</option>
            <option value="it">it</option>
            <option value="policy">policy</option>
            <option value="manager">manager</option>
          </select>

          <div className="roleDeck">
            <button
              className={`roleTile ${moduleName === 'policy' ? 'active' : ''}`}
              onClick={() => setModuleName('policy')}
            >
              <span className="roleCode">EMPLOYEE</span>
              <strong>Employee Desk</strong>
              <small>Leave rules, handbook basics, policy lookup.</small>
            </button>
            <button
              className={`roleTile ${moduleName === 'hr' ? 'active' : ''}`}
              onClick={() => setModuleName('hr')}
            >
              <span className="roleCode">HR</span>
              <strong>HR Desk</strong>
              <small>Approvals, certificates, compliance workflow notes.</small>
            </button>
            <button
              className={`roleTile ${moduleName === 'manager' ? 'active' : ''}`}
              onClick={() => setModuleName('manager')}
            >
              <span className="roleCode">MANAGER</span>
              <strong>Manager Desk</strong>
              <small>Escalations, approvals, and team-level governance.</small>
            </button>
          </div>

          <div className="quick">
            {quickList.map((prompt) => (
              <button key={prompt} className="quickBtn" onClick={() => setQuestion(prompt)}>
                {prompt}
              </button>
            ))}
          </div>

          <p className="sectionTitle">Admin</p>
          <button className="secondary" onClick={fetchMetrics} disabled={isLoadingMetrics}>
            {isLoadingMetrics ? 'Loading Metrics...' : 'Fetch Metrics'}
          </button>
          <pre className="metrics">{metrics}</pre>
        </aside>

        <main className="chatArea">
          <div className="kpiStrip">
            <div className="kpi">
              <span>Total</span>
              <strong>{parsedMetrics?.total_queries ?? '-'}</strong>
            </div>
            <div className="kpi">
              <span>Denied</span>
              <strong>{parsedMetrics?.denied_scope_queries ?? '-'}</strong>
            </div>
            <div className="kpi">
              <span>Blocked</span>
              <strong>{parsedMetrics?.blocked_injection_queries ?? '-'}</strong>
            </div>
            <div className="kpi">
              <span>Fallbacks</span>
              <strong>{parsedMetrics?.low_confidence_fallbacks ?? '-'}</strong>
            </div>
          </div>

          <div className="messages">
            {messages.length === 0 ? (
              <div className="emptyState">
                Ask your first question to start a traceable conversation with citations.
              </div>
            ) : null}
            {messages.map((msg) => (
              <div key={msg.id} className={`msgRow ${msg.kind === 'me' ? 'meRow' : 'botRow'}`}>
                <div className={`avatar ${msg.kind === 'me' ? 'avatarMe' : 'avatarBot'}`}>
                  {msg.kind === 'me' ? 'YOU' : msg.botLabel || 'BOT'}
                </div>
                <div className={`message ${msg.kind === 'me' ? 'me' : 'bot'}`}>
                  <div className="msgText">{msg.text}</div>
                  {msg.kind === 'bot' && msg.payload ? (
                    <div className="feedbackRow">
                      <button className="secondary small" onClick={() => submitFeedback(true, msg.payload!)}>Helpful</button>
                      <button className="secondary small" onClick={() => submitFeedback(false, msg.payload!)}>Not helpful</button>
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a policy or process question..."
          />
          <button onClick={askAssistant} disabled={isAsking}>{isAsking ? 'Asking...' : 'Ask Assistant'}</button>
        </main>
        </div>
      </div>
    </div>
  )
}

export default App
