/**
 * Tool group component for displaying multiple tool calls.
 *
 * Clean, compact design that doesn't overflow. Shows tool count
 * and names in a constrained layout. Uses Remix Icons.
 */

import { useState } from 'react';
import type { Event } from '../api/client';
import { formatTimeWithSeconds } from '../utils/time';

interface ToolGroupProps {
  events: Event[];
}

interface ToolItemProps {
  event: Event;
  isExpanded: boolean;
  onToggle: () => void;
}

// Tool name to icon/color mapping using Remix Icons
const TOOL_STYLES: Record<string, { icon: string; color: string }> = {
  Read: { icon: 'ri-file-text-line', color: 'text-[color:var(--info)]' },
  Write: { icon: 'ri-file-edit-line', color: 'text-[color:var(--success)]' },
  Edit: { icon: 'ri-edit-line', color: 'text-[color:var(--warning)]' },
  Bash: { icon: 'ri-terminal-box-line', color: 'text-[color:var(--cost)]' },
  Glob: { icon: 'ri-file-search-line', color: 'text-[color:var(--info)]' },
  Grep: { icon: 'ri-search-eye-line', color: 'text-[color:var(--info)]' },
  Task: { icon: 'ri-task-line', color: 'text-[color:var(--warning)]' },
  WebFetch: { icon: 'ri-global-line', color: 'text-[color:var(--info)]' },
  WebSearch: { icon: 'ri-earth-line', color: 'text-[color:var(--info)]' },
  TodoWrite: { icon: 'ri-checkbox-circle-line', color: 'text-[color:var(--success)]' },
  AskUserQuestion: { icon: 'ri-question-line', color: 'text-[color:var(--cost)]' },
  default: { icon: 'ri-tools-line', color: 'text-muted-foreground' },
};

function getToolStyle(toolName: string) {
  return TOOL_STYLES[toolName] || TOOL_STYLES.default;
}

