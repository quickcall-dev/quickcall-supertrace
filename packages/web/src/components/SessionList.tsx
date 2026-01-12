/**
 * Session list sidebar component.
 *
 * Displays sessions grouped by date with first prompt as identifier.
 * Clean, professional design matching QuickCall styling.
 */

import { useState, useMemo } from 'react';
import type { Session } from '../api/client';

interface SessionListProps {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onSearch: (query: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
}

type DateGroup = 'Today' | 'Yesterday' | 'This Week' | 'Older';

interface GroupedSessions {
  group: DateGroup;
  sessions: Session[];
}

function getDateGroup(timestamp: string | null): DateGroup {
  if (!timestamp) return 'Older';

  const date = new Date(timestamp);
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
  if (!timestamp) return '';

  const date = new Date(timestamp);
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

function getSessionFilePath(projectPath: string | null, sessionId: string): string {
  if (!projectPath) return sessionId;
  // Convert project path to Claude's folder naming convention
  // Remove leading slash then replace remaining slashes with dashes
  const escapedPath = projectPath.replace(/^\//, '').replace(/\//g, '-');
  // Use $HOME for portability, user can expand ~ if needed
  return `$HOME/.claude/projects/-${escapedPath}/${sessionId}.jsonl`;
}

export function SessionList({
  sessions,
  selectedId,
  onSelect,
  onSearch,
  isDark,
  onToggleTheme,
}: SessionListProps) {
  const [searchQuery, setSearchQuery] = useState('');

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
    <div className="w-56 border-r border-border flex flex-col h-full bg-card shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex flex-col">
            {/* QuickCall Logo */}
            <span className="inline-flex items-baseline">
              <span className="text-lg font-medium tracking-tight text-teal-600 dark:text-teal-500">
                quick
              </span>
              <span className="text-lg font-medium tracking-tight text-foreground">
                call
              </span>
            </span>
            {/* SuperTrace subscript */}
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider -mt-0.5">
              SuperTrace
            </span>
          </div>
          {/* Theme toggle */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            <i className={isDark ? 'ri-sun-line' : 'ri-moon-line'}></i>
          </button>
        </div>

        {/* Search */}
        <form onSubmit={handleSearch}>
          <div className="relative">
            <i className="ri-search-line absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm"></i>
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="w-full pl-9 pr-3 py-2 bg-input border border-border rounded-lg text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-ring focus:ring-1 focus:ring-ring transition-all"
            />
          </div>
        </form>
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
                const prompt = session.first_prompt || 'New session';

                return (
                  <button
                    key={session.id}
                    onClick={() => onSelect(session.id)}
                    className={`
                      w-full px-4 py-3 text-left transition-all duration-150
                      ${isSelected
                        ? 'bg-accent border-l-2 border-primary'
                        : 'hover:bg-accent/50 border-l-2 border-transparent'
                      }
                    `}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm leading-snug ${isSelected ? 'text-foreground font-medium' : 'text-foreground'} line-clamp-2`}>
                          {prompt}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[11px] text-muted-foreground">
                            {getRelativeTime(session.started_at)}
                          </span>
                          <span className="text-muted-foreground/50">·</span>
                          <span
                            className="text-[11px] text-muted-foreground font-mono hover:text-primary cursor-pointer transition-colors"
                            title={getSessionFilePath(session.project_path, session.id)}
                            onClick={(e) => {
                              e.stopPropagation();
                              const filePath = getSessionFilePath(session.project_path, session.id);
                              if (filePath) {
                                navigator.clipboard.writeText(filePath);
                              }
                            }}
                          >
                            {session.id.slice(0, 7)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border text-[11px] text-muted-foreground text-center">
        {sessions.length} session{sessions.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}
