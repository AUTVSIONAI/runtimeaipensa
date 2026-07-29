'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Globe, Loader2, RefreshCw, ExternalLink, Maximize2, Minimize2, WifiOff, FolderOpen, Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { cn } from '@/lib/utils';

const PREVIEW_URL = process.env.NEXT_PUBLIC_PREVIEW_URL || 'http://localhost:8081';

function PreviewPanel() {
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [iframeError, setIframeError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedSite, setSelectedSite] = useState<string>('');
  const [availableSites, setAvailableSites] = useState<string[]>(['']); // '' = root
  const [searchQuery, setSearchQuery] = useState('');
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const checkPreviewConnection = async () => {
    try {
      const res = await fetch(`${PREVIEW_URL}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      });
      return res.ok;
    } catch {
      return false;
    }
  };

  const fetchAvailableSites = async () => {
    try {
      // Try to fetch the workspace/sites directory listing
      const res = await fetch(`${PREVIEW_URL}/sites/`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const html = await res.text();
        // Parse HTML for site directories
        // Look for links like <a href="/sites/site-name/"> or similar patterns
        const siteMatches = html.match(/href="\/sites\/([^\/"]+)\//g);
        if (siteMatches) {
          const sites = Array.from(new Set(siteMatches.map(m => m.replace('href="/sites/', '').replace('/', ''))));
          setAvailableSites(['', ...sites]);
        } else {
          // Fallback: check for any directory-like links
          const dirMatches = html.match(/href="\/sites\/([^\/"]+)\//g);
          if (dirMatches) {
            const sites = Array.from(new Set(dirMatches.map(m => m.replace('href="/sites/', '').replace('/', ''))));
            setAvailableSites(['', ...sites]);
          }
        }
      }
    } catch {
      // Ignore, keep default
    }
  };

  const handleRetry = async () => {
    setIframeError(false);
    setIframeLoaded(false);
    const connected = await checkPreviewConnection();
    if (!connected) {
      alert('Preview server is not running. Please start it with: npm run preview');
    }
    // Force iframe reload
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  useEffect(() => {
    let mounted = true;
    checkPreviewConnection().then(connected => {
      if (mounted && !connected) {
        setIframeError(true);
      }
      if (mounted) {
        fetchAvailableSites();
      }
    });
    return () => { mounted = false; };
  }, []);

  const getIframeSrc = () => {
    if (selectedSite) {
      return `${PREVIEW_URL}/sites/${selectedSite}/`;
    }
    return PREVIEW_URL;
  };

  return (
    <div className="h-full flex flex-col bg-card border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-background/50">
        <div className="flex items-center gap-3">
          <Globe className="h-5 w-5 text-blue-500" />
          <div>
            <h3 className="font-medium">Live Preview</h3>
            <p className="text-xs text-muted-foreground">
              Workspace preview with hot reload
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Site Selector */}
          <div className="relative hidden md:block">
            <Select value={selectedSite} onValueChange={setSelectedSite}>
              <SelectTrigger className="h-8 text-xs w-[200px]">
                <SelectValue placeholder="Select site..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">📁 Workspace Root</SelectItem>
                {availableSites.filter(s => s).map(site => (
                  <SelectItem key={site} value={site}>
                    🌐 {site}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRetry}
            disabled={!iframeError && iframeLoaded}
            className="gap-1"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Retry</span>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.open(getIframeSrc(), '_blank')}
            title="Open in new tab"
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Status Indicator */}
      <div className={cn(
        'px-4 py-2 text-xs flex items-center gap-2 border-b border-border',
        iframeError ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400' : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
      )}>
        {iframeError ? (
          <>
            <WifiOff className="h-3.5 w-3.5" />
            <span>Preview server disconnected</span>
            <span className="flex-1" />
            <span className="font-mono">{PREVIEW_URL}</span>
          </>
        ) : iframeLoaded ? (
          <>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span>Connected and loaded</span>
            </span>
            <span className="flex-1" />
            <span className="font-mono">{getIframeSrc()}</span>
          </>
        ) : (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Connecting to preview server...</span>
            <span className="flex-1" />
            <span className="font-mono">{PREVIEW_URL}</span>
          </>
        )}
      </div>

      {/* Iframe Content */}
      <div className="flex-1 relative overflow-hidden">
        <iframe
          ref={iframeRef}
          src={getIframeSrc()}
          className="absolute inset-0 w-full h-full border-none"
          onLoad={() => {
            setIframeLoaded(true);
            setIframeError(false);
          }}
          onError={() => setIframeError(true)}
          title="AIPENSA Preview"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads"
        />

        {/* Error Overlay */}
        {iframeError && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute inset-0 flex items-center justify-center p-8 bg-card border border-border"
          >
            <div className="text-center max-w-md">
              <WifiOff className="h-16 w-16 text-muted-foreground/50 mx-auto mb-4" />
              <h4 className="text-lg font-medium mb-2">Preview Server Not Running</h4>
              <p className="text-muted-foreground mb-6">
                The preview server is not accessible at <code className="bg-muted px-1.5 py-0.5 rounded text-sm">{PREVIEW_URL}</code>
              </p>
              <div className="space-y-3 p-4 bg-muted rounded-lg text-left text-sm">
                <p className="font-medium">To start the preview server:</p>
                <code className="bg-background/50 px-3 py-1.5 rounded font-mono block">
                  npm run preview
                </code>
                <p className="text-muted-foreground text-xs">
                  Or run directly: <code>python preview_server.py</code>
                </p>
              </div>
              <Button onClick={handleRetry} className="w-full mt-4 gap-2">
                <RefreshCw className="h-4 w-4" />
                Retry Connection
              </Button>
            </div>
          </motion.div>
        )}

        {/* Loading Overlay */}
        {!iframeLoaded && !iframeError && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 flex items-center justify-center bg-card/80 backdrop-blur-sm"
          >
            <div className="text-center">
              <Loader2 className="h-10 w-10 text-blue-500 animate-spin mx-auto mb-4" />
              <p className="text-muted-foreground">Loading preview...</p>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default function PreviewPage() {
  return (
    <div className="h-full">
      <PreviewPanel />
    </div>
  );
}