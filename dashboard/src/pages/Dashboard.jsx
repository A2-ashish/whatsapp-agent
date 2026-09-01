import { useState, useEffect } from 'react';
import api from '../services/api';
import { 
  TrendingUp, 
  ShoppingBag, 
  DollarSign, 
  AlertOctagon, 
  MessageSquare,
  Activity
} from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await api.get('/analytics/');
        setData(response.data);
      } catch (err) {
        console.error('Failed to fetch analytics', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) return <div style={{ color: 'var(--text-muted)' }}>Loading analytics...</div>;
  if (!data) return <div style={{ color: 'var(--danger)' }}>Failed to load analytics</div>;

  const cards = [
    { title: 'Revenue Today', value: `₹${data.revenue_today}`, icon: DollarSign, color: 'var(--success)' },
    { title: 'Orders Today', value: data.orders_today, icon: ShoppingBag, color: 'var(--accent-primary)' },
    { title: 'Open Escalations', value: data.open_escalations, icon: AlertOctagon, color: 'var(--danger)' },
    { title: 'Agent Autonomy', value: `${data.autonomy_rate}%`, icon: Activity, color: 'var(--warning)' },
    { title: 'Total Conversations', value: data.total_conversations, icon: MessageSquare, color: 'var(--accent-secondary)' },
    { title: 'Agent Cost', value: `₹${data.total_cost_inr.toFixed(2)}`, icon: TrendingUp, color: 'var(--text-muted)' },
  ];

  return (
    <div>
      <h1 style={{ marginBottom: '24px', fontSize: '1.75rem' }}>Platform Analytics</h1>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', 
        gap: '24px',
        marginBottom: '32px'
      }}>
        {cards.map((card, i) => (
          <div key={i} className="glass-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '8px' }}>
                  {card.title}
                </p>
                <h3 style={{ fontSize: '2rem', margin: 0 }}>{card.value}</h3>
              </div>
              <div style={{ 
                background: `rgba(${card.color === 'var(--success)' ? '16, 185, 129' : 
                                  card.color === 'var(--danger)' ? '239, 68, 68' : 
                                  card.color === 'var(--warning)' ? '245, 158, 11' : 
                                  '59, 130, 246'}, 0.1)`, 
                padding: '12px', 
                borderRadius: '12px' 
              }}>
                <card.icon size={24} color={card.color} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="glass-panel" style={{ padding: '32px' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '16px' }}>Weekly Performance</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div>
            <p style={{ color: 'var(--text-secondary)' }}>Revenue This Week</p>
            <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
              ₹{data.revenue_this_week}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)' }}>Orders This Week</p>
            <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
              {data.orders_this_week}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
