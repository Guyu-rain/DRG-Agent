import { apiBaseUrl, apiUrl } from '@/services/api';

export function triggerDownload(path: string) {
  const link = document.createElement('a');
  link.href = /^https?:\/\//.test(path) || path.startsWith(apiBaseUrl) ? path : apiUrl(path);
  link.download = '';
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
