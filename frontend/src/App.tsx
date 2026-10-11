import React, { useState, useEffect, useRef } from 'react';
import './index.css';

interface SourceItem {
  source_document: str;
  section_title: str;
  collection: str;
}

interface Message {
  id: string;
  sender: 'user' | 'medibot';
  text: string;
  sources?: SourceItem[];
  retrievalType?: 'hybrid_rag' | 'sql_rag' | 'rbac_denial';
  role?: string;
  timestamp: string;
}

interface DemoAccount {
  username: string;
  role: string;
  name: string;
  dept: string;
  icon: string;
  collections: string[];
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: 'dr.mehta', role: 'doctor', name: 'Dr. Mehta', dept: 'Clinical Medicine', icon: '🩺', collections: ['clinical', 'nursing', 'general'] },
  { username: 'nurse.priya', role: 'nurse', name: 'Nurse Priya', dept: 'ICU Critical Care', icon: '💉', collections: ['nursing', 'general'] },
  { username: 'billing.ravi', role: 'billing_executive', name: 'Ravi Kumar', dept: 'Billing & Insurance', icon: '📊', collections: ['billing', 'general'] },
  { username: 'tech.anand', role: 'technician', name: 'Anand Sharma', dept: 'Biomedical Eng', icon: '🔧', collections: ['equipment', 'general'] },
  { username: 'admin.sys', role: 'admin', name: 'System Admin', dept: 'Executive / IT', icon: '⚡', collections: ['clinical', 'nursing', 'billing', 'equipment', 'general'] }
];

const SAMPLE_PROMPTS: Record<string, string[]> = {
  doctor: [
    "What is the first-line treatment for acute myocardial infarction?",
    "What are the dosage guidelines for Amoxicillin in paediatric patients?",
    "Show me insurance billing codes for cardiology" // Adversarial test
  ],
  nurse: [
    "What are the ICU catheter care and infection control guidelines?",
    "What is the procedure for central line dressing change?",
    "Show me insurance billing codes and claim procedures" // Adversarial test
  ],
  billing_executive: [
    "How many billing claims were pending across departments?",
    "What is the ICD-10 code for acute STEMI and negotiated package rate?",
    "Show me ICU nursing protocols for infection control" // Adversarial test
  ],
  technician: [
    "What is the calibration schedule and maintenance guide for SterilPro 3000?",
    "Which equipment category has the highest open maintenance tickets?",
    "Show me drug formulary dosing guidelines" // Adversarial test
  ],
  admin: [
    "How many billing claims were escalated last month?",
    "Which equipment category has the most open maintenance tickets?",
    "Summarize hospital staff leave entitlement rules"
  ]
};

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

