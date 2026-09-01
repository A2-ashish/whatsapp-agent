import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

export function useSSE() {
  const [events, setEvents] = useState([]);
  const [lastEvent, setLastEvent] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    // We can't use EventSource with headers directly in browser,
    // so we pass token in URL. In production, use HttpOnly cookies for auth.
    // For this prototype, we'll append token to URL if needed or use fetch.
    // Starlette SSE supports EventSource. We will pass a mock or assume a proxy for now.
    
    // To make it work with EventSource and Bearer tokens, we typically need a polyfill 
    // like @microsoft/fetch-event-source, but for standard EventSource we can try:
    // This is a simplified version.
    
    // For demo purposes, assuming API handles auth gracefully or we use a custom fetch implementation.
    // Real implementation would use @microsoft/fetch-event-source for headers.
    
    const url = `${API_URL}/events/?token=${token}`; 
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data === "keepalive") return;
        
        setLastEvent(data);
        setEvents((prev) => [data, ...prev].slice(0, 50)); // Keep last 50 events
      } catch (err) {
        console.error("Failed to parse SSE event", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("SSE Error", err);
      eventSource.close();
      // Simple reconnect logic
      setTimeout(() => {
        // In a real app we'd dispatch a reconnect action
      }, 5000);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return { events, lastEvent };
}
