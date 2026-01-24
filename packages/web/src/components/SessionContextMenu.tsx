/**
 * Session context menu component.
 *
 * 3-dot dropdown menu for session actions: Share, Copy Session ID, Delete.
 * Positioned absolutely on session item, appears on hover.
 */

import { useState, useRef, useEffect } from 'react';

export type SessionAction = 'share' | 'copy' | 'delete';

interface SessionContextMenuProps {
  sessionId: string;
  filePath: string;
  onAction: (action: SessionAction) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SessionContextMenu({
  sessionId: _sessionId,
  filePath,
  onAction,
  isOpen,
  onOpenChange,
}: SessionContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onOpenChange(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onOpenChange(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onOpenChange]);

  const handleCopySessionId = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(filePath);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
      onOpenChange(false);
    }, 1500);
    onAction('copy');
  };

  const handleShare = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenChange(false);
    onAction('share');
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenChange(false);
    onAction('delete');
  };

  const handleToggleMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenChange(!isOpen);
  };

  return (
    <div ref={menuRef} className="relative">
      {/* 3-dot button */}
      <button
        onClick={handleToggleMenu}
        className="p-1 rounded hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
        aria-label="Session options"
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <i className="ri-more-2-fill text-base"></i>
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-1 w-44 bg-card border border-border rounded-lg shadow-xl z-[100] overflow-hidden py-1"
        >
          {/* Share */}
          <button
            role="menuitem"
            onClick={handleShare}
            className="w-full px-3 py-2 text-sm text-left hover:bg-accent transition-colors flex items-center gap-2.5 text-foreground"
          >
            <i className="ri-share-line text-muted-foreground"></i>
            <span>Share</span>
          </button>

          {/* Copy Session ID */}
          <button
            role="menuitem"
            onClick={handleCopySessionId}
            className="w-full px-3 py-2 text-sm text-left hover:bg-accent transition-colors flex items-center gap-2.5 text-foreground"
          >
            <i className={`${copied ? 'ri-check-line text-[color:var(--success)]' : 'ri-file-copy-line text-muted-foreground'}`}></i>
            <span>{copied ? 'Copied!' : 'Copy Session ID'}</span>
          </button>

          {/* Divider */}
          <div className="h-px bg-border my-1"></div>

          {/* Delete */}
          <button
            role="menuitem"
            onClick={handleDelete}
            className="w-full px-3 py-2 text-sm text-left hover:bg-destructive/10 transition-colors flex items-center gap-2.5 text-destructive"
          >
            <i className="ri-delete-bin-line"></i>
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  );
}
