/**
 * Session list sidebar component.
 *
 * Displays list of sessions sorted by recency with search bar.
 * Highlights active session and shows live indicator.
 *
 * Related: api/client.ts (Session type), App.tsx (parent)
 */

import { useState } from 'react';
import type { Session } from '../api/client';

interface SessionListProps {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onSearch: (query: string) => void;
  isConnected: boolean;
}

export function SessionList({
  sessions,
  selectedId,
  onSelect,
  onSearch,
  isConnected,
}: SessionListProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getProjectName = (path: string | null) => {
    if (!path) return 'Unknown Project';
    const parts = path.split('/');
    return parts[parts.length - 1] || path;
  };

  const isActive = (session: Session) => {
    return session.started_at && !session.ended_at;
  };

  return (
    <div className="w-80 border-r border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-semibold">SuperTrace</h1>
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
        </div>

        {/* Search */}
        <form onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
          />
        </form>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-4 text-gray-500 text-sm text-center">
            No sessions yet
          </div>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelect(session.id)}
              className={`w-full p-3 text-left border-b border-gray-800 hover:bg-gray-800 transition-colors ${
                selectedId === session.id ? 'bg-gray-800' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm truncate">
                  {getProjectName(session.project_path)}
                </span>
                {isActive(session) && (
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                )}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {formatTime(session.started_at)}
              </div>
              <div className="text-xs text-gray-600 truncate mt-0.5">
                {session.id.slice(0, 8)}...
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
