/**
 * Message bubble component for conversation display.
 *
 * Renders user prompts, assistant responses, and tool calls
 * with appropriate styling and collapsible sections.
 *
 * Related: SessionView.tsx (parent), api/client.ts (Event type)
 */

import { useState } from 'react';
import type { Event } from '../api/client';

interface MessageBubbleProps {
  event: Event;
}

export function MessageBubble({ event }: MessageBubbleProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const renderUserPrompt = () => {
    const prompt = (event.data?.tool_input as Record<string, unknown>)?.prompt as string;
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-blue-600 text-white rounded-lg px-4 py-2">
          <p className="whitespace-pre-wrap">{prompt || 'User message'}</p>
          <span className="text-xs text-blue-200 mt-1 block">
            {formatTime(event.timestamp)}
          </span>
        </div>
      </div>
    );
  };

  const renderAssistantResponse = () => {
    const transcript = event.data?.transcript as Array<Record<string, unknown>>;
    let content = '';

    if (transcript && Array.isArray(transcript)) {
      // Find last assistant message
      for (let i = transcript.length - 1; i >= 0; i--) {
        const msg = transcript[i];
        if (msg?.type === 'assistant') {
          const messageContent = (msg?.message as Record<string, unknown>)?.content;
          if (Array.isArray(messageContent)) {
            for (const block of messageContent) {
              if ((block as Record<string, unknown>)?.type === 'text') {
                content = (block as Record<string, unknown>)?.text as string || '';
                break;
              }
            }
          }
          break;
        }
      }
    }

    return (
      <div className="flex justify-start">
        <div className="max-w-[80%] bg-gray-700 text-gray-100 rounded-lg px-4 py-2">
          <p className="whitespace-pre-wrap">
            {content || 'Assistant response'}
          </p>
          <span className="text-xs text-gray-400 mt-1 block">
            {formatTime(event.timestamp)}
          </span>
        </div>
      </div>
    );
  };

  const renderToolUse = () => {
    const toolName = event.data?.tool_name as string;
    const toolInput = event.data?.tool_input as Record<string, unknown>;

    return (
      <div className="flex justify-start">
        <div className="max-w-[90%] bg-gray-800 border border-gray-600 rounded-lg px-4 py-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm font-mono text-yellow-400"
          >
            <span>{isExpanded ? '▼' : '▶'}</span>
            <span>Tool: {toolName || 'unknown'}</span>
          </button>

          {isExpanded && toolInput && (
            <pre className="mt-2 text-xs bg-gray-900 p-2 rounded overflow-x-auto">
              {JSON.stringify(toolInput, null, 2)}
            </pre>
          )}

          <span className="text-xs text-gray-500 mt-1 block">
            {formatTime(event.timestamp)}
          </span>
        </div>
      </div>
    );
  };

  const renderSessionEvent = () => {
    const isStart = event.event_type === 'session_start';
    return (
      <div className="flex justify-center">
        <div className="text-xs text-gray-500 bg-gray-800 px-3 py-1 rounded-full">
          {isStart ? 'Session started' : 'Session ended'} •{' '}
          {formatTime(event.timestamp)}
        </div>
      </div>
    );
  };

  switch (event.event_type) {
    case 'user_prompt':
      return renderUserPrompt();
    case 'assistant_stop':
      return renderAssistantResponse();
    case 'tool_use':
      return renderToolUse();
    case 'session_start':
    case 'session_end':
      return renderSessionEvent();
    default:
      return (
        <div className="text-xs text-gray-500 text-center">
          Unknown event: {event.event_type}
        </div>
      );
  }
}