export default function App() {
  const [currentUser, setCurrentUser] = useState<DemoAccount | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [accessibleCollections, setAccessibleCollections] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSources, setShowSources] = useState<Record<string, boolean>>({});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Login handler
  const handleLogin = async (account: DemoAccount) => {
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: account.username, password: 'Password123!' })
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.access_token);
        setCurrentUser(account);
        fetchCollections(account.role);
        
        // Welcome message
        setMessages([
          {
            id: '1',
            sender: 'medibot',
            text: `Welcome **${account.name}** (${account.dept}). MediBot RBAC layer is active. You have access to collections: **[${account.collections.join(', ')}]**. How can I assist you today?`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
      }
    } catch (err) {
      console.error("Login failed:", err);
    }
  };

  const fetchCollections = async (role: string) => {
    try {
      const res = await fetch(`${API_BASE}/collections/${role}`);
      const data = await res.json();
      if (res.ok) {
        setAccessibleCollections(data.accessible_collections);
      }
    } catch (err) {
      console.error("Failed to fetch collections:", err);
    }
  };

  const handleSendMessage = async (queryText?: string) => {
    const query = queryText || inputQuery;
    if (!query.trim() || !currentUser || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question: query, role: currentUser.role })
      });

      const data = await res.json();
      if (res.ok) {
        const botMsg: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'medibot',
          text: data.answer,
          sources: data.sources,
          retrievalType: data.retrieval_type,
          role: data.role,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        const errorMsg: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'medibot',
          text: `Error: ${data.detail || 'Failed to fetch response.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'medibot',
          text: "Connection error: Could not connect to MediBot backend server (localhost:8000).",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (msgId: string) => {
    setShowSources((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  // 1. LOGIN SCREEN
  if (!currentUser) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
        <div className="glass-panel" style={{ width: '100%', maxWidth: 540, padding: 32, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🏥</div>
          <h1 style={{ fontSize: 26, fontWeight: 700, background: 'linear-gradient(to right, #38BDF8, #A855F7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: 8 }}>
            MediBot RBAC Assistant
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 24 }}>
            MediAssist Health Network - Role-Based Intelligence Portal
          </p>

          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, textAlign: 'left', fontWeight: 600 }}>
            Select Demo Staff Account to Authenticate:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.username}
                onClick={() => handleLogin(acc)}
                className="glass-button"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 18px',
                  textAlign: 'left'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <span style={{ fontSize: 24 }}>{acc.icon}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{acc.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{acc.dept} ({acc.username})</div>
                  </div>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    padding: '4px 10px',
                    borderRadius: 20,
                    background: acc.role === 'admin' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                    color: acc.role === 'admin' ? '#C084FC' : '#38BDF8',
                    border: '1px solid rgba(255,255,255,0.1)'
                  }}
                >
                  {acc.role.replace('_', ' ')}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // 2. MAIN CHAT DASHBOARD
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
      
      {/* SIDEBAR */}
      <div
        className="glass-panel"
        style={{
          width: 320,
          margin: 12,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: 20,
          borderRadius: 16
        }}
      >
        <div>
          {/* Header Branding */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            <span style={{ fontSize: 28 }}>🏥</span>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: '#F8FAFC' }}>MediBot</h2>
              <span style={{ fontSize: 11, color: '#10B981', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 500 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', display: 'inline-block' }}></span>
                RBAC Layer Active
              </span>
            </div>
          </div>

          {/* User Profile Card */}
          <div
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--border-color)',
              borderRadius: 12,
              padding: 14,
              marginBottom: 20
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 22 }}>{currentUser.icon}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{currentUser.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{currentUser.dept}</div>
              </div>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 10 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Role:</span>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  padding: '2px 8px',
                  borderRadius: 12,
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38BDF8',
                  border: '1px solid rgba(56, 189, 248, 0.3)'
                }}
              >
                {currentUser.role.replace('_', ' ')}
              </span>
            </div>
          </div>

          {/* Accessible Collections */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Accessible Collections ({accessibleCollections.length})
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {accessibleCollections.map((col) => (
                <span
                  key={col}
                  style={{
                    fontSize: 12,
                    padding: '4px 10px',
                    borderRadius: 8,
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-color)',
                    color: '#E2E8F0'
                  }}
                >
                  📁 {col}
                </span>
              ))}
            </div>
          </div>

          {/* Sample Role Prompts */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Suggested Queries ({currentUser.role}):
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {SAMPLE_PROMPTS[currentUser.role]?.map((promptText, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(promptText)}
                  style={{
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                    padding: '8px 10px',
                    color: 'var(--text-muted)',
                    fontSize: 12,
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.color = '#F8FAFC')}
                  onMouseOut={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                >
                  💬 "{promptText}"
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Switch Role Button */}
        <button
          onClick={() => { setCurrentUser(null); setToken(null); }}
          className="glass-button"
          style={{ width: '100%', marginTop: 20, fontSize: 13 }}
        >
          🔄 Switch User Role
        </button>
      </div>

      {/* CHAT MAIN WINDOW */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          margin: '12px 12px 12px 0',
          height: 'calc(100vh - 24px)'
        }}
      >
        {/* Top Bar */}
        <div
          className="glass-panel"
          style={{
            padding: '16px 24px',
            marginBottom: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderRadius: 16
          }}
        >
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>MediAssist Internal Knowledge & Analytics</h3>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Qdrant Vector Store RBAC Filter Enabled | Cross-Encoder Rerank Top-3 | SQL RAG
            </span>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <span style={{ fontSize: 12, background: 'rgba(16, 185, 129, 0.15)', color: '#10B981', padding: '4px 10px', borderRadius: 20, border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              FastAPI Connected
            </span>
          </div>
        </div>

        {/* Messages Scroll Area */}
        <div
          className="glass-panel"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: 24,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            borderRadius: 16
          }}
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="animate-fade-in"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start'
              }}
            >
              {/* Message Box */}
              <div
                style={{
                  maxWidth: '78%',
                  padding: '14px 18px',
                  borderRadius: msg.sender === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                  background: msg.sender === 'user'
                    ? 'linear-gradient(135deg, #0284C7, #2563EB)'
                    : 'rgba(30, 41, 59, 0.85)',
                  border: msg.sender === 'user' ? 'none' : '1px solid var(--border-color)',
                  color: '#F8FAFC',
                  lineHeight: 1.6,
                  fontSize: 14,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                }}
              >
                {/* Header Badge on Bot Messages */}
                {msg.sender === 'medibot' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                    <span style={{ fontSize: 14 }}>🏥</span>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#38BDF8' }}>MediBot</span>

                    {/* Retrieval Type Tag */}
                    {msg.retrievalType === 'hybrid_rag' && (
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10, background: 'rgba(56, 189, 248, 0.2)', color: '#38BDF8', border: '1px solid rgba(56, 189, 248, 0.4)' }}>
                        HYBRID RAG + RERANK
                      </span>
                    )}

                    {msg.retrievalType === 'sql_rag' && (
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10, background: 'rgba(168, 85, 247, 0.2)', color: '#C084FC', border: '1px solid rgba(168, 85, 247, 0.4)' }}>
                        SQL RAG (DB ANALYTICS)
                      </span>
                    )}

                    {msg.text.includes("don't have access") || msg.text.includes("do not have permission") ? (
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10, background: 'rgba(244, 63, 94, 0.2)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.4)' }}>
                        RBAC DENIAL
                      </span>
                    ) : null}
                  </div>
                )}

                {/* Message Body */}
                <div style={{ whitespace: 'pre-wrap' }}>{msg.text}</div>

                {/* Sources Drawer */}
                {msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <button
                      onClick={() => toggleSources(msg.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#38BDF8',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6
                      }}
                    >
                      📚 {showSources[msg.id] ? 'Hide Source Citations' : `View ${msg.sources.length} Cited Sources`}
                    </button>

                    {showSources[msg.id] && (
                      <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {msg.sources.map((src, idx) => (
                          <div
                            key={idx}
                            style={{
                              background: 'rgba(0,0,0,0.3)',
                              padding: '8px 12px',
                              borderRadius: 8,
                              fontSize: 12,
                              borderLeft: '3px solid #38BDF8'
                            }}
                          >
                            <div style={{ fontWeight: 600, color: '#F8FAFC' }}>📄 Document: {src.source_document}</div>
                            <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>Section: {src.section_title}</div>
                            <div style={{ color: '#A855F7', fontSize: 10, marginTop: 2 }}>Collection: {src.collection}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 6, textAlign: 'right' }}>
                  {msg.timestamp}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)', fontSize: 13 }}>
              <span style={{ fontSize: 18 }}>⚙️</span> MediBot processing (RBAC filter → Hybrid retrieval → Cross-encoder rerank → LLM)...
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div
          className="glass-panel"
          style={{
            padding: '12px 16px',
            marginTop: 12,
            display: 'flex',
            gap: 12,
            alignItems: 'center',
            borderRadius: 16
          }}
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder={`Ask MediBot a clinical, policy, or analytics question (${currentUser.role})...`}
            style={{
              flex: 1,
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border-color)',
              borderRadius: 10,
              padding: '12px 16px',
              color: '#F8FAFC',
              fontSize: 14,
              outline: 'none'
            }}
          />

          <button
            onClick={() => handleSendMessage()}
            disabled={loading || !inputQuery.trim()}
            className="glass-button"
            style={{
              background: 'linear-gradient(135deg, #0284C7, #2563EB)',
              border: 'none',
              padding: '12px 24px',
              fontWeight: 600,
              color: '#FFFFFF'
            }}
          >
            Send ➔
          </button>
        </div>

      </div>
    </div>
  );
}
