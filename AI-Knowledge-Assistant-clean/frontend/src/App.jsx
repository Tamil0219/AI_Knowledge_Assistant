import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { Send, Upload, Moon, Sun, Bot, User, FileText, Database } from 'lucide-react'

// Backend URL
const API_URL = 'http://127.0.0.1:8000';

function App() {
  const [theme, setTheme] = useState('light');
  const [messages, setMessages] = useState([
    { role: 'ai', content: 'Hello! I am your AI Knowledge Assistant. Upload a document and ask me anything about it!', sources: [] }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  // Upload State
  const [uploadStatus, setUploadStatus] = useState({ status: 'idle', message: '' });
  
  const messagesEndRef = useRef(null);

  // Toggle Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle File Upload
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check extension
    if (!file.name.endsWith('.txt') && !file.name.endsWith('.pdf')) {
      setUploadStatus({ status: 'error', message: 'Only .txt and .pdf allowed' });
      return;
    }

    setUploadStatus({ status: 'loading', message: 'Uploading and processing...' });
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      
      if (!response.ok) throw new Error(data.detail || 'Upload failed');
      
      setUploadStatus({ status: 'success', message: `${file.name} uploaded successfully.` });
    } catch (err) {
      setUploadStatus({ status: 'error', message: err.message });
    }
  };

  // Handle Send Message
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isTyping) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsTyping(true);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMessage })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to get response');
      }

      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: data.answer, 
        sources: data.sources || [] 
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: `**Error:** ${error.message}`, 
        sources: [] 
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <h1>
          <Database size={24} />
          Knowledge DB
        </h1>

        <div className="upload-section">
          <h2>Add Documents</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
            Upload PDFs or Text files to train the assistant.
          </p>
          
          <div className="file-input-wrapper">
            <button className="btn btn-primary">
              <Upload size={18} />
              Upload File
            </button>
            <input type="file" accept=".txt,.pdf" onChange={handleFileUpload} />
          </div>

          {uploadStatus.status !== 'idle' && (
            <div className={`upload-status ${uploadStatus.status}`}>
              {uploadStatus.message}
            </div>
          )}
        </div>

        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
        </button>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-container">
        
        {/* Chat History */}
        <div className="chat-history">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.role}`}>
              <div className={`message ${msg.role}`}>
                <div className="message-content">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontWeight: 'bold', color: 'var(--primary)' }}>
                    {msg.role === 'ai' ? <Bot size={18} /> : <User size={18} />}
                    {msg.role === 'ai' ? 'Assistant' : 'You'}
                  </div>
                  
                  {/* Markdown Renderer for clean text output */}
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>

                {/* Render Sources if Context was retrieved */}
                {msg.role === 'ai' && msg.sources && msg.sources.length > 0 && (
                  <div className="sources-container">
                    <div className="sources-title">Knowledge Sources</div>
                    <div className="source-badges">
                      {msg.sources.map((src, i) => (
                        <div key={i} className="source-badge">
                          <FileText size={12} />
                          {src.source} (Sim: {(src.similarity || 0).toFixed(2)})
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isTyping && (
            <div className="message-wrapper ai">
              <div className="message ai">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="input-area">
          <form className="input-form" onSubmit={handleSendMessage}>
            <textarea
              placeholder="Ask a question based on your documents..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              disabled={isTyping}
            />
            <button type="submit" className="send-btn" disabled={!inputValue.trim() || isTyping}>
              <Send size={18} />
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

export default App
