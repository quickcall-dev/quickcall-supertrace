/**
 * Session list sidebar component.
 *
 * Displays sessions grouped by date with first prompt as identifier.
 * Includes Import Sessions button for manual JSONL ingestion.
 * Clean, professional design matching QuickCall styling.
 */

import { useState, useMemo, useRef, useEffect } from 'react';
import type { Session } from '../api/client';
import { triggerIngest, forceReimportAll, deleteSession } from '../api/client';
import { parseUTCTimestamp } from '../utils/time';
import { useVersion } from '../contexts/VersionContext';
import { SessionContextMenu, type SessionAction } from './SessionContextMenu';
import { DeleteSessionDialog } from './DeleteSessionDialog';
import { ExportModal, type ExportLevel } from './ExportModal';

interface SessionListProps {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onSearch: (query: string) => void;
  onSessionsImported: () => void;
  onSessionDeleted?: (sessionId: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  unreadSessionIds?: string[];
}

type DateGroup = 'Today' | 'Yesterday' | 'This Week' | 'Older';

interface GroupedSessions {
  group: DateGroup;
  sessions: Session[];
}

function getDateGroup(timestamp: string | null): DateGroup {
  const date = parseUTCTimestamp(timestamp);
  if (!date) return 'Older';

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  if (date >= today) return 'Today';
  if (date >= yesterday) return 'Yesterday';
  if (date >= weekAgo) return 'This Week';
  return 'Older';
}

function getRelativeTime(timestamp: string | null): string {
  const date = parseUTCTimestamp(timestamp);
  if (!date) return '';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;

  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function getSessionFilePath(session: Session): string {
  // Use file_path from server if available (preferred)
  if (session.file_path) return session.file_path;

  // Fallback: construct path from project_path (legacy)
  if (!session.project_path) return session.id;
  const escapedPath = session.project_path.replace(/^\//, '').replace(/\//g, '-');
  const homeDir = '/Users/' + (session.project_path.split('/')[2] || 'user');
  return `${homeDir}/.claude/projects/-${escapedPath}/${session.id}.jsonl`;
}

export function SessionList({
  sessions,
  selectedId,
  onSelect,
  onSearch,
  onSessionsImported,
  onSessionDeleted,
  isDark,
  onToggleTheme,
  unreadSessionIds = [],
}: SessionListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [showImportMenu, setShowImportMenu] = useState(false);
  const [showReimportConfirm, setShowReimportConfirm] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Session context menu state
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string | null>(null);
  const [deleteDialogSession, setDeleteDialogSession] = useState<Session | null>(null);
  const [exportModalSession, setExportModalSession] = useState<Session | null>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowImportMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Use API version (updates after restart) with build-time fallback
  const { versionInfo } = useVersion();
  const displayVersion = versionInfo?.currentVersion || __APP_VERSION__;
  console.log('[SessionList] versionInfo:', versionInfo?.currentVersion, 'displayVersion:', displayVersion);

  const handleImportSessions = async () => {
    console.log('[SessionList] Import button clicked, isImporting:', isImporting);
    if (isImporting) return;

    setShowImportMenu(false);
    setIsImporting(true);
    setImportStatus('Importing...');

    try {
      const result = await triggerIngest(50);
      if (result.imported > 0) {
        setImportStatus(`Imported ${result.new_sessions} new, ${result.imported} updated`);
        onSessionsImported();
      } else {
        setImportStatus('Already up to date');
      }
    } catch (error) {
      setImportStatus('Import failed');
      console.error('Import error:', error);
    } finally {
      setIsImporting(false);
      // Clear status after 3 seconds
      setTimeout(() => setImportStatus(null), 3000);
    }
  };

  const handleForceReimport = async () => {
    if (isImporting) return;

    setShowReimportConfirm(false);
    setShowImportMenu(false);
    setIsImporting(true);
    setImportStatus('Force reimporting...');

    try {
      const result = await forceReimportAll(50);
      setImportStatus(`Reimported ${result.imported.sessions} sessions, ${result.imported.messages} messages`);
      onSessionsImported();
    } catch (error) {
      setImportStatus('Force reimport failed');
      console.error('Force reimport error:', error);
    } finally {
      setIsImporting(false);
      setTimeout(() => setImportStatus(null), 5000);
    }
  };

  const handleCopyPath = (e: React.MouseEvent, session: Session) => {
    e.stopPropagation();
    const filePath = getSessionFilePath(session);
    navigator.clipboard.writeText(filePath);
    setCopiedId(session.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Session context menu handlers
  const handleSessionAction = (session: Session, action: SessionAction) => {
    switch (action) {
      case 'share':
        setExportModalSession(session);
        break;
      case 'copy':
        // Copy is handled in SessionContextMenu
        setCopiedId(session.id);
        setTimeout(() => setCopiedId(null), 2000);
        break;
      case 'delete':
        setDeleteDialogSession(session);
        break;
    }
  };

  const handleDeleteSession = async () => {
    if (!deleteDialogSession) return;
    await deleteSession(deleteDialogSession.id);
    onSessionDeleted?.(deleteDialogSession.id);
  };

  // Placeholder export handlers - will be wired to Agent 3's export functions
  const handleExportHTML = async (sessionId: string, level: ExportLevel) => {
    console.log(`[SessionList] Export HTML: ${sessionId}, level: ${level}`);
    // Agent 3 will implement: exportToHTML(sessionId, level)
    throw new Error('HTML export not yet implemented');
  };

  const handleExportPNG = async (sessionId: string, level: ExportLevel) => {
    console.log(`[SessionList] Export PNG: ${sessionId}, level: ${level}`);
    // Agent 3 will implement: exportToPNG(sessionId, level)
    throw new Error('PNG export not yet implemented');
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    if (value === '') {
      onSearch('');
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  const groupedSessions = useMemo(() => {
    const groups: Record<DateGroup, Session[]> = {
      'Today': [],
      'Yesterday': [],
      'This Week': [],
      'Older': [],
    };

    sessions.forEach(session => {
      const group = getDateGroup(session.started_at);
      groups[group].push(session);
    });

    const result: GroupedSessions[] = [];
    const order: DateGroup[] = ['Today', 'Yesterday', 'This Week', 'Older'];

    order.forEach(group => {
      if (groups[group].length > 0) {
        result.push({ group, sessions: groups[group] });
      }
    });

    return result;
  }, [sessions]);

  return (
    <div className="w-full border-r border-border flex flex-col h-full bg-card overflow-hidden">
      {/* Header - branding */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between shrink-0">
        <a
          href="https://quickcall.dev"
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col hover:opacity-80 transition-opacity cursor-pointer"
        >
          <span className="inline-flex items-baseline">
            <span className="text-lg font-semibold tracking-tight text-teal-600 dark:text-teal-500">
              quick
            </span>
            <span className="text-lg font-semibold tracking-tight text-foreground">
              call
            </span>
          </span>
          <span className="inline-flex items-baseline gap-1.5">
            <span className="text-xl font-bold -mt-1 tracking-tight bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-500 bg-clip-text text-transparent">
              SuperTrace
            </span>
            <span className="text-[10px] text-amber-500/70 font-medium">
              v{displayVersion}
            </span>
          </span>
        </a>
        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded-lg hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          <i className={isDark ? 'ri-sun-line' : 'ri-moon-line'}></i>
        </button>
      </div>

      {/* Search & Import - below header */}
      <div className="p-3 border-b border-border shrink-0">
        {/* Search */}
        <form onSubmit={handleSearch} className="w-full">
          <div className="flex items-center gap-2 bg-muted rounded-lg px-3 py-1.5 focus-within:ring-1 focus-within:ring-ring transition-all">
            <i className="ri-search-line text-muted-foreground text-sm shrink-0"></i>
            <input
              type="text"
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="flex-1 min-w-0 bg-transparent border-none outline-none text-sm text-foreground placeholder-muted-foreground"
            />
          </div>
        </form>

        {/* Import Sessions Button with Dropdown */}
        <div className="relative mt-2" ref={menuRef}>
          {/* Single button with integrated dropdown */}
          <button
            onClick={handleImportSessions}
            disabled={isImporting}
            className={`
              w-full py-1.5 px-3 rounded-lg text-sm font-medium transition-all
              flex items-center justify-center gap-2
              ${isImporting
                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                : 'bg-primary text-primary-foreground hover:bg-primary/80 active:bg-primary/70 cursor-pointer'
              }
            `}
          >
            <i className={`${isImporting ? 'ri-loader-4-line animate-spin' : 'ri-download-2-line'} shrink-0`}></i>
            <span className="truncate">{isImporting ? 'Importing...' : 'Import Sessions'}</span>
            {/* Dropdown arrow */}
            <i
              className="ri-arrow-down-s-line ml-auto shrink-0 hover:bg-primary-foreground/10 rounded"
              onClick={(e) => {
                e.stopPropagation();
                setShowImportMenu(!showImportMenu);
              }}
            ></i>
          </button>

          {/* Dropdown menu */}
          {showImportMenu && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-lg shadow-xl z-[100] overflow-hidden">
              <button
                onClick={() => {
                  setShowImportMenu(false);
                  setShowReimportConfirm(true);
                }}
                className="w-full px-3 py-2.5 text-sm text-left hover:bg-destructive/10 transition-colors flex items-center gap-2 text-destructive"
              >
                <i className="ri-refresh-line"></i>
                <span>Force Reimport All</span>
              </button>
            </div>
          )}
        </div>

        {/* Force Reimport Confirmation Dialog */}
        {showReimportConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[200]">
            <div className="bg-card border border-border rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
              {/* Header */}
              <div className="px-5 py-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center shrink-0">
                  <i className="ri-alert-line text-destructive text-xl"></i>
                </div>
                <h3 className="text-lg font-semibold text-foreground">Force Reimport All Sessions</h3>
              </div>

              {/* Body */}
              <div className="px-5 pb-4 space-y-3">
                <p className="text-sm text-muted-foreground">This will:</p>
                <ul className="text-sm space-y-2">
                  <li className="flex items-start gap-3">
                    <i className="ri-delete-bin-line text-destructive mt-0.5 shrink-0"></i>
                    <span className="text-foreground">Delete all session data from the database</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <i className="ri-refresh-line text-primary mt-0.5 shrink-0"></i>
                    <span className="text-foreground">Re-import all sessions from JSONL files</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <i className="ri-restart-line text-amber-500 mt-0.5 shrink-0"></i>
                    <span className="text-foreground">Reset message indices and computed fields</span>
                  </li>
                </ul>
                <div className="bg-destructive/10 text-destructive text-sm px-3 py-2.5 rounded-lg flex items-center gap-2 mt-4">
                  <i className="ri-error-warning-line shrink-0"></i>
                  <span>This cannot be undone.</span>
                </div>
              </div>

              {/* Footer */}
              <div className="px-5 py-4 border-t border-border flex justify-end gap-3 bg-muted/30">
                <button
                  onClick={() => setShowReimportConfirm(false)}
                  className="px-4 py-2 text-sm font-medium rounded-lg hover:bg-accent transition-colors text-foreground"
                >
                  Cancel
                </button>
                <button
                  onClick={handleForceReimport}
                  className="px-4 py-2 text-sm font-medium rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
                >
                  Force Reimport
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Import Status */}
        {importStatus && (
          <div className={`
            mt-2 text-xs text-center py-1 px-2 rounded w-full max-w-full truncate
            ${importStatus.includes('failed')
              ? 'bg-destructive/10 text-destructive'
              : 'bg-primary/10 text-primary'
            }
          `}>
            {importStatus}
          </div>
        )}
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-8 text-center">
            <div className="w-12 h-12 mx-auto mb-3 bg-muted rounded-full flex items-center justify-center">
              <i className="ri-chat-3-line text-muted-foreground text-xl"></i>
            </div>
            <p className="text-sm text-muted-foreground">No sessions yet</p>
            <p className="text-xs text-muted-foreground mt-1">Start a Claude session to see it here</p>
          </div>
        ) : (
          groupedSessions.map(({ group, sessions: groupSessions }) => (
            <div key={group}>
              {/* Group Header */}
              <div className="px-4 py-2 text-[11px] font-medium text-muted-foreground uppercase tracking-wider sticky top-0 bg-card/95 backdrop-blur-sm border-b border-border/50">
                {group}
              </div>

              {/* Sessions in Group */}
              {groupSessions.map((session) => {
                const isSelected = selectedId === session.id;
                const isUnread = unreadSessionIds.includes(session.id);
                const prompt = session.first_prompt || 'New session';
                const isMenuOpen = openMenuSessionId === session.id;

                return (
                  <div
                    key={session.id}
                    className="group relative"
                  >
                    <button
                      onClick={() => onSelect(session.id)}
                      className={`
                        relative w-full px-4 py-3 text-left transition-all duration-150
                        ${isSelected
                          ? 'bg-accent border-l-2 border-primary'
                          : 'hover:bg-accent/50 border-l-2 border-transparent'
                        }
                      `}
                    >
                      {/* Unread indicator dot - top right, aligned with text */}
                      {isUnread && !isSelected && (
                        <div className="absolute top-3.5 right-10 w-2 h-2 bg-teal-500 rounded-full" />
                      )}
                      <div className="flex items-start">
                        <div className="flex-1 min-w-0 pr-6">
                          <p className={`text-sm leading-snug ${isSelected ? 'text-foreground font-medium' : isUnread ? 'text-foreground font-medium' : 'text-foreground'} line-clamp-2`}>
                            {prompt}
                          </p>
                          <div className="flex items-center gap-2 mt-1.5">
                            <span className="text-[11px] text-muted-foreground">
                              {getRelativeTime(session.started_at)}
                            </span>
                            <span className="text-muted-foreground/50">·</span>
                            <span
                              className={`text-[11px] font-mono cursor-pointer transition-colors ${copiedId === session.id ? 'text-[color:var(--success)]' : 'text-muted-foreground hover:text-primary'}`}
                              title={getSessionFilePath(session)}
                              onClick={(e) => handleCopyPath(e, session)}
                            >
                              {copiedId === session.id ? '✓ Copied' : session.id.slice(0, 8)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </button>

                    {/* 3-dot context menu - shows on hover */}
                    <div className={`absolute right-2 top-3 ${isMenuOpen ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity`}>
                      <SessionContextMenu
                        sessionId={session.id}
                        filePath={getSessionFilePath(session)}
                        isOpen={isMenuOpen}
                        onOpenChange={(open) => setOpenMenuSessionId(open ? session.id : null)}
                        onAction={(action) => handleSessionAction(session, action)}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border text-[11px] text-muted-foreground text-center">
        {sessions.length} session{sessions.length !== 1 ? 's' : ''}
      </div>

      {/* Delete Session Dialog */}
      <DeleteSessionDialog
        sessionId={deleteDialogSession?.id || ''}
        isOpen={deleteDialogSession !== null}
        onClose={() => setDeleteDialogSession(null)}
        onConfirm={handleDeleteSession}
      />

      {/* Export Modal */}
      <ExportModal
        sessionId={exportModalSession?.id || ''}
        sessionTitle={exportModalSession?.first_prompt || 'Session'}
        isOpen={exportModalSession !== null}
        onClose={() => setExportModalSession(null)}
        onExportHTML={handleExportHTML}
        onExportPNG={handleExportPNG}
      />
    </div>
  );
}
