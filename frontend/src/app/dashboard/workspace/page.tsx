'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { FileBrowser } from '@/components/workspace/FileBrowser';

export default function WorkspacePage() {
  return (
    <div className="h-full flex flex-col bg-background">
      <div className="p-4 lg:p-6 border-b border-border">
        <h1 className="text-2xl font-bold">Workspace</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Browse and manage files created by the agent in the workspace directory
        </p>
      </div>
      <FileBrowser />
    </div>
  );
}