/**
 * Message bubble component for conversation display.
 *
 * Clean, professional design with proper token stats display.
 * Uses Remix Icons and QuickCall color system.
 */

import { useState, useEffect } from 'react';
import type { Event } from '../api/client';
import { formatTime } from '../utils/time';

interface MessageBubbleProps {
  event: Event;
  searchQuery?: string;
  showAllThinking?: boolean;
}

const MAX_COLLAPSED_LENGTH = 500; // Characters before truncating

// Highlight exact substring matches (case-insensitive)
function highlightText(text: string, query: string | undefined): React.ReactNode {
  if (!query?.trim() || !text) return text;
  if (query.length < 2) return text; // Require at least 2 chars

  // Escape regex special characters and do case-insensitive match
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);

  if (parts.length === 1) return text;

  return parts.map((part, i) =>
    regex.test(part)
      ? <mark key={i} className="bg-yellow-400/50 dark:bg-yellow-500/40 text-inherit rounded-sm px-0.5">{part}</mark>
      : part
  );
}

// Reusable copy button component
function CopyButton({ text, copied, onCopy }: { text: string; copied: boolean; onCopy: (text: string) => void }) {
  return (
    <button
      onClick={() => onCopy(text)}
      className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
      title={copied ? 'Copied!' : 'Copy to clipboard'}
    >
      <i className={`${copied ? 'ri-check-line text-[color:var(--success)]' : 'ri-file-copy-line'}`} />
      <span>{copied ? 'Copied' : 'Copy'}</span>
    </button>
  );
}

