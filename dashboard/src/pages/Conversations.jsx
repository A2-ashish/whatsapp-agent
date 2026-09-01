import { useState, useEffect } from 'react';
import api from '../services/api';
import { MessageCircle, Code, User, Bot, AlertTriangle } from 'lucide-react';
import { format } from 'date-fns';

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  
  const [selectedId, setSelectedId] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      const response = await api.get('/conversations/');
      setConversations(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingList(false);
    }
  };

  const loadTranscript = async (id) => {
    setSelectedId(id);
    setLoadingTranscript(true);
    try {
      const response = await api.get(`/conversations/${id}/messages`);
      setTranscript(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingTranscript(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 120px)', gap: '24px' }}>
      
      {/* Conversations List */}
      <div className="glass-panel" style={{ width: '350px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid var(--border-color)' }}>
          <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Conversations</h2>
        </div>
        
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
          {loadingList ? (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>Loading...</p>
          ) : conversations.map(c => (
            <div 
              key={c.id}
              onClick={() => loadTranscript(c.id)}
              style={{
                padding: '16px',
                borderRadius: '8px',
                cursor: 'pointer',
                marginBottom: '8px',
                background: selectedId === c.id ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                border: `1px solid ${selectedId === c.id ? 'rgba(59, 130, 246, 0.2)' : 'transparent'}`,
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                if (selectedId !== c.id) e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
              }}
              onMouseLeave={(e) => {
                if (selectedId !== c.id) e.currentTarget.style.background = 'transparent';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <strong style={{ fontSize: '1rem' }}>{c.customer_name || c.customer_phone}</strong>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {c.last_message_at ? format(new Date(c.last_message_at), 'MMM d, HH:mm') : ''}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                {c.is_paused && <span className="badge badge-warning">Paused</span>}
                {c.status === 'closed' && <span className="badge">Closed</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Transcript Viewer */}
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selectedId && transcript ? (
          <>
            <div style={{ padding: '20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.25rem' }}>{transcript.customer.name || transcript.customer.whatsapp_number}</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '4px 0 0 0' }}>
                  {transcript.customer.whatsapp_number}
                </p>
              </div>
              {transcript.conversation.is_paused && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--warning)', background: 'var(--warning-bg)', padding: '8px 12px', borderRadius: '8px' }}>
                  <AlertTriangle size={18} /> Awaiting escalation response
                </div>
              )}
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {transcript.messages.map(msg => {
                const isCustomer = msg.sender === 'customer';
                const isOwner = msg.sender === 'owner';
                
                return (
                  <div key={msg.id} style={{ 
                    display: 'flex', 
                    flexDirection: 'column',
                    alignItems: isCustomer ? 'flex-start' : 'flex-end',
                    maxWidth: '85%',
                    alignSelf: isCustomer ? 'flex-start' : 'flex-end'
                  }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '8px', 
                      marginBottom: '4px',
                      color: 'var(--text-muted)',
                      fontSize: '0.85rem'
                    }}>
                      {isCustomer ? <User size={14} /> : isOwner ? <User size={14} color="var(--success)" /> : <Bot size={14} color="var(--accent-primary)" />}
                      {isCustomer ? 'Customer' : isOwner ? 'Business Owner' : 'AI Agent'}
                      <span style={{ opacity: 0.5 }}>• {format(new Date(msg.timestamp), 'HH:mm')}</span>
                    </div>
                    
                    <div style={{
                      background: isCustomer ? 'var(--bg-tertiary)' : isOwner ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                      border: `1px solid ${isCustomer ? 'var(--border-color)' : isOwner ? 'rgba(16, 185, 129, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`,
                      padding: '12px 16px',
                      borderRadius: '12px',
                      borderTopLeftRadius: isCustomer ? '4px' : '12px',
                      borderTopRightRadius: !isCustomer ? '4px' : '12px',
                      color: 'var(--text-primary)',
                      lineHeight: 1.5,
                      whiteSpace: 'pre-wrap'
                    }}>
                      {msg.content}
                    </div>

                    {msg.tool_calls && Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0 && (
                      <div style={{ 
                        marginTop: '8px', 
                        padding: '8px 12px', 
                        background: 'rgba(0,0,0,0.2)', 
                        borderRadius: '8px',
                        border: '1px dashed var(--border-color)',
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)',
                        fontFamily: 'monospace',
                        alignSelf: 'flex-end'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px', color: 'var(--accent-primary)' }}>
                          <Code size={14} /> Tools Executed
                        </div>
                        {msg.tool_calls.map((tc, idx) => (
                          <div key={idx}>- {tc.name || (typeof tc === 'string' ? tc : JSON.stringify(tc))}</div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            <MessageCircle size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
            <p>Select a conversation to view transcript</p>
          </div>
        )}
      </div>
    </div>
  );
}
