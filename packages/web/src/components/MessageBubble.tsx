/**
 * Message bubble component for conversation display.
 *
 * Clean, professional design with proper token stats display.
 */

import type { Event } from '../api/client';

interface MessageBubbleProps {
  event: Event;
}

export function MessageBubble({ event }: MessageBubbleProps) {
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
        <div className="max-w-[75%] bg-blue-600 rounded-2xl rounded-br-md px-4 py-3 shadow-lg">
          {/* Render images if present */}
          {images && images.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {images.map((img, idx) => {
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
                      className="max-w-[200px] max-h-40 rounded-lg border border-blue-400/30 hover:opacity-90 transition-opacity"
                    />
                  </a>
                );
              })}
            </div>
          )}
          <p className="text-white text-sm leading-relaxed whitespace-pre-wrap break-words">
            {prompt || 'User message'}
          </p>
          <div className="mt-2 text-right">
            <span className="text-[11px] text-blue-200/70">
              {formatTime(event.timestamp)}
            </span>
          </div>
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

    const formatTokens = (n: number): string => {
      if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
      return n.toString();
    };

    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] bg-gray-800/80 border border-gray-700/50 rounded-2xl rounded-bl-md px-4 py-3">
          <p className="text-gray-100 text-sm leading-relaxed whitespace-pre-wrap break-words">
            {content || 'Assistant response'}
          </p>

          {/* Footer with time and tokens */}
          <div className="mt-3 pt-2 border-t border-gray-700/50 flex items-center justify-between gap-4 flex-wrap">
            <span className="text-[11px] text-gray-500">
              {formatTime(event.timestamp)}
            </span>

            {tokenUsage && tokenUsage.total_tokens && tokenUsage.total_tokens > 0 && (
              <div className="flex items-center gap-3 text-[11px] font-mono">
                <span className="text-cyan-400/80">
                  {formatTokens(tokenUsage.input_tokens || 0)} in
                </span>
                <span className="text-gray-600">/</span>
                <span className="text-emerald-400/80">
                  {formatTokens(tokenUsage.output_tokens || 0)} out
                </span>
                {tokenUsage.cache_read_input_tokens && tokenUsage.cache_read_input_tokens > 0 && (
                  <>
                    <span className="text-gray-600">·</span>
                    <span className="text-purple-400/80">
                      {formatTokens(tokenUsage.cache_read_input_tokens)} cached
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderToolUse = () => {
    const toolName = event.data?.tool_name as string;
    return (
      <div className="flex justify-start">
        <div className="text-xs text-gray-500 bg-gray-800/50 px-3 py-1.5 rounded-lg border border-gray-800">
          Tool: {toolName || 'unknown'} · {formatTime(event.timestamp)}
        </div>
      </div>
    );
  };

  const renderSessionEvent = () => {
    const isStart = event.event_type === 'session_start';
    return (
      <div className="flex justify-center py-2">
        <div className="flex items-center gap-2 text-[11px] text-gray-500 bg-gray-900/50 px-4 py-1.5 rounded-full border border-gray-800">
          <div className={`w-1.5 h-1.5 rounded-full ${isStart ? 'bg-green-500' : 'bg-red-500'}`} />
          <span>{isStart ? 'Session started' : 'Session ended'}</span>
          <span className="text-gray-600">·</span>
          <span className="text-gray-600">{formatTime(event.timestamp)}</span>
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
      <div className="flex justify-center py-2">
        <div className="flex items-center gap-2 text-[11px] text-purple-400 bg-purple-900/20 px-4 py-1.5 rounded-full border border-purple-800/50">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span className="font-medium">{command}</span>
          {tokenUsage && tokenUsage.total_tokens && (
            <span className="text-purple-300/70">
              {formatTokens(tokenUsage.total_tokens)} tokens
            </span>
          )}
          <span className="text-purple-600">·</span>
          <span className="text-purple-600">{formatTime(event.timestamp)}</span>
        </div>
      </div>
    );
  };

  const renderNotification = () => {
    const notification = event.data?.notification as string || 'Notification';
    return (
      <div className="flex justify-center py-2">
        <div className="flex items-center gap-2 text-[11px] text-orange-400 bg-orange-900/20 px-4 py-1.5 rounded-full border border-orange-800/50">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <span>{notification}</span>
          <span className="text-orange-600">·</span>
          <span className="text-orange-600">{formatTime(event.timestamp)}</span>
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
        <div className="text-xs text-gray-600 text-center py-2">
          Unknown event: {event.event_type}
        </div>
      );
  }
}
