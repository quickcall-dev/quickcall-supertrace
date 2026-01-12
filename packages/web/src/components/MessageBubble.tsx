/**
 * Message bubble component for conversation display.
 *
 * Clean, professional design with proper token stats display.
 * Uses Remix Icons and QuickCall color system.
 */

import { useState } from 'react';
import type { Event } from '../api/client';
import { formatTime } from '../utils/time';

interface MessageBubbleProps {
  event: Event;
}

const MAX_COLLAPSED_LENGTH = 500; // Characters before truncating

export function MessageBubble({ event }: MessageBubbleProps) {
  const [expanded, setExpanded] = useState(false);

  const renderUserPrompt = () => {
    const prompt = event.data?.prompt as string;
    const images = event.data?.images as Array<{
      id?: string;
      url?: string;
      media_type?: string;
      base64?: string;
    }> | undefined;

    const isLong = prompt && prompt.length > MAX_COLLAPSED_LENGTH;
    const displayPrompt = expanded || !isLong
      ? prompt
      : prompt?.slice(0, MAX_COLLAPSED_LENGTH);

    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-3 shadow-sm">
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
                      className="max-w-[200px] max-h-40 rounded-lg border border-primary-foreground/20 hover:opacity-90 transition-opacity"
                    />
                  </a>
                );
              })}
            </div>
          )}
          <div className="relative">
            <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
              {displayPrompt || 'User message'}
            </p>

            {/* Gradient fade + Show more button */}
            {isLong && !expanded && (
              <div className="absolute bottom-0 left-0 right-0 pt-10 bg-gradient-to-t from-primary via-primary/90 to-transparent">
                <button
                  onClick={() => setExpanded(true)}
                  className="text-sm font-medium text-primary-foreground/80 hover:text-primary-foreground hover:underline transition-colors"
                >
                  Show more
                </button>
              </div>
            )}
          </div>

          {/* Show less button when expanded */}
          {isLong && expanded && (
            <button
              onClick={() => setExpanded(false)}
              className="mt-2 text-sm font-medium text-primary-foreground/80 hover:text-primary-foreground hover:underline transition-colors"
            >
              Show less
            </button>
          )}

          <div className="mt-2 text-right">
            <span className="text-[11px] text-primary-foreground/60">
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

    // First try to get message directly (from reimport)
    if (event.data?.message && typeof event.data.message === 'string') {
      content = event.data.message;
    }
    // Fallback: extract from transcript (from live hooks)
    else if (transcript && Array.isArray(transcript)) {
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

    const isLong = content.length > MAX_COLLAPSED_LENGTH;
    const displayContent = expanded || !isLong
      ? content
      : content.slice(0, MAX_COLLAPSED_LENGTH);

    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] bg-muted border border-border rounded-2xl rounded-bl-md px-4 py-3">
          <div className="relative">
            <div className="overflow-x-auto max-w-full">
              <pre className="text-foreground text-sm leading-relaxed whitespace-pre-wrap font-sans [&_*]:font-sans">
                {displayContent || 'Assistant response'}
              </pre>
            </div>

            {/* Gradient fade + Show more button */}
            {isLong && !expanded && (
              <div className="absolute bottom-0 left-0 right-0 pt-10 bg-gradient-to-t from-muted via-muted/90 to-transparent">
                <button
                  onClick={() => setExpanded(true)}
                  className="text-sm font-medium text-foreground hover:underline transition-colors"
                >
                  Show more
                </button>
              </div>
            )}
          </div>

          {/* Show less button when expanded */}
          {isLong && expanded && (
            <button
              onClick={() => setExpanded(false)}
              className="mt-2 text-sm font-medium text-foreground hover:underline transition-colors"
            >
              Show less
            </button>
          )}

          {/* Footer with time and tokens */}
          <div className="mt-3 pt-2 border-t border-border flex items-center justify-between gap-4 flex-wrap">
            <span className="text-[11px] text-muted-foreground">
              {formatTime(event.timestamp)}
            </span>

            {tokenUsage && tokenUsage.total_tokens && tokenUsage.total_tokens > 0 && (
              <div className="flex items-center gap-3 text-[11px] font-mono">
                <span className="text-[color:var(--info)] flex items-center gap-1">
                  <i className="ri-arrow-down-line text-[10px]"></i>
                  {formatTokens(tokenUsage.input_tokens || 0)}
                </span>
                <span className="text-[color:var(--success)] flex items-center gap-1">
                  <i className="ri-arrow-up-line text-[10px]"></i>
                  {formatTokens(tokenUsage.output_tokens || 0)}
                </span>
                {tokenUsage.cache_read_input_tokens && tokenUsage.cache_read_input_tokens > 0 && (
                  <span className="text-[color:var(--cost)] flex items-center gap-1">
                    <i className="ri-database-2-line text-[10px]"></i>
                    {formatTokens(tokenUsage.cache_read_input_tokens)}
                  </span>
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
        <div className="text-xs text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-lg border border-border flex items-center gap-2">
          <i className="ri-tools-line"></i>
          <span>{toolName || 'unknown'}</span>
          <span className="text-muted-foreground/50">·</span>
          <span className="text-muted-foreground/70">{formatTime(event.timestamp)}</span>
        </div>
      </div>
    );
  };

  const renderSessionEvent = () => {
    const isStart = event.event_type === 'session_start';
    return (
      <div className="flex justify-center py-2">
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground bg-muted/50 px-4 py-1.5 rounded-full border border-border">
          <i className={`${isStart ? 'ri-play-circle-line text-[color:var(--success)]' : 'ri-stop-circle-line text-destructive'}`}></i>
          <span>{isStart ? 'Session started' : 'Session ended'}</span>
          <span className="text-muted-foreground/50">·</span>
          <span className="text-muted-foreground/70">{formatTime(event.timestamp)}</span>
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
        <div className="flex items-center gap-2 text-[11px] text-[color:var(--info)] bg-[color:var(--info)]/10 px-4 py-1.5 rounded-full border border-[color:var(--info)]/30">
          <i className="ri-refresh-line"></i>
          <span className="font-medium">{command}</span>
          {tokenUsage && tokenUsage.total_tokens && (
            <span className="opacity-70">
              {formatTokens(tokenUsage.total_tokens)} tokens
            </span>
          )}
          <span className="opacity-50">·</span>
          <span className="opacity-50">{formatTime(event.timestamp)}</span>
        </div>
      </div>
    );
  };

  const renderNotification = () => {
    const notification = event.data?.notification as string || 'Notification';
    return (
      <div className="flex justify-center py-2">
        <div className="flex items-center gap-2 text-[11px] text-[color:var(--warning)] bg-[color:var(--warning)]/10 px-4 py-1.5 rounded-full border border-[color:var(--warning)]/30">
          <i className="ri-notification-3-line"></i>
          <span>{notification}</span>
          <span className="opacity-50">·</span>
          <span className="opacity-50">{formatTime(event.timestamp)}</span>
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
        <div className="text-xs text-muted-foreground text-center py-2">
          Unknown event: {event.event_type}
        </div>
      );
  }
}
