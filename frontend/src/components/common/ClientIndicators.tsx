'use client';

import { useEffect, useState } from 'react';

export function ClientIndicators() {
  const [isClient, setIsClient] = useState(false);
  const [immediateEffectRan, setImmediateEffectRan] = useState(false);
  const [setTimeoutRan, setSetTimeoutRan] = useState(false);
  const [clientSideRan, setClientSideRan] = useState(false);

  useEffect(() => {
    setIsClient(true);
    setImmediateEffectRan(!!(window as any).__CLIENT_MOUNTED_EFFECT_RAN__);
    setSetTimeoutRan(!!(window as any).__CLIENT_TIMEOUT_RAN__);
    setClientSideRan(!!(window as any).__CLIENT_SIDE_RAN__);
  }, []);

  if (!isClient) return null;

  return (
    <>
      <div style={{ position: 'fixed', bottom: 10, right: 10, background: 'green', color: 'white', padding: '5px 10px', borderRadius: 4, fontSize: 12, zIndex: 9999 }}>
        CLIENT-SIDE ACTIVE
      </div>
      {immediateEffectRan && (
        <div style={{ position: 'fixed', bottom: 35, right: 10, background: 'blue', color: 'white', padding: '5px 10px', borderRadius: 4, fontSize: 12, zIndex: 9999 }}>
          IMMEDIATE EFFECT RAN
        </div>
      )}
      {setTimeoutRan && (
        <div style={{ position: 'fixed', bottom: 60, right: 10, background: 'purple', color: 'white', padding: '5px 10px', borderRadius: 4, fontSize: 12, zIndex: 9999 }}>
          SETTIMEOUT RAN
        </div>
      )}
      {clientSideRan && (
        <div style={{ position: 'fixed', bottom: 85, right: 10, background: 'orange', color: 'white', padding: '5px 10px', borderRadius: 4, fontSize: 12, zIndex: 9999 }}>
          BACKUP EFFECT RAN
        </div>
      )}
    </>
  );
}