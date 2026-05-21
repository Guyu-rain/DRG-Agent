import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AppLayout } from '@/components/Layout/AppLayout';
import { DRGGrouping } from '@/pages/DRGGrouping/DRGGrouping';
import { DocumentDetail } from '@/pages/DocumentSystem/DocumentDetail';
import { DocumentList } from '@/pages/DocumentSystem/DocumentList';
import { DocumentSystem } from '@/pages/DocumentSystem/DocumentSystem';
import { ExecutionLog } from '@/pages/ExecutionLog/ExecutionLog';
import { RuleManagement } from '@/pages/RuleManagement/RuleManagement';
import { Settings } from '@/pages/Settings/Settings';
import { TaskCenter } from '@/pages/TaskCenter/TaskCenter';
import { TestCase } from '@/pages/TestCase/TestCase';
import { brandColor } from '@/utils/constants';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <TaskCenter /> },
      { path: 'drg', element: <DRGGrouping /> },
      { path: 'rules', element: <RuleManagement /> },
      { path: 'docs', element: <DocumentSystem /> },
      { path: 'docs/type/:type', element: <DocumentList /> },
      { path: 'docs/detail/:id', element: <DocumentDetail /> },
      { path: 'tests', element: <TestCase /> },
      { path: 'logs', element: <ExecutionLog /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: brandColor,
          borderRadius: 6,
          fontFamily:
            'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        components: {
          Card: { borderRadiusLG: 8 },
          Button: { borderRadius: 6 },
          Table: { headerBg: '#f8fafc' },
        },
      }}
    >
      <AntApp>
        <RouterProvider router={router} />
      </AntApp>
    </ConfigProvider>
  );
}
