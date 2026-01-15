/**
 * useLocalStorage hook for persisting state to localStorage.
 *
 * Provides a useState-like interface with automatic persistence.
 * Related: App.tsx, useTheme.ts
 */

import { useState, useCallback } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((prev: T) => T)) => void] {
  // Get stored value or use initial
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue;
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  // Persist to localStorage when value changes
  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    setStoredValue(prev => {
      const nextValue = value instanceof Function ? value(prev) : value;
      try {
        localStorage.setItem(key, JSON.stringify(nextValue));
      } catch (error) {
        console.warn(`Error writing localStorage key "${key}":`, error);
      }
      return nextValue;
    });
  }, [key]);

  return [storedValue, setValue];
}
