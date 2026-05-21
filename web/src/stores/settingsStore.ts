import { create } from 'zustand';
import { systemApi } from '@/services';
import type { SystemConfig } from '@/types/task';

interface SettingsState {
  config: SystemConfig | null;
  health: Record<string, unknown> | null;
  fetchConfig: () => Promise<void>;
  saveConfig: (config: SystemConfig) => Promise<void>;
  fetchHealth: () => Promise<void>;
  initDemo: () => Promise<string>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  config: null,
  health: null,
  fetchConfig: async () => {
    const response = await systemApi.config();
    set({ config: response.data });
  },
  saveConfig: async (config) => {
    const response = await systemApi.updateConfig(config);
    set({ config: response.data });
  },
  fetchHealth: async () => {
    const response = await systemApi.health();
    set({ health: response.data });
  },
  initDemo: async () => {
    const response = await systemApi.initDemo();
    await Promise.all([useSettingsStore.getState().fetchConfig(), useSettingsStore.getState().fetchHealth()]);
    return response.data.message;
  },
}));
