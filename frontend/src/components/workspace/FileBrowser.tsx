'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  FolderOpen,
  File,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Search,
  Home,
  FolderPlus,
  FilePlus,
  Download,
  MoreHorizontal,
  Trash2,
  Edit,
  Copy,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileNode {
  path: string;
  name: string;
  size: number;
  is_dir: boolean;
  modified_at: string;
  children?: FileNode[];
  expanded?: boolean;
}

interface FileBrowserProps {
  initialPath?: string;
}

export function FileBrowser({ initialPath = '' }: FileBrowserProps) {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [files, setFiles] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [showContent, setShowContent] = useState(false);
  const [creatingFile, setCreatingFile] = useState(false);
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [newItemPath, setNewItemPath] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');

  const loadFiles = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listFiles(path, true);
      const fileNodes = (data.files || []).map((f: any) => ({
        path: f.path,
        name: f.name,
        size: f.size,
        is_dir: f.is_dir,
        modified_at: f.modified_at,
        children: f.is_dir ? [] : undefined,
        expanded: false,
      }));
      setFiles(fileNodes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load files');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFiles(currentPath);
  }, [currentPath, loadFiles]);

  const handleFileClick = async (file: FileNode) => {
    if (file.is_dir) {
      // Navigate into folder
      setCurrentPath(file.path);
      return;
    }

    // Select file
    setSelectedFile(file);
    setShowContent(true);

    // Load file content
    try {
      const data = await api.readFile(file.path);
      setFileContent(data.content || '');
    } catch (e) {
      setFileContent(`Error loading file: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const handleFolderToggle = (file: FileNode) => {
    // Toggle expansion - in this simple version, we just navigate
    setCurrentPath(file.path);
  };

  const goUp = () => {
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '';
    setCurrentPath(parentPath);
  };

  const goHome = () => {
    setCurrentPath('');
  };

  const handleCreateFile = async () => {
    if (!newItemName.trim()) return;
    try {
      const fullPath = `${newItemPath}/${newItemName}`;
      await api.writeFile(fullPath, '', 'utf-8', true);
      setCreatingFile(false);
      setNewItemName('');
      loadFiles(currentPath);
    } catch (e) {
      alert(`Failed to create file: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const handleCreateFolder = async () => {
    if (!newItemName.trim()) return;
    try {
      const fullPath = `${newItemPath}/${newItemName}`;
      await api.writeFile(fullPath, '', 'utf-8', true); // Creates directory
      setCreatingFolder(false);
      setNewItemName('');
      loadFiles(currentPath);
    } catch (e) {
      alert(`Failed to create folder: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const handleOpenCreateFile = (parentPath: string) => {
    setNewItemPath(parentPath);
    setCreatingFile(true);
  };

  const handleOpenCreateFolder = (parentPath: string) => {
    setNewItemPath(parentPath);
    setCreatingFolder(true);
  };

  const handleDelete = async (file: FileNode) => {
    if (!confirm(`Delete ${file.name}?`)) return;
    try {
      await api.writeFile(file.path, '', 'utf-8', false); // This would need a delete endpoint
      loadFiles(currentPath);
    } catch (e) {
      alert(`Failed to delete: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const handleDownload = async (file: FileNode) => {
    try {
      const data = await api.readFile(file.path);
      const blob = new Blob([data.content || ''], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Failed to download: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedFile) return;
    try {
      await api.writeFile(selectedFile.path, editContent, 'utf-8', true);
      setFileContent(editContent);
      setIsEditing(false);
      loadFiles(currentPath);
    } catch (e) {
      alert(`Failed to save: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const filteredFiles = files.filter(f =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-2 p-3 border-b border-border bg-muted/30">
        <Button variant="ghost" size="icon" onClick={goHome} title="Workspace root">
          <Home className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={goUp} title="Go up" disabled={currentPath === '/workspace'}>
          <ChevronRight className="h-4 w-4 rotate-180" />
        </Button>
        <div className="flex-1 flex items-center gap-2 min-w-0">
          <Input
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="max-w-xs"
          />
        </div>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" onClick={() => handleOpenCreateFile(currentPath)}>
            <FilePlus className="h-3.5 w-3.5 mr-1" />
            <span className="hidden sm:inline">New File</span>
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleOpenCreateFolder(currentPath)}>
            <FolderPlus className="h-3.5 w-3.5 mr-1" />
            <span className="hidden sm:inline">New Folder</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={() => loadFiles(currentPath)} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Current path breadcrumb */}
      <div className="px-3 py-2 border-b border-border bg-muted/20 text-sm text-muted-foreground flex items-center gap-1 overflow-x-auto">
        <span className="flex items-center gap-1">
          <Home className="h-3 w-3" />
          <Button variant="ghost" size="sm" className="p-0 h-auto" onClick={goHome}>workspace</Button>
        </span>
        {currentPath && (
          <>
            {currentPath
              .split('/')
              .filter(Boolean)
              .map((segment, idx, arr) => {
                const path = arr.slice(0, idx + 1).join('/');
                return (
                  <span key={path} className="flex items-center gap-1">
                    <ChevronRight className="h-3 w-3" />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="p-0 h-auto"
                      onClick={() => setCurrentPath(path)}
                    >
                      {segment}
                    </Button>
                  </span>
                );
              })}
          </>
        )}
      </div>

      {/* Main content - split view */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Tree */}
        <div className="w-80 border-r border-border bg-card flex flex-col overflow-hidden">
          {creatingFile && (
            <div className="p-2 border-b border-border bg-muted/30">
              <div className="flex gap-2">
                <Input
                  value={newItemName}
                  onChange={(e) => setNewItemName(e.target.value)}
                  placeholder="filename.txt"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleCreateFile();
                    if (e.key === 'Escape') setCreatingFile(false);
                  }}
                  autoFocus
                  className="flex-1"
                />
                <Button size="sm" onClick={handleCreateFile}>Create</Button>
                <Button variant="ghost" size="sm" onClick={() => setCreatingFile(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">Creating in: {newItemPath}</p>
            </div>
          )}

          {creatingFolder && (
            <div className="p-2 border-b border-border.bg-muted/30">
              <div className="flex gap-2">
                <Input
                  value={newItemName}
                  onChange={(e) => setNewItemName(e.target.value)}
                  placeholder="folder-name"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleCreateFolder();
                    if (e.key === 'Escape') setCreatingFolder(false);
                  }}
                  autoFocus
                  className="flex-1"
                />
                <Button size="sm" onClick={handleCreateFolder}>Create</Button>
                <Button variant="ghost" size="sm" onClick={() => setCreatingFolder(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">Creating in: {newItemPath}</p>
            </div>
          )}

          <ScrollArea className="flex-1 overflow-y-auto p-2">
            {loading ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <RefreshCw className="h-5 w-5 animate-spin" />
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-full text-destructive">
                <p>Error: {error}</p>
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <FolderOpen className="h-12 w-12 opacity-50 mb-2" />
                <p className="text-sm">No files found</p>
                <p className="text-xs text-muted-foreground/50">
                  {searchQuery ? 'Try adjusting your search' : 'Create a file or folder to get started'}
                </p>
              </div>
            ) : (
              <ul className="space-y-0.5" role="tree">
                {filteredFiles.map((file) => (
                  <FileTreeNode
                    key={file.path}
                    file={file}
                    selected={selectedFile?.path === file.path}
                    onClick={handleFileClick}
                    onCreateFile={handleOpenCreateFile}
                    onCreateFolder={handleOpenCreateFolder}
                    onDelete={handleDelete}
                    onDownload={handleDownload}
                  />
                ))}
              </ul>
            )}
          </ScrollArea>
        </div>

        {/* File Preview / Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {showContent && selectedFile ? (
            <>
              <div className="flex items-center justify-between p-3 border-b border-border bg-muted/30">
                <div className="flex items-center gap-2 min-w-0">
                  <File className="h-4 w-4 text-muted-foreground" />
                  <span className="truncate font-medium">{selectedFile.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({selectedFile.path})
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={() => navigator.clipboard.writeText(fileContent)} title="Copy content">
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDownload(selectedFile!)} title="Download">
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => setIsEditing(!isEditing)} title={isEditing ? 'View' : 'Edit'}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => { setShowContent(false); setSelectedFile(null); }} title="Close">
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                {isEditing ? (
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full h-full p-4 font-mono text-sm resize-none border-none focus:outline-none bg-background"
                    spellCheck={false}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') setIsEditing(false);
                    }}
                  />
                ) : (
                  <ScrollArea className="h-full p-4">
                    <pre className="font-mono text-sm whitespace-pre-wrap word-break-break-all text-foreground">
                      {fileContent}
                    </pre>
                  </ScrollArea>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <File className="h-16 w-16 mx-auto opacity-30 mb-4" />
                <p className="text-lg">Select a file to preview</p>
                <p className="text-sm mt-1">Click on any file in the tree to view its contents</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface FileTreeNodeProps {
  file: FileNode;
  selected: boolean;
  onClick: (file: FileNode) => void;
  onCreateFile: (path: string) => void;
  onCreateFolder: (path: string) => void;
  onDelete: (file: FileNode) => void;
  onDownload: (file: FileNode) => void;
}

function FileTreeNode({ file, selected, onClick, onCreateFile, onCreateFolder, onDelete, onDownload }: FileTreeNodeProps) {
  const [showActions, setShowActions] = useState(false);

  return (
    <li>
      <div
        className={cn(
          'flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors',
          'hover:bg-accent',
          selected && 'bg-primary/10 text-primary',
          file.is_dir && 'cursor-pointer'
        )}
        onClick={() => !file.is_dir && onClick(file)}
        onDoubleClick={() => file.is_dir && onClick(file)}
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
      >
        {file.is_dir ? (
          <FolderOpen className={cn('h-4 w-4 flex-shrink-0', file.expanded && 'text-primary')} />
        ) : (
          <File className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        )}
        <span className="truncate flex-1 text-sm">{file.name}</span>
        {!file.is_dir && (
          <span className="text-xs text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
            {formatSize(file.size)}
          </span>
        )}
        {showActions && !file.is_dir && (
          <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onClick(file); }} title="Open">
              <File className="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onDownload(file); }} title="Download">
              <Download className="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={(e) => { e.stopPropagation(); onDelete(file); }} title="Delete">
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        )}
        {showActions && file.is_dir && (
          <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onCreateFile(file.path); }} title="New file">
              <FilePlus className="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onCreateFolder(file.path); }} title="New folder">
              <FolderPlus className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>
    </li>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}