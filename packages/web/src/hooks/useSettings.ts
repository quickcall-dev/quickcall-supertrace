/**
 * useSettings hook for managing SuperTrace application settings.
 *
 * Provides persistent settings with localStorage backing.
 * Related: useLocalStorage.ts, App.tsx, IntentInsights.tsx
 */

import { useLocalStorage } from './useLocalStorage';

export interface SuperTraceSettings {
  intentRefreshThreshold: number; // Number of prompts before auto-refresh (default: 5)
  notifications: {
    enabled: boolean; // Master switch for notifications
    intentChanges: boolean; // Notify when intents change
  };
}

const DEFAULT_SETTINGS: SuperTraceSettings = {
  intentRefreshThreshold: 5,
  notifications: {
    enabled: false,
    intentChanges: true,
  },
};

const STORAGE_KEY = 'supertrace-settings';

export function useSettings(): [SuperTraceSettings, (settings: SuperTraceSettings | ((prev: SuperTraceSettings) => SuperTraceSettings)) => void] {
  const [settings, setSettings] = useLocalStorage<SuperTraceSettings>(STORAGE_KEY, DEFAULT_SETTINGS);

  // Merge with defaults to handle new settings added in future versions
  const mergedSettings: SuperTraceSettings = {
    ...DEFAULT_SETTINGS,
    ...settings,
    notifications: {
      ...DEFAULT_SETTINGS.notifications,
      ...settings?.notifications,
    },
  };

  return [mergedSettings, setSettings];
}
