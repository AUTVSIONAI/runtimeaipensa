'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    router.push('/dashboard');
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">AIPENSA Runtime Dev UI</h1>
        <p className="text-gray-500 mt-4">Redirecting to dashboard...</p>
      </div>
    </div>
  );
}