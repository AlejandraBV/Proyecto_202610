import React from 'react';
import { Sidebar } from '@/components/Sidebar';

interface LayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children, sidebar }) => {
  return (
    <div className="flex h-screen bg-white">
      {sidebar}
      <div className="flex-1 flex flex-col">
        {children}
      </div>
    </div>
  );
};
