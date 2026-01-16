/**
 * Draggable resize handle for panels.
 *
 * Creates a vertical divider that can be dragged to resize adjacent panels.
 * Related: App.tsx
 */

import { useRef, useCallback, useEffect } from 'react';

interface ResizeHandleProps {
  onResize: (deltaX: number) => void;
  onResizeEnd?: () => void;
  onDoubleClick?: () => void;
}

export function ResizeHandle({ onResize, onResizeEnd, onDoubleClick }: ResizeHandleProps) {
  const isDragging = useRef(false);
  const startX = useRef(0);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    startX.current = e.clientX;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const deltaX = e.clientX - startX.current;
      startX.current = e.clientX;
      onResize(deltaX);
    };

    const handleMouseUp = () => {
      if (isDragging.current) {
        isDragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        onResizeEnd?.();
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [onResize, onResizeEnd]);

  return (
    <div
      className="w-1 hover:w-1.5 bg-transparent hover:bg-primary/30 cursor-col-resize transition-all duration-150 shrink-0 group relative"
      onMouseDown={handleMouseDown}
      onDoubleClick={onDoubleClick}
    >
      {/* Visible indicator on hover */}
      <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-0.5 bg-border group-hover:bg-primary/50 transition-colors" />
    </div>
  );
}
