import { useState, useEffect } from 'react';

let wsInstance: WebSocket | null = null;
let eventListeners = new Set<(event: any) => void>();
let statusListeners = new Set<(connected: boolean) => void>();
let reconnectTimeout: NodeJS.Timeout | null = null;
let isConnected = false;

function getWsUrl(): string {
  // Use VITE_WS_BASE or derive same-origin WebSocket url
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // If Vite proxy handles ws at same port, use current origin
  return `${proto}//${window.location.host}/ws/live`;
}

function connectWs() {
  if (wsInstance) return;
  
  try {
    wsInstance = new WebSocket(getWsUrl());
    
    wsInstance.onopen = () => {
      isConnected = true;
      statusListeners.forEach(listener => listener(true));
    };
    
    wsInstance.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        eventListeners.forEach(listener => listener(data));
      } catch (e) {
        console.error('Failed to parse WS message', e);
      }
    };
    
    wsInstance.onclose = () => {
      isConnected = false;
      wsInstance = null;
      statusListeners.forEach(listener => listener(false));
      
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(connectWs, 3000);
    };
    
    wsInstance.onerror = () => {
      if (wsInstance) wsInstance.close();
    };
  } catch (e) {
    console.error('Failed to initialize WebSocket', e);
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    reconnectTimeout = setTimeout(connectWs, 3000);
  }
}

export function useLiveEvents() {
  const [lastEvent, setLastEvent] = useState<any>(null);
  const [connected, setConnected] = useState(isConnected);

  useEffect(() => {
    if (!wsInstance) {
      connectWs();
    }
    
    const onEvent = (data: any) => setLastEvent(data);
    const onStatus = (status: boolean) => setConnected(status);

    eventListeners.add(onEvent);
    statusListeners.add(onStatus);
    
    setConnected(isConnected);

    return () => {
      eventListeners.delete(onEvent);
      statusListeners.delete(onStatus);
    };
  }, []);

  return { lastEvent, connected };
}
