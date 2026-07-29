// UI store - manages global UI state like sidebar, panels, modals, theme

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export type RightPanelTab = 'workflow' | 'timeline' | 'debug' | 'browser' | 'settings' | 'plugins' | 'workspace';

interface UIState {
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  rightPanelTab: RightPanelTab;
  theme: 'light' | 'dark' | 'system';
  activeModal: string | null;
  notifications: Array<{ id: string; type: 'info' | 'success' | 'warning' | 'error'; message: string }>;

  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleRightPanel: () => void;
  setRightPanelOpen: (open: boolean) => void;
  setRightPanelTab: (tab: RightPanelTab) => void;
  setTheme: (theme: UIState['theme']) => void;
  openModal: (id: string) => void;
  closeModal: () => void;
  addNotification: (notification: Omit<UIState['notifications'][0], 'id'>) => void;
  removeNotification: (id: string) => void;
}

export const useUIStore = create<UIState>()(
  devtools(
    (set) => ({
      sidebarOpen: true,
      rightPanelOpen: false,
      rightPanelTab: 'workflow',
      theme: 'system',
      activeModal: null,
      notifications: [],

      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      toggleRightPanel: () => set((state) => ({ rightPanelOpen: !state.rightPanelOpen })),
      setRightPanelOpen: (rightPanelOpen) => set({ rightPanelOpen }),
      setRightPanelTab: (rightPanelTab) => set({ rightPanelTab }),
      setTheme: (theme) => set({ theme }),
      openModal: (activeModal) => set({ activeModal }),
      closeModal: () => set({ activeModal: null }),
      addNotification: (notification) =>
        set((state) => ({
          notifications: [...state.notifications, { ...notification, id: crypto.randomUUID() }],
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
    }),
    { name: 'UIStore' }
  )
);