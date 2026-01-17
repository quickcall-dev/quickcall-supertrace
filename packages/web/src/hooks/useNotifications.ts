/**
 * useNotifications hook for browser notification management.
 *
 * Handles permission requests and showing notifications.
 * Related: useSettings.ts, App.tsx
 */

import { useState, useCallback, useEffect } from 'react';

type NotificationPermission = 'default' | 'denied' | 'granted';

interface UseNotificationsReturn {
  permission: NotificationPermission;
  isSupported: boolean;
  requestPermission: () => Promise<boolean>;
  showNotification: (title: string, body?: string, options?: NotificationOptions) => void;
}

export function useNotifications(): UseNotificationsReturn {
  const isSupported = typeof window !== 'undefined' && 'Notification' in window;

  const [permission, setPermission] = useState<NotificationPermission>(() => {
    if (!isSupported) return 'denied';
    return Notification.permission;
  });

  // Update permission state if it changes externally
  useEffect(() => {
    if (!isSupported) return;
    setPermission(Notification.permission);
  }, [isSupported]);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!isSupported) return false;

    if (permission === 'granted') return true;
    if (permission === 'denied') return false;

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result === 'granted';
    } catch (error) {
      console.warn('Error requesting notification permission:', error);
      return false;
    }
  }, [isSupported, permission]);

  const showNotification = useCallback(
    (title: string, body?: string, options?: NotificationOptions) => {
      if (!isSupported || permission !== 'granted') return;

      try {
        const notification = new Notification(title, {
          body,
          icon: '/favicon.ico',
          badge: '/favicon.ico',
          ...options,
        });

        // Auto-close after 5 seconds
        setTimeout(() => notification.close(), 5000);
      } catch (error) {
        console.warn('Error showing notification:', error);
      }
    },
    [isSupported, permission]
  );

  return {
    permission,
    isSupported,
    requestPermission,
    showNotification,
  };
}
