/**
 * Message bubble component for conversation display.
 *
 * Renders user prompts, assistant responses, and session events.
 * Tool calls are now handled by ToolGroup component in SessionView.
 *
 * Related: SessionView.tsx (parent), ToolGroup.tsx (sibling), api/client.ts (Event type)
 */

import type { Event } from '../api/client';

interface MessageBubbleProps {
  event: Event;
}

export function MessageBubble({ event }: MessageBubbleProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const renderUserPrompt = () => {
    const prompt = event.data?.prompt as string;
    const images = event.data?.images as Array<{
      id?: string;
      url?: string;
      media_type?: string;
      base64?: string;
    }> | undefined;

    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-blue-600 text-white rounded-lg px-4 py-2">
          {/* Render images if present */}
          {images && images.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {images.map((img, idx) => {
                // Use URL if available, otherwise fall back to base64
                const src = img.url
                  ? img.url
                  : img.base64
                  ? `data:${img.media_type || 'image/png'};base64,${img.base64}`
                  : null;

                if (!src) return null;

                return (
                  <a
                    key={img.id || idx}
                    href={src}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    <img
                      src={src}
                      alt={`Image ${idx + 1}`}
                      className="max-w-xs max-h-48 rounded border border-blue-400 hover:opacity-90 transition-opacity"
                    />
                  </a>
                );
              })}
            </div>
          )}
          {/* User prompt with scrollbar for long content */}
          <div className="max-h-[400px] overflow-y-auto">
            <p className="whitespace-pre-wrap break-words">{prompt || 'User message'}</p>
          </div>
          <span className="text-xs text-blue-200 mt-1 block">
            {formatTime(event.timestamp)}
          </span>
        </div>
      </div>
    );
  };

  const renderAssistantResponse = () => {
    const transcript = event.data?.transcript as Array<Record<string, unknown>>;
    const tokenUsage = event.data?.token_usage as {
      input_tokens?: number;
      output_tokens?: number;
      cache_creation_input_tokens?: number;
      cache_read_input_tokens?: number;
      total_tokens?: number;
    } | null;

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

    // Format token numbers with K suffix for thousands
    const formatTokens = (n: number): string => {
      if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
      return n.toString();
    };

    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] bg-gray-700 text-gray-100 rounded-lg px-4 py-2">
          {/* Assistant response with scrollbar for long content */}
          <div className="max-h-[600px] overflow-y-auto">
            <p className="whitespace-pre-wrap break-words">
              {content || 'Assistant response'}
            </p>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-gray-400">
              {formatTime(event.timestamp)}
            </span>
            {tokenUsage && tokenUsage.total_tokens && tokenUsage.total_tokens > 0 && (
              <span className="text-xs text-cyan-400 font-mono">
                {formatTokens(tokenUsage.input_tokens || 0)} in / {formatTokens(tokenUsage.output_tokens || 0)} out
                {tokenUsage.cache_read_input_tokens && tokenUsage.cache_read_input_tokens > 0 && (
                  <span className="text-green-400"> ({formatTokens(tokenUsage.cache_read_input_tokens)} cached)</span>
                )}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Tool events are now handled by ToolGroup in SessionView
  // This is a fallback in case a single tool_use event needs rendering
  const renderToolUse = () => {
    const toolName = event.data?.tool_name as string;
    return (
      <div className="flex justify-start">
        <div className="text-xs text-gray-500 bg-gray-800 px-3 py-1 rounded">
          Tool: {toolName || 'unknown'} • {formatTime(event.timestamp)}
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

  const renderCompactEvent = () => {
    const command = event.data?.command as string || '/compact';
    const tokenUsage = event.data?.token_usage_before as {
      input_tokens?: number;
      output_tokens?: number;
      total_tokens?: number;
    } | null;

    const formatTokens = (n: number): string => {
      if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
      return n.toString();
    };

    return (
      <div className="flex justify-center">
        <div className="text-xs text-purple-400 bg-purple-900/30 border border-purple-700 px-3 py-1 rounded-full">
          {command}
          {tokenUsage && tokenUsage.total_tokens && (
            <span className="text-purple-300 ml-2">
              ({formatTokens(tokenUsage.total_tokens)} tokens before)
            </span>
          )}
          <span className="text-purple-500 ml-2">• {formatTime(event.timestamp)}</span>
        </div>
      </div>
    );
  };

  const renderNotification = () => {
    const notification = event.data?.notification as string || 'Notification';
    return (
      <div className="flex justify-center">
        <div className="text-xs text-orange-400 bg-orange-900/30 border border-orange-700 px-3 py-1 rounded-full">
          {notification} • {formatTime(event.timestamp)}
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
    case 'compact':
      return renderCompactEvent();
    case 'notification':
      return renderNotification();
    default:
      return (
        <div className="text-xs text-gray-500 text-center">
          Unknown event: {event.event_type}
        </div>
      );
  }
}
