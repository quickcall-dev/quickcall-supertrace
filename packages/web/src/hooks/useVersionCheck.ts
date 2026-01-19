/**
 * useVersionCheck hook for auto-update notifications.
 *
 * Checks for package updates from the backend and manages update state.
 * Related: UpdateNotification.tsx, api/client.ts
 */

import { useState, useEffect, useCallback, useRef } from 'react';

interface VersionInfo {
  currentVersion: string;
  latestVersion: string;
  updateAvailable: boolean;
  installMethod: 'pip' | 'uvx' | 'source' | 'unknown';
  changelogUrl: string | null;
}

interface UpdateState {
  status: 'idle' | 'checking' | 'updating' | 'restarting' | 'error';
  message: string | null;
}

interface UseVersionCheckResult {
  versionInfo: VersionInfo | null;
  updateState: UpdateState;
  isChecking: boolean;
  isDismissed: boolean;
  checkNow: () => Promise<void>;
  triggerUpdate: () => Promise<void>;
  dismiss: () => void;
  debug: {
    enabled: boolean;
    simulateUpdate: () => void;
    reset: () => void;
  };
}

const STORAGE_KEY = 'supertrace-version-dismissed';
const CHECK_INTERVAL = 30 * 60 * 1000; // 30 minutes

export function useVersionCheck(): UseVersionCheckResult {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [updateState, setUpdateState] = useState<UpdateState>({ status: 'idle', message: null });
  const [dismissedVersion, setDismissedVersion] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });

  const intervalRef = useRef<number | null>(null);
  const reconnectIntervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);

  const checkVersion = useCallback(async () => {
    setUpdateState({ status: 'checking', message: null });

    try {
      const response = await fetch('/api/version');
      if (!response.ok) throw new Error('Failed to fetch version');

      const data = await response.json();

      const info: VersionInfo = {
        currentVersion: data.current_version,
        latestVersion: data.latest_version,
        updateAvailable: data.update_available,
        installMethod: data.install_method,
        changelogUrl: data.changelog_url,
      };

      setVersionInfo(info);
      setUpdateState({ status: 'idle', message: null });

      // Reset dismissed if new version detected
      if (info.updateAvailable && info.latestVersion !== dismissedVersion) {
        setDismissedVersion(null);
        localStorage.removeItem(STORAGE_KEY);
      }

    } catch (error) {
      console.error('Version check failed:', error);
      setUpdateState({ status: 'error', message: 'Failed to check for updates' });
    }
  }, [dismissedVersion]);

  const triggerUpdate = useCallback(async () => {
    setUpdateState({ status: 'updating', message: 'Installing update...' });

    try {
      const response = await fetch('/api/version/update', { method: 'POST' });
      const data = await response.json();

      if (data.status === 'error') {
        setUpdateState({ status: 'error', message: data.message });
        return;
      }

      if (data.status === 'current') {
        // Already on latest - don't show message
        setUpdateState({ status: 'idle', message: null });
        return;
      }

      // Update initiated - wait for server restart
      setUpdateState({ status: 'restarting', message: 'Server restarting...' });

      // Poll for server to come back
      const pollHealth = async () => {
        try {
          const healthResponse = await fetch('/api/health');
          if (healthResponse.ok) {
            // Server is back - clear all timers
            if (reconnectIntervalRef.current) clearInterval(reconnectIntervalRef.current);
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            reconnectIntervalRef.current = null;
            timeoutRef.current = null;

            setUpdateState({ status: 'idle', message: `Updated to v${data.new_version}!` });

            // Re-check version to update UI
            await checkVersion();

            // Clear success message after 5s
            setTimeout(() => {
              setUpdateState({ status: 'idle', message: null });
            }, 5000);
          }
        } catch {
          // Server still down, keep polling
        }
      };

      // Start polling after 3s delay
      setTimeout(() => {
        reconnectIntervalRef.current = window.setInterval(pollHealth, 2000);
      }, 3000);

      // Timeout after 60s
      timeoutRef.current = window.setTimeout(() => {
        if (reconnectIntervalRef.current) {
          clearInterval(reconnectIntervalRef.current);
          reconnectIntervalRef.current = null;
          setUpdateState({
            status: 'error',
            message: 'Server restart timed out. Please restart manually.'
          });
        }
      }, 60000);

    } catch (error) {
      console.error('Update failed:', error);
      setUpdateState({ status: 'error', message: 'Update request failed' });
    }
  }, [checkVersion]);

  const dismiss = useCallback(() => {
    if (versionInfo?.latestVersion) {
      setDismissedVersion(versionInfo.latestVersion);
      localStorage.setItem(STORAGE_KEY, versionInfo.latestVersion);
    }
  }, [versionInfo]);

  // Debug helpers - only in dev mode
  const debugEnabled = import.meta.env.DEV;

  const debugSimulateUpdate = useCallback(() => {
    setVersionInfo({
      currentVersion: '0.1.0',
      latestVersion: '0.2.0',
      updateAvailable: true,
      installMethod: 'pip',
      changelogUrl: 'https://github.com/quickcall-dev/quickcall-supertrace/releases/tag/v0.2.0',
    });
    setDismissedVersion(null);
    localStorage.removeItem(STORAGE_KEY);
    setUpdateState({ status: 'idle', message: null });
  }, []);

  const debugReset = useCallback(() => {
    setVersionInfo(null);
    setDismissedVersion(null);
    localStorage.removeItem(STORAGE_KEY);
    setUpdateState({ status: 'idle', message: null });
    checkVersion();
  }, [checkVersion]);

  // Check on mount and periodically
  useEffect(() => {
    checkVersion();

    intervalRef.current = window.setInterval(checkVersion, CHECK_INTERVAL);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (reconnectIntervalRef.current) clearInterval(reconnectIntervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [checkVersion]);

  const isDismissed = dismissedVersion === versionInfo?.latestVersion;

  return {
    versionInfo,
    updateState,
    isChecking: updateState.status === 'checking',
    isDismissed,
    checkNow: checkVersion,
    triggerUpdate,
    dismiss,
    debug: {
      enabled: debugEnabled,
      simulateUpdate: debugSimulateUpdate,
      reset: debugReset,
    },
  };
}
