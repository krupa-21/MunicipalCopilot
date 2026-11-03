import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  FileText,
  GitCompare,
  Sparkles,
  ShieldCheck,
  Upload,
  Trash2,
  Eye,
  ExternalLink,
  X,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Building2,
  Send,
  RefreshCw,
  FileCheck,
  ChevronRight,
  Shield
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const DEPARTMENTS = [
  'All Departments',
  'Solid Waste Management',
  'Health & Hospital',
  'Roads & Buildings',
  'Water & Drainage',
  'Revenue & Tax',
  'General Administration'
];

const DOC_TYPES = [
  'All Types',
  'Circular',
  'Policy',
  'Tender',
  'Manual',
  'Office Order'
];

const SAMPLE_QUERIES = [
  'What is the target response time for high-priority complaints?',
  'What are the escalation deadlines if a grievance is unresolved?',
  'What are the responsibilities for complaint verification and closure?',
  'What are the record retention and personal data protection rules?'
];

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [userRole, setUserRole] = useState('Admin (Commissioner)');
  const [backendOnline, setBackendOnline] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  // Chat State
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      text: 'Namaste! I am the **Ahmedabad Municipal Corporation (AMC) Knowledge Copilot**. I assist municipal teams in searching, analyzing, and acting upon approved circulars, tenders, and policies with strict source citations.\n\nHow can I help your department today?',
      sources: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [selectedDept, setSelectedDept] = useState('All Departments');
  const [selectedDocType, setSelectedDocType] = useState('All Types');
  const chatBottomRef = useRef(null);

  // Ingestion State
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadDept, setUploadDept] = useState('Solid Waste Management');
  const [uploadDocType, setUploadDocType] = useState('Circular');
  const [uploadVersion, setUploadVersion] = useState('1.0');
  const [uploadIssueDate, setUploadIssueDate] = useState(new Date().toISOString().split('T')[0]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  // Document Preview Modal
  const [previewModal, setPreviewModal] = useState({
    isOpen: false,
    filename: '',
    title: '',
    page: 1
  });

  // Diff / Comparison State
  const [diffDoc1, setDiffDoc1] = useState('');
  const [diffDoc2, setDiffDoc2] = useState('');
  const [isComparing, setIsComparing] = useState(false);
  const [diffResult, setDiffResult] = useState(null);

  // Summarizer State
  const [summarizeDoc, setSummarizeDoc] = useState('');
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryResult, setSummaryResult] = useState(null);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  // Check Backend Health
  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/`, { method: 'GET' });
      if (res.ok) {
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch {
      setBackendOnline(false);
    }
  };

  // Fetch Documents
  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
        if (data.documents && data.documents.length > 0) {
          if (!diffDoc1) setDiffDoc1(data.documents[0].filename);
          if (!diffDoc2 && data.documents.length > 1) setDiffDoc2(data.documents[1].filename);
          if (!summarizeDoc) setSummarizeDoc(data.documents[0].filename);
        }
      }
    } catch (e) {
      console.error('Failed to load documents:', e);
    } finally {
      setLoadingDocs(false);
    }
  };

  // Fetch Audit Logs
  const fetchAuditLogs = async () => {
    setLoadingAudit(true);
    try {
      const res = await fetch(`${API_BASE}/audit-logs`);
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data.logs || []);
      }
    } catch (e) {
      console.error('Failed to load audit logs:', e);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    checkHealth();
    fetchDocuments();
    // Heartbeat check every 60 seconds to reduce terminal clutter
    const interval = setInterval(checkHealth, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeTab === 'audit') {
      fetchAuditLogs();
    }
  }, [activeTab]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Enforce Role-Based Tab Permissions
  useEffect(() => {
    if (userRole === 'Desk Assistant' && ['diff', 'audit'].includes(activeTab)) {
      setActiveTab('chat');
    }
  }, [userRole, activeTab]);

  // Handle Ask Query
  const handleSendQuery = async (queryText) => {
    const textToSend = queryText || chatInput;
    if (!textToSend.trim() || isQuerying) return;

    const userMsg = {
      id: Date.now(),
      role: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setIsQuerying(true);

    try {
      const params = new URLSearchParams({
        query: textToSend,
        user_role: userRole
      });
      if (selectedDept !== 'All Departments') {
        params.append('department', selectedDept);
      }
      if (selectedDocType !== 'All Types') {
        params.append('document_type', selectedDocType);
      }

      const res = await fetch(`${API_BASE}/ask?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: data.answer || 'No answer generated.',
        sources: data.sources || [],
        responseTime: data.response_time_ms,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          text: `⚠️ Error communicating with Copilot backend: ${err.message}. Please verify the backend service is running.`,
          sources: [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  // Handle Document Upload
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) {
      alert('Please select a file to upload.');
      return;
    }

    setIsUploading(true);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('department', uploadDept);
    formData.append('document_type', uploadDocType);
    formData.append('version', uploadVersion);
    formData.append('issue_date', uploadIssueDate);

    try {
      const res = await fetch(`${API_BASE}/upload-pdf`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail?.message || data.detail || 'Upload failed');
      }

      setUploadStatus({
        type: 'success',
        message: `Document "${data.filename}" indexed successfully (${data.total_chunks} chunks, ${data.total_pages} pages).`
      });
      setUploadFile(null);
      fetchDocuments();
    } catch (err) {
      setUploadStatus({
        type: 'error',
        message: err.message
      });
    } finally {
      setIsUploading(false);
    }
  };

  // Handle Delete Document
  const handleDeleteDocument = async (filename, originalName) => {
    if (!window.confirm(`Are you sure you want to delete "${originalName}"?`)) return;

    try {
      const res = await fetch(`${API_BASE}/documents/${filename}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchDocuments();
      } else {
        alert('Failed to delete document.');
      }
    } catch (err) {
      alert(`Error deleting document: ${err.message}`);
    }
  };

  // Handle Document Comparison
  const handleRunComparison = async () => {
    if (!diffDoc1 || !diffDoc2) {
      alert('Please select two documents to compare.');
      return;
    }
    if (diffDoc1 === diffDoc2) {
      alert('Please select two distinct document versions.');
      return;
    }

    setIsComparing(true);
    setDiffResult(null);

    try {
      const params = new URLSearchParams({
        filename1: diffDoc1,
        filename2: diffDoc2
      });

      const res = await fetch(`${API_BASE}/test-structured-comparison?${params.toString()}`, {
        method: 'POST'
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Comparison request failed');
      }

      const data = await res.json();
      setDiffResult(data);
    } catch (err) {
      alert(`Comparison error: ${err.message}`);
    } finally {
      setIsComparing(false);
    }
  };

  // Handle Document Summarization
  const handleRunSummarize = async () => {
    if (!summarizeDoc) {
      alert('Please select a document to summarize.');
      return;
    }

    setIsSummarizing(true);
    setSummaryResult(null);

    try {
      const res = await fetch(`${API_BASE}/summarize/${summarizeDoc}`, {
        method: 'POST'
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Summarization request failed');
      }

      const data = await res.json();
      setSummaryResult(data);
    } catch (err) {
      alert(`Summarization error: ${err.message}`);
    } finally {
      setIsSummarizing(false);
    }
  };

  // Helper to open document preview
  const openPreview = (filename, originalName, page = 1) => {
    setPreviewModal({
      isOpen: true,
      filename,
      title: originalName || filename,
      page: page || 1
    });
  };


  // Admin: delete a single audit log
  const handleDeleteLog = async (logId) => {
    if (!window.confirm(`Delete audit log #${logId}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/audit-logs/${logId}`, { method: 'DELETE' });
      if (res.ok) fetchAuditLogs();
      else alert('Failed to delete log entry.');
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  // Admin: clear all audit logs
  const handleClearAllLogs = async () => {
    if (!window.confirm('Clear ALL audit logs? This cannot be undone.')) return;
    try {
      const res = await fetch(`${API_BASE}/audit-logs`, { method: 'DELETE' });
      if (res.ok) setAuditLogs([]);
      else alert('Failed to clear logs.');
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  // Render citation pills in text

  const renderMessageContent = (text, sources) => {
    // Regex for citation pattern like [S1], [S2]
    const parts = text.split(/(\[S\d+\])/g);
    return (
      <div style={{ whiteSpace: 'pre-wrap' }}>
        {parts.map((part, index) => {
          const match = part.match(/\[S(\d+)\]/);
          if (match) {
            const sourceIndex = parseInt(match[1], 10) - 1;
            const source = sources && sources[sourceIndex];
            return (
              <button
                key={index}
                className="citation-pill"
                title={source ? `${source.document} (Page ${source.page})` : 'Source Citation'}
                onClick={() => {
                  if (source) {
                    // Find document in list or use filename
                    const docObj = documents.find((d) => d.original_filename === source.document);
                    const fileToOpen = docObj ? docObj.filename : source.document;
                    openPreview(fileToOpen, source.document, source.page);
                  }
                }}
              >
                {part}
              </button>
            );
          }
          return part;
        })}
      </div>
    );
  };

  return (
    <div>
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="amc-logo-badge">AMC</div>
          <div className="header-titles">
            <h1>
              Ahmedabad Municipal Corporation
              <span className="badge badge-teal" style={{ fontSize: '10px' }}>
                SSIP 2.0 • SEVA FIRST
              </span>
            </h1>
            <p>AI-Powered Municipal Operations and Knowledge Copilot</p>
          </div>
        </div>

        <div className="header-right">
          <div className={`status-badge ${backendOnline ? 'online' : 'offline'}`}>
            <span className="status-dot"></span>
            {backendOnline ? 'AI Service Connected' : 'Backend Offline'}
          </div>

          <div className="role-selector">
            <Shield size={14} color="currentColor" />
            <span>Role:</span>
            <select
              className="role-select"
              value={userRole}
              onChange={(e) => setUserRole(e.target.value)}
            >
              <option value="Admin (Commissioner)">Admin (Commissioner)</option>
              <option value="Department Officer">Department Officer</option>
              <option value="Desk Assistant">Desk Assistant</option>
            </select>
            <span
              className={`badge ${
                userRole.includes('Admin')
                  ? 'badge-teal'
                  : userRole === 'Department Officer'
                  ? 'badge-blue'
                  : 'badge-amber'
              }`}
              style={{ fontSize: '11px', whiteSpace: 'nowrap' }}
            >
              {userRole.includes('Admin')
                ? 'Full Control'
                : userRole === 'Department Officer'
                ? 'Officer Access'
                : 'Inquiries & Summaries'}
            </span>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="nav-bar">
        <button
          className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <MessageSquare size={16} />
          Copilot Q&A
        </button>

        <button
          className={`nav-tab ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          <FileText size={16} />
          Document Repository ({documents.length})
        </button>

        {userRole !== 'Desk Assistant' && (
          <button
            className={`nav-tab ${activeTab === 'diff' ? 'active' : ''}`}
            onClick={() => setActiveTab('diff')}
          >
            <GitCompare size={16} />
            Policy Version Diff
          </button>
        )}

        <button
          className={`nav-tab ${activeTab === 'summarize' ? 'active' : ''}`}
          onClick={() => setActiveTab('summarize')}
        >
          <Sparkles size={16} />
          Document Summarizer
        </button>

        {userRole !== 'Desk Assistant' && (
          <button
            className={`nav-tab ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <ShieldCheck size={16} />
            Governance & Audit Trail
          </button>
        )}
      </nav>

      {/* App Body Content */}
      <main className="app-content">
        {/* TAB 1: COPILOT CHAT */}
        {activeTab === 'chat' && (
          <div className="chat-container">
            <div className="chat-main">
              {/* Filter Bar */}
              <div className="chat-filter-bar">
                <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontWeight: 600 }}>
                  FILTER BY:
                </span>
                <select
                  className="select"
                  style={{ width: 'auto', padding: '4px 10px' }}
                  value={selectedDept}
                  onChange={(e) => setSelectedDept(e.target.value)}
                >
                  {DEPARTMENTS.map((dept) => (
                    <option key={dept} value={dept}>
                      {dept}
                    </option>
                  ))}
                </select>

                <select
                  className="select"
                  style={{ width: 'auto', padding: '4px 10px' }}
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                >
                  {DOC_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>

                <span style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--text-dim)' }}>
                  Grounded strictly in approved AMC circulars
                </span>
              </div>

              {/* Message List */}
              <div className="chat-messages">
                {messages.map((msg) => (
                  <div key={msg.id} className={`chat-message ${msg.role}`}>
                    <div className="message-avatar">
                      {msg.role === 'user' ? 'U' : 'AMC'}
                    </div>
                    <div className="message-bubble">
                      {renderMessageContent(msg.text, msg.sources)}

                      {/* Cited Sources Box */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="sources-box">
                          <span className="sources-title">Verified Citations:</span>
                          {msg.sources.map((s, idx) => {
                            const docObj = documents.find((d) => d.original_filename === s.document);
                            const fileToOpen = docObj ? docObj.filename : s.document;
                            return (
                              <div
                                key={idx}
                                className="source-chip"
                                onClick={() => openPreview(fileToOpen, s.document, s.page)}
                                title="Click to view cited page in PDF viewer"
                              >
                                <FileCheck size={12} color="currentColor" />
                                <span>{s.source_id}: {s.document}</span>
                                <span className="badge badge-blue">Page {s.page}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {msg.responseTime && (
                        <div style={{ marginTop: '6px', fontSize: '11px', color: 'var(--text-dim)' }}>
                          ⏱️ Processed in {msg.responseTime} ms • Grounded Verification OK
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {isQuerying && (
                  <div className="chat-message assistant">
                    <div className="message-avatar">AMC</div>
                    <div className="message-bubble" style={{ color: 'var(--text-muted)' }}>
                      🔍 Retrieving municipal documents and verifying evidence...
                    </div>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Chat Input */}
              <div className="chat-input-area">
                <form
                  className="chat-input-wrapper"
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendQuery();
                  }}
                >
                  <input
                    type="text"
                    className="input"
                    placeholder="Ask about circular rules, response SLAs, officer duties, or tender clauses..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    disabled={isQuerying}
                  />
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isQuerying || !chatInput.trim()}
                  >
                    <Send size={15} />
                    Ask Copilot
                  </button>
                </form>
              </div>
            </div>

            {/* Sidebar with Quick Queries */}
            <div className="chat-sidebar">
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    <Sparkles size={16} color="currentColor" />
                    Sample Municipal Queries
                  </div>
                </div>
                <div className="prompt-chips">
                  {SAMPLE_QUERIES.map((q, idx) => (
                    <button
                      key={idx}
                      className="prompt-chip"
                      onClick={() => handleSendQuery(q)}
                      disabled={isQuerying}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              <div className="card" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                <div className="card-title" style={{ fontSize: '13px', marginBottom: '8px' }}>
                  <ShieldCheck size={14} color="var(--heritage-green)" />
                  Grounded Integrity Safeguards
                </div>
                <p>• Zero hallucination policy: Unsubstantiated claims are rejected.</p>
                <p style={{ marginTop: '6px' }}>• Every response links directly to the cited circular and page number.</p>
                <p style={{ marginTop: '6px' }}>• Multi-version awareness distinguishes revised SLA rules from previous drafts.</p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: DOCUMENT REPOSITORY */}
        {activeTab === 'documents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Upload Section - Admin Only */}
            {userRole.includes('Admin') ? (
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Upload size={18} color="currentColor" />
                  Ingest Municipal Document
                </div>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Supports PDF, DOCX, TXT with page-level chunking
                </span>
              </div>

              <form onSubmit={handleUpload}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Select File *
                    </label>
                    <input
                      type="file"
                      className="input"
                      accept=".pdf,.docx,.txt"
                      onChange={(e) => setUploadFile(e.target.files[0])}
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Department
                    </label>
                    <select
                      className="select"
                      value={uploadDept}
                      onChange={(e) => setUploadDept(e.target.value)}
                    >
                      {DEPARTMENTS.filter((d) => d !== 'All Departments').map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Document Type
                    </label>
                    <select
                      className="select"
                      value={uploadDocType}
                      onChange={(e) => setUploadDocType(e.target.value)}
                    >
                      {DOC_TYPES.filter((t) => t !== 'All Types').map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Version / Number
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={uploadVersion}
                      onChange={(e) => setUploadVersion(e.target.value)}
                      placeholder="e.g. 1.0 or AMC/2026/04"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Issue Date
                    </label>
                    <input
                      type="date"
                      className="input"
                      value={uploadIssueDate}
                      onChange={(e) => setUploadIssueDate(e.target.value)}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isUploading || !uploadFile}
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw size={14} className="animate-spin" />
                        Extracting & Embedding...
                      </>
                    ) : (
                      <>
                        <Upload size={14} />
                        Index into Municipal Knowledge Base
                      </>
                    )}
                  </button>

                  {uploadStatus && (
                    <div
                      style={{
                        fontSize: '13px',
                        color: uploadStatus.type === 'success' ? 'var(--emerald-light)' : 'var(--rose)'
                      }}
                    >
                      {uploadStatus.message}
                    </div>
                  )}
                </div>
              </form>
            </div>
            ) : (
              <div className="card" style={{ padding: '16px 20px', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Shield size={18} color="currentColor" />
                    <span style={{ fontSize: '13px', color: 'var(--text-main)' }}>
                      Current Role: <strong>{userRole}</strong> (Read-Only Repository Access). Document ingestion and removal are restricted to <strong>Admin (Commissioner)</strong>.
                    </span>
                  </div>
                  <span className="badge badge-blue">Read-Only Mode</span>
                </div>
              </div>
            )}

            {/* Documents Table */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <FileText size={18} color="var(--heritage-green)" />
                  Approved Circulars & Documents ({documents.length})
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={fetchDocuments}
                  disabled={loadingDocs}
                >
                  <RefreshCw size={13} />
                  Refresh
                </button>
              </div>

              {documents.length === 0 ? (
                <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No documents found in knowledge base. Upload circulars to begin.
                </div>
              ) : (
                <div className="table-wrapper">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Document Title</th>
                        <th>Department</th>
                        <th>Type</th>
                        <th>Version</th>
                        <th>Pages</th>
                        <th>Size</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc) => (
                        <tr key={doc.filename}>
                          <td style={{ fontWeight: 600 }}>{doc.original_filename}</td>
                          <td>
                            <span className="badge badge-teal">{doc.department}</span>
                          </td>
                          <td>
                            <span className="badge badge-blue">{doc.document_type}</span>
                          </td>
                          <td>{doc.version || '1.0'}</td>
                          <td>{doc.total_pages}</td>
                          <td>{doc.file_size_kb} KB</td>
                          <td>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                onClick={() => openPreview(doc.filename, doc.original_filename, 1)}
                              >
                                <Eye size={12} />
                                View
                              </button>
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                onClick={() => {
                                  setSummarizeDoc(doc.filename);
                                  setActiveTab('summarize');
                                }}
                              >
                                <Sparkles size={12} />
                                Summarize
                              </button>
                              {userRole.includes('Admin') && (
                                <button
                                  className="btn btn-danger"
                                  style={{ padding: '4px 8px', fontSize: '11px' }}
                                  onClick={() => handleDeleteDocument(doc.filename, doc.original_filename)}
                                >
                                  <Trash2 size={12} />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: POLICY VERSION DIFF */}
        {activeTab === 'diff' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <GitCompare size={18} color="var(--terracotta)" />
                  Policy Version Difference & Amendment Analysis
                </div>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Deep comparison of circular rules across 12 structured dimensions
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '16px', alignItems: 'end' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Document A (Base / Previous Version)
                  </label>
                  <select
                    className="select"
                    value={diffDoc1}
                    onChange={(e) => setDiffDoc1(e.target.value)}
                  >
                    {documents.map((d) => (
                      <option key={d.filename} value={d.filename}>
                        {d.original_filename}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Document B (Amended / Revised Version)
                  </label>
                  <select
                    className="select"
                    value={diffDoc2}
                    onChange={(e) => setDiffDoc2(e.target.value)}
                  >
                    {documents.map((d) => (
                      <option key={d.filename} value={d.filename}>
                        {d.original_filename}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={handleRunComparison}
                  disabled={isComparing || !diffDoc1 || !diffDoc2}
                  style={{ height: '38px' }}
                >
                  {isComparing ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      Analyzing Differences...
                    </>
                  ) : (
                    <>
                      <GitCompare size={14} />
                      Compare Policy Versions
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Diff Results Display */}
            {diffResult && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {/* Priority / SLA Shift Matrix */}
                {diffResult.priority_and_response_time_comparison?.comparisons && (
                  <div className="card">
                    <div className="card-header">
                      <div className="card-title">
                        <Clock size={16} color="currentColor" />
                        Priority Categories & Response SLA Shift Analysis
                      </div>
                    </div>
                    <div className="table-wrapper">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Status</th>
                            <th>Previous Category & Target</th>
                            <th>Revised Category & Target</th>
                            <th>Policy Analysis</th>
                          </tr>
                        </thead>
                        <tbody>
                          {diffResult.priority_and_response_time_comparison.comparisons.map((c, i) => (
                            <tr key={i}>
                              <td>
                                <span className={`badge ${c.change_type === 'unchanged' ? 'badge-teal' : 'badge-amber'}`}>
                                  {c.change_type.replace(/_/g, ' ')}
                                </span>
                              </td>
                              <td>
                                <strong>{c.previous_category || '—'}</strong>: {c.previous_response_target || '—'}
                              </td>
                              <td>
                                <strong>{c.revised_category || '—'}</strong>: {c.revised_response_target || '—'}
                              </td>
                              <td style={{ color: 'var(--text-muted)' }}>{c.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Categorized Changes */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <FileCheck size={16} color="var(--heritage-green)" />
                      Detailed Policy Clause Comparison
                    </div>
                  </div>

                  <div className="diff-grid">
                    {diffResult.comparison?.fields &&
                      Object.entries(diffResult.comparison.fields).map(([fieldName, fieldData]) => {
                        const hasChanges =
                          (fieldData.modified && fieldData.modified.length > 0) ||
                          (fieldData.added && fieldData.added.length > 0) ||
                          (fieldData.removed && fieldData.removed.length > 0);

                        if (!hasChanges) return null;

                        return (
                          <div key={fieldName} className="diff-item modified">
                            <div style={{ fontWeight: 700, fontSize: '14px', marginBottom: '8px', textTransform: 'capitalize' }}>
                              {fieldName.replace(/_/g, ' ')}
                            </div>

                            {fieldData.modified?.map((m, idx) => (
                              <div key={idx} style={{ marginBottom: '10px', fontSize: '12px' }}>
                                <div style={{ color: 'var(--terracotta)', fontWeight: 600 }}>• Modified Requirement:</div>
                                <div style={{ color: 'var(--text-dim)', textDecoration: 'line-through' }}>
                                  Old: {m.previous}
                                </div>
                                <div style={{ color: 'var(--text-heading)', marginTop: '2px' }}>
                                  New: {m.revised}
                                </div>
                                <div style={{ color: 'var(--text-dim)', fontStyle: 'italic', marginTop: '2px' }}>
                                  Reason: {m.reason}
                                </div>
                              </div>
                            ))}

                            {fieldData.added?.map((a, idx) => (
                              <div key={idx} style={{ marginBottom: '8px', fontSize: '12px' }}>
                                <div style={{ color: 'var(--heritage-green)', fontWeight: 600 }}>+ Added Obligation:</div>
                                <div>{a.requirement || a}</div>
                              </div>
                            ))}

                            {fieldData.removed?.map((r, idx) => (
                              <div key={idx} style={{ marginBottom: '8px', fontSize: '12px' }}>
                                <div style={{ color: 'var(--status-danger)', fontWeight: 600 }}>- Removed Clause:</div>
                                <div>{r.requirement || r}</div>
                              </div>
                            ))}
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: DOCUMENT SUMMARIZER */}
        {activeTab === 'summarize' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Sparkles size={18} color="currentColor" />
                  AI Document Summarizer
                </div>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Extract structured municipal summaries in 5 dimensions
                </span>
              </div>

              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <select
                  className="select"
                  style={{ maxWidth: '400px' }}
                  value={summarizeDoc}
                  onChange={(e) => setSummarizeDoc(e.target.value)}
                >
                  {documents.map((d) => (
                    <option key={d.filename} value={d.filename}>
                      {d.original_filename}
                    </option>
                  ))}
                </select>

                <button
                  className="btn btn-primary"
                  onClick={handleRunSummarize}
                  disabled={isSummarizing || !summarizeDoc}
                >
                  {isSummarizing ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      Generating Structured Summary...
                    </>
                  ) : (
                    <>
                      <Sparkles size={14} />
                      Generate Summary
                    </>
                  )}
                </button>
              </div>
            </div>

            {summaryResult && (
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    <FileCheck size={16} color="var(--heritage-green)" />
                    Structured Municipal Summary: {summaryResult.filename}
                  </div>
                  <span className="badge badge-teal">
                    {summaryResult.total_pages} Pages Processed
                  </span>
                </div>
                <div
                  style={{
                    whiteSpace: 'pre-wrap',
                    lineHeight: '1.7',
                    fontSize: '14px',
                    color: 'var(--text-main)',
                    background: 'var(--bg-subtle)',
                    padding: '20px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-color)'
                  }}
                >
                  {summaryResult.summary}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 5: GOVERNANCE & AUDIT TRAIL */}
        {activeTab === 'audit' && (
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <ShieldCheck size={18} color="var(--heritage-green)" />
                Administrative Compliance & Query Audit Trail
              </div>
              <button
                className="btn btn-secondary"
                onClick={fetchAuditLogs}
                disabled={loadingAudit}
              >
                <RefreshCw size={13} />
                Refresh Logs
              </button>
              {userRole.includes('Admin') && (
                <button
                  className="btn btn-danger"
                  onClick={handleClearAllLogs}
                  style={{ fontSize: '12px', padding: '5px 10px' }}
                >
                  <Trash2 size={13} />
                  Clear All Logs
                </button>
              )}
            </div>

            {auditLogs.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                No queries logged yet. Queries asked through the Copilot will be recorded here for compliance review.
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Timestamp</th>
                      <th>User Role</th>
                      <th>Query</th>
                      <th>Answer Snippet</th>
                      <th>Citations</th>
                      <th>Response Time</th>
                      <th>Status</th>
                      {userRole.includes('Admin') && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td>#{log.id}</td>
                        <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{log.timestamp}</td>
                        <td>
                          <span className="badge badge-blue">{log.user_role}</span>
                        </td>
                        <td style={{ fontWeight: 600 }}>{log.query}</td>
                        <td style={{ maxWidth: '300px', fontSize: '12px', color: 'var(--text-muted)' }}>
                          {log.answer_preview}
                        </td>
                        <td style={{ fontSize: '11px', color: 'var(--primary-light)' }}>
                          {log.sources}
                        </td>
                        <td>{log.response_time_ms} ms</td>
                        <td>
                          <span className={`badge ${log.status === 'SUCCESS' ? 'badge-teal' : 'badge-amber'}`}>
                            {log.status}
                          </span>
                        </td>
                        {userRole.includes('Admin') && (
                          <td>
                            <button
                              className="btn btn-danger"
                              style={{ padding: '3px 8px', fontSize: '11px' }}
                              onClick={() => handleDeleteLog(log.id)}
                              title="Delete this log entry"
                            >
                              <Trash2 size={11} />
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      {/* DOCUMENT PREVIEW MODAL */}
      {previewModal.isOpen && (
        <div className="modal-overlay" onClick={() => setPreviewModal({ isOpen: false, filename: '', title: '', page: 1 })}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileText size={18} color="currentColor" />
                <span style={{ fontWeight: 700, fontSize: '15px' }}>{previewModal.title}</span>
                <span className="badge badge-blue">Page {previewModal.page}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <a
                  href={`${API_BASE}/files/${previewModal.filename}#page=${previewModal.page}`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px', fontSize: '12px' }}
                >
                  <ExternalLink size={13} />
                  New Tab
                </a>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px' }}
                  onClick={() => setPreviewModal({ isOpen: false, filename: '', title: '', page: 1 })}
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="modal-body">
              <iframe
                title="Document Preview"
                src={`${API_BASE}/files/${previewModal.filename}#page=${previewModal.page}`}
                className="preview-iframe"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}