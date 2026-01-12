/**
 * Session list sidebar component.
 *
 * Displays sessions grouped by date with first prompt as identifier.
 * Clean, professional design for enterprise use.
 */

import { useState, useMemo } from 'react';
import type { Session } from '../api/client';

interface SessionListProps {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onSearch: (query: string) => void;
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

export function SessionList({
  sessions,
  selectedId,
  onSelect,
  onSearch,
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
    <div className="w-72 border-r border-gray-800 flex flex-col h-full bg-gray-950">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <i className="ri-flashlight-line text-white text-sm"></i>
          </div>
          <span className="font-semibold text-gray-100">SuperTrace</span>
        </div>

        {/* Search */}
        <form onSubmit={handleSearch}>
          <div className="relative">
            <i className="ri-search-line absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm"></i>
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="w-full pl-9 pr-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-700 focus:ring-1 focus:ring-gray-700 transition-all"
            />
          </div>
        </form>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-8 text-center">
            <div className="w-12 h-12 mx-auto mb-3 bg-gray-900 rounded-full flex items-center justify-center">
              <i className="ri-chat-3-line text-gray-600 text-xl"></i>
            </div>
            <p className="text-sm text-gray-500">No sessions yet</p>
            <p className="text-xs text-gray-600 mt-1">Start a Claude session to see it here</p>
          </div>
        ) : (
          groupedSessions.map(({ group, sessions: groupSessions }) => (
            <div key={group}>
              {/* Group Header */}
              <div className="px-4 py-2 text-[11px] font-medium text-gray-500 uppercase tracking-wider sticky top-0 bg-gray-950/95 backdrop-blur-sm border-b border-gray-900">
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
                        ? 'bg-gray-800/80 border-l-2 border-blue-500'
                        : 'hover:bg-gray-900/50 border-l-2 border-transparent'
                      }
                    `}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm leading-snug ${isSelected ? 'text-gray-100' : 'text-gray-300'} line-clamp-2`}>
                          {prompt}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[11px] text-gray-600">
                            {getRelativeTime(session.started_at)}
                          </span>
                          <span className="text-gray-800">·</span>
                          <span className="text-[11px] text-gray-600 font-mono">
                            {session.id.slice(0, 6)}
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
      <div className="p-3 border-t border-gray-800 text-[11px] text-gray-600 text-center">
        {sessions.length} session{sessions.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}
