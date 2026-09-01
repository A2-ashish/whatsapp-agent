import { useState, useEffect } from 'react';
import api from '../services/api';
import { Tag, Settings, Save } from 'lucide-react';

export default function Policies() {
  const [policies, setPolicies] = useState([]);
  const [settings, setSettings] = useState({ auto_approve_order_limit: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [polRes, setRes] = await Promise.all([
        api.get('/policies/discounts'),
        api.get('/policies/settings')
      ]);
      setPolicies(polRes.data);
      setSettings(setRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (e) => {
    e.preventDefault();
    try {
      await api.patch('/policies/settings', { auto_approve_order_limit: settings.auto_approve_order_limit });
      alert("Settings saved!");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <h1 style={{ fontSize: '1.75rem', marginBottom: '24px' }}>Policies & Limits</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        
        {/* Agent Limits */}
        <div className="glass-panel" style={{ padding: '24px', alignSelf: 'start' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={20} color="var(--accent-primary)" />
            Agent Autonomy Limits
          </h2>

          <form onSubmit={updateSetting} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label className="label">Auto-Approve Order Limit (₹)</label>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                The agent will automatically escalate any order exceeding this total value.
              </p>
              <input 
                type="number" 
                className="input-field"
                value={settings.auto_approve_order_limit}
                onChange={e => setSettings({...settings, auto_approve_order_limit: parseFloat(e.target.value)})}
              />
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ width: 'fit-content' }}>
              <Save size={18} /> Save Limits
            </button>
          </form>
        </div>

        {/* Discount Tiers */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Tag size={20} color="var(--success)" />
              Bulk Discount Tiers
            </h2>
            <button className="btn btn-secondary">Add Tier</button>
          </div>

          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
            The agent will strictly enforce these discount rules during negotiations. It cannot invent discounts outside these tiers.
          </p>

          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Quantity Range</th>
                  <th>Discount %</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {policies.map(p => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 500 }}>{p.description || 'Standard Tier'}</td>
                    <td>{p.min_quantity} - {p.max_quantity || '∞'} units</td>
                    <td>
                      <span className="badge badge-success">{p.discount_percent}%</span>
                    </td>
                    <td>
                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.8rem' }}>Edit</button>
                    </td>
                  </tr>
                ))}
                {policies.length === 0 && !loading && (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>No policies defined</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
