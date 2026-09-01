import { useState, useEffect } from 'react';
import api from '../services/api';
import { AlertTriangle, CheckCircle, MessageSquare, Send } from 'lucide-react';
import { format } from 'date-fns';

export default function Escalations() {
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedEscalation, setSelectedEscalation] = useState(null);
  const [resolveText, setResolveText] = useState('');
  const [resolveMode, setResolveMode] = useState('instruct_agent');
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    fetchEscalations();
  }, []);

  const fetchEscalations = async () => {
    try {
      const response = await api.get('/escalations/?status=open');
      setEscalations(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (e) => {
    e.preventDefault();
    if (!resolveText.trim()) return;
    
    setResolving(true);
    try {
      await api.post(`/escalations/${selectedEscalation.id}/resolve`, {
        mode: resolveMode,
        content: resolveText
      });
      setSelectedEscalation(null);
      setResolveText('');
      fetchEscalations(); // Refresh list
    } catch (err) {
      console.error("Resolution failed", err);
      alert("Failed to resolve escalation");
    } finally {
      setResolving(false);
    }
  };

  return (
    <div>
      <h1 style={{ fontSize: '1.75rem', marginBottom: '24px' }}>Active Escalations</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* List Panel */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle color="var(--warning)" size={20} className={escalations.length > 0 ? "pulse-alert" : ""} />
            Needs Attention ({escalations.length})
          </h2>

          {loading ? (
            <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
          ) : escalations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
              <CheckCircle size={48} style={{ margin: '0 auto 16px', color: 'var(--success)', opacity: 0.5 }} />
              <p>All caught up! No active escalations.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {escalations.map(esc => (
                <div 
                  key={esc.id} 
                  className="glass-card"
                  style={{ 
                    padding: '16px', 
                    cursor: 'pointer',
                    border: selectedEscalation?.id === esc.id ? '1px solid var(--accent-primary)' : ''
                  }}
                  onClick={() => setSelectedEscalation(esc)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span className="badge badge-warning">Escalated</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {format(new Date(esc.created_at), 'HH:mm')}
                    </span>
                  </div>
                  <h4 style={{ margin: '0 0 4px', fontSize: '1rem' }}>{esc.reason}</h4>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {esc.conversation_summary}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Resolution Panel */}
        {selectedEscalation ? (
          <div className="glass-panel animate-fade-in" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '16px' }}>Resolve Escalation</h2>
            
            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
              <h4 style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', marginBottom: '8px' }}>Agent's Summary</h4>
              <p style={{ marginBottom: '16px', lineHeight: 1.6 }}>{selectedEscalation.conversation_summary}</p>
              
              <h4 style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', marginBottom: '8px' }}>Suggested Action</h4>
              <p style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>{selectedEscalation.suggested_action}</p>
            </div>

            <form onSubmit={handleResolve} style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label className="label">Resolution Mode</label>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button 
                    type="button"
                    className={`btn ${resolveMode === 'instruct_agent' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setResolveMode('instruct_agent')}
                    style={{ flex: 1 }}
                  >
                    Instruct Agent
                  </button>
                  <button 
                    type="button"
                    className={`btn ${resolveMode === 'direct_reply' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setResolveMode('direct_reply')}
                    style={{ flex: 1 }}
                  >
                    Direct Reply
                  </button>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                  {resolveMode === 'instruct_agent' 
                    ? "Tell the agent what to do, and it will reply to the customer autonomously." 
                    : "Send a message directly to the customer as the business owner."}
                </p>
              </div>

              <div>
                <label className="label">
                  {resolveMode === 'instruct_agent' ? 'Instruction for Agent' : 'Message to Customer'}
                </label>
                <textarea 
                  className="input-field"
                  rows={4}
                  value={resolveText}
                  onChange={(e) => setResolveText(e.target.value)}
                  placeholder={resolveMode === 'instruct_agent' ? "E.g., Approve the return this one time." : "Hi, I'm the owner..."}
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary" disabled={resolving || !resolveText.trim()}>
                {resolving ? 'Sending...' : <><Send size={18} /> Resolve & Unpause</>}
              </button>
            </form>
          </div>
        ) : (
          <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            <div style={{ textAlign: 'center' }}>
              <MessageSquare size={48} style={{ opacity: 0.2, margin: '0 auto 16px' }} />
              <p>Select an escalation to resolve</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
