/**
 * Version context for sharing version state across components.
 *
 * Ensures sidebar and update notification share the same version info
 * so both update immediately after server restart.
 */

import { createContext, useContext, type ReactNode } from 'react';
import { useVersionCheck } from '../hooks/useVersionCheck';

type VersionContextType = ReturnType<typeof useVersionCheck>;

const VersionContext = createContext<VersionContextType | null>(null);

export function VersionProvider({ children }: { children: ReactNode }) {
  const versionState = useVersionCheck();
  console.log('[VersionProvider] currentVersion:', versionState.versionInfo?.currentVersion);

  return (
    <VersionContext.Provider value={versionState}>
      {children}
    </VersionContext.Provider>
  );
}

export function useVersion(): VersionContextType {
  const context = useContext(VersionContext);
  if (!context) {
    throw new Error('useVersion must be used within a VersionProvider');
  }
  return context;
}
