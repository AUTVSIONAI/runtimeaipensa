// Settings store - manages application settings with backend persistence

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { api } from '@/lib/api';
import type { UISettings, RuntimeConfig, SettingsResponse } from '@/types/runtime';

interface SettingsState {
  settings: SettingsResponse | null;
  isLoading: boolean;
  isSaving: boolean;
  lastSaved: string | null;
  error: string | null;

  // Actions
  loadSettings: () => Promise<void>;
  saveSettings: (uiSettings: Partial<UISettings>) => Promise<boolean>;
  updateSetting: <K extends keyof UISettings>(key: K, value: UISettings[K]) => void;
  resetSettings: () => Promise<void>;
  exportBackup: () => Promise<any>;
  importBackup: (data: any, overwrite?: boolean) => Promise<boolean>;
  clearCache: () => Promise<void>;
}

const DEFAULT_UI_SETTINGS: UISettings = {
  theme: 'system',
  accent_color: 'blue',
  density: 'comfortable',
  auto_scroll: true,
  compact_mode: false,
  show_module_status: true,
  animations_enabled: true,
  notifications_enabled: true,
  sound_enabled: false,
  desktop_notifications_enabled: false,
  debug_mode: false,
  performance_monitoring: true,
  event_persistence: true,
  ws_auto_reconnect: true,
  log_level: 'info',
  max_events: 10000,
  api_url: 'http://localhost:8000',
  ws_url: 'ws://localhost:8000/ws/events',
  notification_types: {
    errors: true,
    warnings: true,
    info: true,
    debug: false,
  },
};

const STORAGE_KEY = 'aipensa_ui_settings';

export const useSettingsStore = create<SettingsState>()(
  devtools(
    (set, get) => ({
      settings: null,
      isLoading: false,
      isSaving: false,
      lastSaved: null,
      error: null,

      loadSettings: async () => {
        set({ isLoading: true, error: null });
        try {
          // Try to load from backend first
          let backendSettings: SettingsResponse | null = null;
          try {
            backendSettings = await api.getSettings();
          } catch (e) {
            console.warn('Backend settings not available, using localStorage');
          }

          // Load from localStorage as fallback
          const localSettings = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
          const parsedLocal = localSettings ? JSON.parse(localSettings) : null;

          // Merge settings: backend runtime config + localStorage UI settings
          const mergedSettings: SettingsResponse = {
            settings: {
              runtime: backendSettings?.settings?.runtime || {} as RuntimeConfig,
              ui: {
                ...DEFAULT_UI_SETTINGS,
                ...parsedLocal,
                ...backendSettings?.settings?.ui,
              },
            },
          };

          set({ settings: mergedSettings, isLoading: false, lastSaved: mergedSettings.settings.ui ? new Date().toISOString() : null });
        } catch (e) {
          set({ error: e instanceof Error ? e.message : 'Failed to load settings', isLoading: false });
        }
      },

      saveSettings: async (uiSettings: Partial<UISettings>) => {
        set({ isSaving: true });
        try {
          // Save to localStorage immediately
          const currentSettings = get().settings;
          const newUISettings = { ...currentSettings?.settings?.ui, ...uiSettings } as UISettings;

          if (typeof window !== 'undefined') {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(newUISettings));
          }

          // Also try to save to backend (for server-side persistence)
          try {
            await api.updateSettings(newUISettings);
          } catch (e) {
            console.warn('Backend settings save not available:', e);
          }

          set({
            settings: { ...currentSettings!, settings: { ...currentSettings!.settings, ui: newUISettings } } as SettingsResponse,
            isSaving: false,
            lastSaved: new Date().toISOString(),
          });

          return true;
        } catch (e) {
          set({ error: e instanceof Error ? e.message : 'Failed to save settings', isSaving: false });
          return false;
        }
      },

      updateSetting: <K extends keyof UISettings>(key: K, value: UISettings[K]) => {
        const currentSettings = get().settings;
        if (currentSettings) {
          const newUISettings = { ...currentSettings.settings.ui, [key]: value } as UISettings;
          set({
            settings: {
              ...currentSettings,
              settings: { ...currentSettings.settings, ui: newUISettings },
            },
          });
        }
      },

      resetSettings: async () => {
        set({ isSaving: true });
        try {
          // Clear localStorage
          if (typeof window !== 'undefined') {
            localStorage.removeItem(STORAGE_KEY);
          }

          // Try backend reset
          try {
            await api.resetSettings();
          } catch (e) {
            console.warn('Backend reset not available:', e);
          }

          // Reset to defaults
          set({
            settings: {
              settings: {
                runtime: {} as RuntimeConfig,
                ui: DEFAULT_UI_SETTINGS,
              },
            },
            isSaving: false,
            lastSaved: new Date().toISOString(),
          });
        } catch (e) {
          set({ error: e instanceof Error ? e.message : 'Failed to reset settings', isSaving: false });
        }
      },

      exportBackup: async () => {
        try {
          return await api.exportBackup();
        } catch (e) {
          throw new Error(e instanceof Error ? e.message : 'Failed to export backup');
        }
      },

      importBackup: async (data: any, overwrite = false) => {
        try {
          await api.importBackup({ data, overwrite });
          // Reload settings after import
          await get().loadSettings();
          return true;
        } catch (e) {
          set({ error: e instanceof Error ? e.message : 'Failed to import backup' });
          return false;
        }
      },

      clearCache: async () => {
        try {
          await api.clearCache();
        } catch (e) {
          throw new Error(e instanceof Error ? e.message : 'Failed to clear cache');
        }
      },
    }),
    { name: 'SettingsStore' }
  )
);