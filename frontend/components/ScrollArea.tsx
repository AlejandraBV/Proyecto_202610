import React, { useEffect, useRef } from 'react';

interface ScrollAreaProps {
  children: React.ReactNode;
  className?: string;
}

export const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(
  ({ children, className = '' }, ref) => {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }, [children]);

    return (
      <div
        ref={scrollRef}
        className={`overflow-y-auto ${className}`}
      >
        {children}
      </div>
    );
  }
);

ScrollArea.displayName = 'ScrollArea';
