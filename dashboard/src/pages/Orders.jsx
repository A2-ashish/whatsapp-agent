import { useState, useEffect } from 'react';
import api from '../services/api';
import { Eye, CheckCircle, Clock, XCircle, Truck } from 'lucide-react';
import { format } from 'date-fns';

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchOrders();
  }, [filter]);

  const fetchOrders = async () => {
    try {
      const url = filter === 'all' ? '/orders/' : `/orders/?status=${filter}`;
      const response = await api.get(url);
      setOrders(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'confirmed': return <span className="badge badge-info"><CheckCircle size={12} style={{marginRight: '4px'}}/> Confirmed</span>;
      case 'processing': return <span className="badge badge-warning"><Clock size={12} style={{marginRight: '4px'}}/> Processing</span>;
      case 'shipped': return <span className="badge badge-success"><Truck size={12} style={{marginRight: '4px'}}/> Shipped</span>;
      case 'completed': return <span className="badge badge-success"><CheckCircle size={12} style={{marginRight: '4px'}}/> Completed</span>;
      case 'cancelled': return <span className="badge badge-danger"><XCircle size={12} style={{marginRight: '4px'}}/> Cancelled</span>;
      default: return <span className="badge">{status}</span>;
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.75rem' }}>Orders</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['all', 'confirmed', 'processing', 'shipped', 'cancelled'].map(f => (
            <button 
              key={f}
              onClick={() => setFilter(f)}
              className={filter === f ? 'btn btn-primary' : 'btn btn-secondary'}
              style={{ textTransform: 'capitalize' }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '24px' }}>
        {loading ? (
          <div style={{ color: 'var(--text-muted)' }}>Loading orders...</div>
        ) : (
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Date</th>
                  <th>Customer ID</th>
                  <th>Items</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                      #{order.id.substring(0, 8)}
                    </td>
                    <td>{format(new Date(order.created_at), 'MMM d, yyyy HH:mm')}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{order.customer_id.substring(0, 8)}...</td>
                    <td>
                      {Array.isArray(order.items_json) ? order.items_json.length : 0} items
                    </td>
                    <td style={{ fontWeight: 600 }}>₹{order.total}</td>
                    <td>{getStatusBadge(order.status)}</td>
                    <td>
                      <button className="btn btn-secondary" style={{ padding: '6px' }}>
                        <Eye size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
                {orders.length === 0 && (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No orders found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