function ToolItem({ event, isExpanded, onToggle }: ToolItemProps) {
  const [copied, setCopied] = useState(false);
  const toolName = event.data?.tool_name as string || 'unknown';
  const toolInput = event.data?.tool_input as Record<string, unknown>;
  const toolResult = event.data?.tool_result;
  const style = getToolStyle(toolName);

  const formatData = (data: unknown): string => {
    if (data === null || data === undefined) return '';
    return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  };

  // Format tool as copyable text (input + result)
  const formatToolText = (): string => {
    let output = `## ${toolName}\n`;
    if (toolInput && Object.keys(toolInput).length > 0) {
      output += `\n### Input\n\`\`\`json\n${formatData(toolInput)}\n\`\`\`\n`;
    }
    if (toolResult !== null && toolResult !== undefined) {
      output += `\n### Result\n\`\`\`json\n${formatData(toolResult)}\n\`\`\`\n`;
    }
    return output;
  };

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(formatToolText());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Get a preview of the tool input for collapsed view
  const getInputPreview = (): string => {
    if (!toolInput) return '';

    if (toolName === 'Read' && toolInput.file_path) {
      return String(toolInput.file_path).split('/').slice(-2).join('/');
    }
    if (toolName === 'Edit' && toolInput.file_path) {
      return String(toolInput.file_path).split('/').slice(-2).join('/');
    }
    if (toolName === 'Write' && toolInput.file_path) {
      return String(toolInput.file_path).split('/').slice(-2).join('/');
    }
    if (toolName === 'Bash' && toolInput.command) {
      const cmd = String(toolInput.command);
      return cmd.length > 40 ? cmd.slice(0, 40) + '...' : cmd;
    }
    if (toolName === 'Glob' && toolInput.pattern) {
      return String(toolInput.pattern);
    }
    if (toolName === 'Grep' && toolInput.pattern) {
      return String(toolInput.pattern);
    }

    return '';
  };

  const preview = getInputPreview();

  return (
    <div className="border-b border-border last:border-b-0 group/tool">
      <div className="flex items-center gap-3 px-3 py-2.5 hover:bg-accent/50 transition-colors">
        <button
          onClick={onToggle}
          className="flex-1 flex items-center gap-3 text-left"
        >
          <i className={`${style.icon} ${style.color} text-base`}></i>
          <div className="flex-1 min-w-0 flex items-center gap-2">
            <span className={`font-mono text-sm ${style.color}`}>{toolName}</span>
            {preview && !isExpanded && (
              <span className="text-xs text-muted-foreground truncate">{preview}</span>
            )}
          </div>
          <span className="text-[11px] text-muted-foreground opacity-0 group-hover/tool:opacity-100 transition-opacity">
            {formatTimeWithSeconds(event.timestamp)}
          </span>
          <i className={`ri-arrow-down-s-line text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`}></i>
        </button>
        {/* Copy button for this tool */}
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover/tool:opacity-100"
          title={copied ? 'Copied!' : 'Copy tool'}
        >
          <i className={`${copied ? 'ri-check-line text-[color:var(--success)]' : 'ri-file-copy-line'}`} />
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-3">
          {toolInput && Object.keys(toolInput).length > 0 && (
            <div>
              <div className="text-[11px] text-muted-foreground mb-1.5 uppercase tracking-wide">Input</div>
              <pre className="text-xs bg-muted p-3 rounded-lg overflow-x-auto overflow-y-auto max-h-[300px] text-foreground border border-border">
                {formatData(toolInput)}
              </pre>
            </div>
          )}
          {toolResult !== null && toolResult !== undefined && (
            <div>
              <div className="text-[11px] text-muted-foreground mb-1.5 uppercase tracking-wide">Result</div>
              <pre className="text-xs bg-muted p-3 rounded-lg overflow-x-auto overflow-y-auto max-h-[400px] text-foreground border border-border">
                {formatData(toolResult)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ToolGroup({ events }: ToolGroupProps) {
  const [isGroupExpanded, setIsGroupExpanded] = useState(false);
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [copiedAll, setCopiedAll] = useState(false);

  const toggleGroup = () => setIsGroupExpanded(!isGroupExpanded);

  const toggleTool = (eventId: number) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedTools(newExpanded);
  };

  // Format all tools into a single copyable string
  const formatAllTools = (): string => {
    return events.map((event, index) => {
      const toolName = event.data?.tool_name as string || 'unknown';
      const toolInput = event.data?.tool_input as Record<string, unknown>;
      const toolResult = event.data?.tool_result;

      const formatData = (data: unknown): string => {
        if (data === null || data === undefined) return '';
        return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
      };

      let output = `## Tool ${index + 1}: ${toolName}\n`;
      if (toolInput && Object.keys(toolInput).length > 0) {
        output += `\n### Input\n\`\`\`json\n${formatData(toolInput)}\n\`\`\`\n`;
      }
      if (toolResult !== null && toolResult !== undefined) {
        output += `\n### Result\n\`\`\`json\n${formatData(toolResult)}\n\`\`\`\n`;
      }
      return output;
    }).join('\n---\n\n');
  };

  const handleCopyAll = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent toggle when clicking copy
    try {
      await navigator.clipboard.writeText(formatAllTools());
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Get unique tool names for summary
  const toolNames = events.map((ev) => ev.data?.tool_name as string || 'unknown');
  const toolCounts: Record<string, number> = {};
  toolNames.forEach(name => {
    toolCounts[name] = (toolCounts[name] || 0) + 1;
  });

  // Format as compact badges
  const badges = Object.entries(toolCounts).slice(0, 4);
  const remaining = Object.keys(toolCounts).length - 4;

  return (
    <div className="group/toolgroup max-w-[70%] bg-muted/50 border border-border rounded-xl overflow-hidden">
      {/* Group header */}
      <div className="flex items-center justify-between px-4 py-3 hover:bg-accent/30 transition-colors">
        <button
          onClick={toggleGroup}
          className="flex-1 flex items-center gap-3"
        >
          <div className="flex items-center gap-1.5">
            <i className={`ri-arrow-down-s-line text-muted-foreground transition-transform ${isGroupExpanded ? 'rotate-180' : ''}`}></i>
            <i className="ri-tools-line text-muted-foreground"></i>
            <span className="text-sm font-medium text-foreground">
              Tools
            </span>
            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {events.length}
            </span>
          </div>

          {/* Tool badges - only show when collapsed */}
          {!isGroupExpanded && (
            <div className="flex items-center gap-1.5 ml-2">
              {badges.map(([name, count]) => {
                const style = getToolStyle(name);
                return (
                  <span
                    key={name}
                    className={`text-xs ${style.color} bg-muted px-2 py-0.5 rounded-full font-mono flex items-center gap-1`}
                  >
                    <i className={`${style.icon} text-[10px]`}></i>
                    {name}{count > 1 && <span className="text-muted-foreground">×{count}</span>}
                  </span>
                );
              })}
              {remaining > 0 && (
                <span className="text-xs text-muted-foreground">+{remaining}</span>
              )}
            </div>
          )}
        </button>

        {/* Copy All button */}
        <button
          onClick={handleCopyAll}
          className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover/toolgroup:opacity-100 ml-2"
          title={copiedAll ? 'Copied!' : 'Copy all tools'}
        >
          <i className={`${copiedAll ? 'ri-check-line text-[color:var(--success)]' : 'ri-file-copy-line'}`} />
          <span>{copiedAll ? 'Copied' : 'Copy All'}</span>
        </button>
      </div>

      {/* Tool list */}
      {isGroupExpanded && (
        <div className="border-t border-border max-h-[600px] overflow-y-auto">
          {events.map((event) => (
            <ToolItem
              key={event.id}
              event={event}
              isExpanded={expandedTools.has(event.id)}
              onToggle={() => toggleTool(event.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
