import { useState, useEffect, useCallback } from 'react';
import { BASE_URL } from '../config';
import { getAuthHeaders } from '../api';

export interface NotificationItem {
  id: string;
  title: string;
  content: string;
  timestamp: number;
  read: boolean;
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${BASE_URL}/notifications`, { headers });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.items || []);
      }
    } catch (e) {
      console.error('Failed to fetch notifications', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerLoginAlert = useCallback(async () => {
    try {
      const headers = await getAuthHeaders();
      await fetch(`${BASE_URL}/notifications/trigger-login-alert`, {
        method: 'POST',
        headers,
      });
      // Start polling for this alert arriving
      const interval = setInterval(fetchNotifications, 5000);
      // Stop polling after 30 seconds (agent usually takes ~10-15s)
      setTimeout(() => clearInterval(interval), 30000);
    } catch (e) {
      console.error('Failed to trigger login alert', e);
    }
  }, [fetchNotifications]);

  const dismissNotification = useCallback(async (id: string) => {
    try {
      const headers = await getAuthHeaders();
      await fetch(`${BASE_URL}/notifications/${id}`, {
        method: 'DELETE',
        headers,
      });
      setNotifications(prev => prev.filter(n => n.id !== id));
    } catch (e) {
      console.error('Failed to dismiss notification', e);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  return { notifications, loading, triggerLoginAlert, dismissNotification, refresh: fetchNotifications };
}
