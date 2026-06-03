import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children, sidebar }) => {
  return (
    <div className="flex h-screen bg-white">
      {sidebar}
      {/* overflow-hidden is required so children with overflow-y-auto can actually scroll */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {children}
      </div>
    </div>
  );
};
