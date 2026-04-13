import { useEffect, useMemo, useState } from 'react'
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

type Message = {
  id: number
  kind: 'me' | 'bot'
  text: string
  meta?: string
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
  const [health, setHealth] = useState('API status unknown')
  const [healthOk, setHealthOk] = useState(false)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false)
  const [toast, setToast] = useState('')

  const quickList = useMemo(() => quickPrompts[moduleName] || [], [moduleName])

  const pushMessage = (message: Omit<Message, 'id'>, owner = username.trim().toLowerCase()) => {
    setMessages((prev) => {
      const next = [...prev, { id: prev.length + 1, ...message }]
      localStorage.setItem(`chat_history_${owner}`, JSON.stringify(next))
      return next
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
      setMessages(history ? JSON.parse(history) : [])
      setToken(data.access_token)
      setRole(data.role)
      setLoginState(`Logged in as ${username} (${data.role})`)
      pushMessage(
        {
          kind: 'bot',
          text: `Session ready for ${data.role}.`,
          meta: 'You can ask questions now.',
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
    pushMessage({ kind: 'me', text: asked, meta: `module=${moduleName}` })
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
        meta: `confidence=${data.confidence.toFixed(2)} | scope=${data.access_scope} | citations=${citationText.join('; ') || 'none'}`,
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

  const checkHealth = async () => {
    const response = await fetch('/api/v1/health')
    setHealth(response.ok ? 'API online' : 'API unavailable')
    setHealthOk(response.ok)
  }

  useEffect(() => {
    checkHealth()
  }, [])

  const clearHistory = () => {
    const owner = username.trim().toLowerCase()
    localStorage.removeItem(`chat_history_${owner}`)
    setMessages([])
  }

  return (
    <div className="app">
      {toast ? <div className="toast">{toast}</div> : null}
      <header className="hero">
        <h1>Private Company Assistant</h1>
        <p>React console for role-aware chat, citations, feedback, and admin metrics.</p>
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
          <span className={`pill ${healthOk ? 'ok' : 'bad'}`}>{health}</span>
          <span className="pill">role={role || 'guest'}</span>

          <div className="messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.kind === 'me' ? 'me' : 'bot'}`}>
                <div>{msg.text}</div>
                {msg.meta ? <div className="meta">{msg.meta}</div> : null}
                {msg.kind === 'bot' && msg.payload ? (
                  <div className="feedbackRow">
                    <button className="secondary small" onClick={() => submitFeedback(true, msg.payload!)}>Helpful</button>
                    <button className="secondary small" onClick={() => submitFeedback(false, msg.payload!)}>Not helpful</button>
                  </div>
                ) : null}
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
  )
}

export default App