export function MessageBubble({ event, searchQuery, showAllThinking = false }: MessageBubbleProps) {
  const [expanded, setExpanded] = useState(false);
  const [thinkingExpanded, setThinkingExpanded] = useState(showAllThinking);
  const [copied, setCopied] = useState(false);

  // Copy text to clipboard with visual feedback
  const handleCopy = async (text: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Sync with global toggle
  useEffect(() => {
    setThinkingExpanded(showAllThinking);
  }, [showAllThinking]);

  const renderUserPrompt = () => {
    const prompt = event.data?.prompt as string;
    const promptIndex = event.data?.promptIndex as number | undefined;
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
      <div className="group flex flex-col items-end gap-1">
        <div className="flex justify-end items-start gap-2 w-full">
          {/* Prompt number badge - from backend to ensure correct numbering */}
          {promptIndex && (
            <div className="shrink-0 w-6 h-6 mt-3 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-semibold" title={`Prompt ${promptIndex}`}>
              {promptIndex}
            </div>
          )}
          <div className="max-w-[85%] sm:max-w-[75%] bg-[color:var(--user-bubble)] text-[color:var(--user-bubble-foreground)] rounded-2xl rounded-br-md px-3 py-2 sm:px-4 sm:py-3 shadow-sm">
            {/* Render images if present */}
            {images && images.length > 0 && (
              <div className="mb-2 sm:mb-3 flex flex-wrap gap-1.5 sm:gap-2">
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
                {highlightText(displayPrompt || 'User message', searchQuery)}
              </p>

              {/* Gradient fade + Show more button */}
              {isLong && !expanded && (
                <div className="absolute bottom-0 left-0 right-0 pt-10 bg-gradient-to-t from-[color:var(--user-bubble)] via-[color:var(--user-bubble)]/90 to-transparent">
                  <button
                    onClick={() => setExpanded(true)}
                    className="text-sm font-medium text-[color:var(--user-bubble-foreground)]/80 hover:text-[color:var(--user-bubble-foreground)] hover:underline transition-colors"
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
                className="mt-2 text-sm font-medium text-[color:var(--user-bubble-foreground)]/80 hover:text-[color:var(--user-bubble-foreground)] hover:underline transition-colors"
              >
                Show less
              </button>
            )}

            <div className="mt-2 text-right">
              <span className="text-[11px] text-[color:var(--user-bubble-foreground)]/60">
                {formatTime(event.timestamp)}
              </span>
            </div>
          </div>
        </div>
        {/* Copy button below bubble */}
        <div className="mr-1">
          <CopyButton text={prompt || ''} copied={copied} onCopy={handleCopy} />
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
    const thinkingContent = event.data?.thinkingContent as string | undefined;

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

    // Determine what to show based on content and thinking
    const hasContent = content.trim().length > 0;
    const hasThinking = !!thinkingContent;

    // Build copyable text: content first, then thinking
    const copyableText = [content, thinkingContent].filter(Boolean).join('\n\n---\n\n');

    return (
      <div className="group flex flex-col items-start gap-1">
        <div className="flex justify-start w-full">
          <div className="max-w-[85%] sm:max-w-[70%] bg-[color:var(--assistant-bubble)] text-[color:var(--assistant-bubble-foreground)] border border-border rounded-2xl rounded-bl-md px-3 py-2 sm:px-4 sm:py-3">
            {/* Thinking section - collapsible dropdown */}
            {hasThinking && (
              <div className={hasContent ? "mb-3" : ""}>
                <div className="flex items-start gap-2">
                  <button
                    onClick={() => setThinkingExpanded(!thinkingExpanded)}
                    className="mt-2 hover:opacity-80 transition-opacity"
                  >
                    <i className={`ri-arrow-down-s-line text-base text-muted-foreground transition-transform ${thinkingExpanded ? 'rotate-180' : ''}`} />
                  </button>
                  <div className="flex-1 bg-purple-500/10 border border-purple-500/20 rounded-lg overflow-hidden">
                    <button
                      onClick={() => setThinkingExpanded(!thinkingExpanded)}
                      className="w-full px-3 py-2 flex items-center gap-1.5 text-sm text-purple-400 hover:bg-purple-500/10 transition-colors"
                    >
                      <i className="ri-brain-line" />
                      Thinking
                    </button>
                    {thinkingExpanded && (
                      <div className="px-3 pb-3">
                        <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed max-h-96 overflow-y-auto">
                          {thinkingContent}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Content section - only show if there's actual content */}
            {hasContent ? (
              <>
                <div className="relative">
                  <div className="overflow-x-auto max-w-full">
                    <pre className="text-[color:var(--assistant-bubble-foreground)] text-sm leading-relaxed whitespace-pre-wrap font-sans [&_*]:font-sans">
                      {highlightText(displayContent, searchQuery)}
                    </pre>
                  </div>

                  {/* Gradient fade + Show more button */}
                  {isLong && !expanded && (
                    <div className="absolute bottom-0 left-0 right-0 pt-10 bg-gradient-to-t from-[color:var(--assistant-bubble)] via-[color:var(--assistant-bubble)]/90 to-transparent">
                      <button
                        onClick={() => setExpanded(true)}
                        className="text-sm font-medium text-[color:var(--assistant-bubble-foreground)] hover:underline transition-colors"
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
                    className="mt-2 text-sm font-medium text-[color:var(--assistant-bubble-foreground)] hover:underline transition-colors"
                  >
                    Show less
                  </button>
                )}
              </>
            ) : !hasThinking ? (
              <div className="text-sm text-muted-foreground italic">
                No text output
              </div>
            ) : null}

            {/* Footer with time and tokens */}
            <div className="mt-2 sm:mt-3 pt-2 border-t border-border flex items-center justify-between gap-2 sm:gap-4 flex-wrap">
              <span className="text-[11px] text-muted-foreground">
                {formatTime(event.timestamp)}
              </span>

              {tokenUsage && tokenUsage.total_tokens && tokenUsage.total_tokens > 0 && (
                <div className="flex items-center gap-2 sm:gap-3 text-[11px] font-mono">
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
        {/* Copy button below bubble */}
        {(hasContent || hasThinking) && (
          <div className="ml-1">
            <CopyButton text={copyableText} copied={copied} onCopy={handleCopy} />
          </div>
        )}
      </div>
    );
  };

  const renderToolUse = () => {
    const toolName = event.data?.tool_name as string;
    const toolInput = event.data?.tool_input as Record<string, unknown> | undefined;

    // Build copyable text for tool use
    const copyableText = toolInput
      ? `Tool: ${toolName}\nInput: ${JSON.stringify(toolInput, null, 2)}`
      : `Tool: ${toolName}`;

    return (
      <div className="group flex flex-col items-start gap-1">
        <div className="flex justify-start">
          <div className="text-xs text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-lg border border-border flex items-center gap-2">
            <i className="ri-tools-line"></i>
            <span>{toolName || 'unknown'}</span>
            <span className="text-muted-foreground/50">·</span>
            <span className="text-muted-foreground/70">{formatTime(event.timestamp)}</span>
          </div>
        </div>
        {/* Copy button below bubble */}
        <div className="ml-1">
          <CopyButton text={copyableText} copied={copied} onCopy={handleCopy} />
        </div>
      </div>
    );
  };

  const renderSessionEvent = () => {
    const isStart = event.event_type === 'session_start';
    const text = isStart ? 'Session started' : 'Session ended';

    return (
      <div className="group flex flex-col items-center gap-1 py-2">
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground bg-muted/50 px-4 py-1.5 rounded-full border border-border">
          <i className={`${isStart ? 'ri-play-circle-line text-[color:var(--success)]' : 'ri-stop-circle-line text-destructive'}`}></i>
          <span>{text}</span>
          <span className="text-muted-foreground/50">·</span>
          <span className="text-muted-foreground/70">{formatTime(event.timestamp)}</span>
        </div>
        {/* Copy button below bubble */}
        <CopyButton text={`${text} at ${formatTime(event.timestamp)}`} copied={copied} onCopy={handleCopy} />
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

    const copyableText = tokenUsage?.total_tokens
      ? `${command} - ${formatTokens(tokenUsage.total_tokens)} tokens`
      : command;

    return (
      <div className="group flex flex-col items-center gap-1 py-2">
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
        {/* Copy button below bubble */}
        <CopyButton text={copyableText} copied={copied} onCopy={handleCopy} />
      </div>
    );
  };

  const renderNotification = () => {
    const notification = event.data?.notification as string || 'Notification';

    return (
      <div className="group flex flex-col items-center gap-1 py-2">
        <div className="flex items-center gap-2 text-[11px] text-[color:var(--warning)] bg-[color:var(--warning)]/10 px-4 py-1.5 rounded-full border border-[color:var(--warning)]/30">
          <i className="ri-notification-3-line"></i>
          <span>{notification}</span>
          <span className="opacity-50">·</span>
          <span className="opacity-50">{formatTime(event.timestamp)}</span>
        </div>
        {/* Copy button below bubble */}
        <CopyButton text={notification} copied={copied} onCopy={handleCopy} />
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
