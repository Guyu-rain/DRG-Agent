import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './components/Common/ErrorBoundary';
import './index.css';

/**
 * Phase 3 起默认连接真实后端 API（通过 Vite 代理转发到 :8000）。
 * 仅当显式设置 VITE_ENABLE_MSW=true 时才启用 MSW Mock，用于离线前端开发。
 */
async function enableMocking() {
  if (import.meta.env.VITE_ENABLE_MSW !== 'true') {
    return;
  }
  const { worker } = await import('./mocks/browser');
  return worker.start({ onUnhandledRequest: 'bypass' });
}

void enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>,
  );
});
