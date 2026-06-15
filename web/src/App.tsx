import { ConfigProvider, App as AntApp, theme as antdTheme } from 'antd';
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
      { path: 'docs/all', element: <DocumentList /> },
      { path: 'docs/type/:type', element: <DocumentList /> },
      { path: 'docs/detail/:id', element: <DocumentDetail /> },
      { path: 'tests', element: <TestCase /> },
      { path: 'logs', element: <ExecutionLog /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);

const sansStack =
  '"Geist", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, -apple-system, sans-serif';

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: brandColor,
          colorInfo: '#2b3f6b',
          colorSuccess: '#4a6f60',
          colorWarning: '#c08552',
          colorError: '#b6553a',

          colorText: '#1c1e22',
          colorTextSecondary: '#4a4d54',
          colorTextTertiary: '#8a8c92',
          colorTextQuaternary: '#b3b5bb',
          colorBgBase: '#f7f4ec',
          colorBgContainer: '#ffffff',
          colorBgElevated: '#ffffff',
          colorBgLayout: 'transparent',

          colorBorder: '#e4ddc9',
          colorBorderSecondary: '#ede6d3',
          colorSplit: '#ede6d3',

          borderRadius: 6,
          borderRadiusSM: 4,
          borderRadiusLG: 6,
          borderRadiusXS: 2,

          fontFamily: sansStack,
          fontSize: 13.5,
          lineHeight: 1.6,
          controlHeight: 36,

          wireframe: false,
          motionDurationMid: '0.24s',
          motionEaseOut: 'cubic-bezier(0.22, 0.61, 0.36, 1)',
        },
        components: {
          Layout: {
            headerBg: 'transparent',
            siderBg: 'transparent',
            bodyBg: 'transparent',
            footerBg: 'transparent',
            headerHeight: 72,
            headerPadding: '0 32px',
          },
          Card: {
            borderRadiusLG: 6,
            paddingLG: 24,
            colorBorderSecondary: '#e4ddc9',
            boxShadowTertiary: '0 1px 0 rgba(28,30,34,0.03), 0 18px 36px -24px rgba(60,52,28,0.22)',
          },
          Button: {
            borderRadius: 4,
            controlHeight: 36,
            fontWeight: 500,
            primaryShadow: '0 1px 0 rgba(74,111,96,0.18)',
            defaultBorderColor: '#c9bf9f',
          },
          Menu: {
            itemBg: 'transparent',
            itemSelectedBg: '#ebefe7',
            itemSelectedColor: '#4a6f60',
            itemHoverBg: '#efeadc',
            itemColor: '#2f323a',
            itemBorderRadius: 4,
            itemHeight: 38,
            iconSize: 15,
            collapsedIconSize: 17,
            activeBarWidth: 0,
          },
          Table: {
            headerBg: 'transparent',
            headerSplitColor: 'transparent',
            headerColor: '#8a8c92',
            rowHoverBg: '#fbf9f3',
            borderColor: '#ede6d3',
            cellPaddingBlock: 16,
          },
          Tag: {
            borderRadiusSM: 999,
            defaultBg: '#efeadc',
            defaultColor: '#4a4d54',
          },
          Input: {
            colorBorder: '#c9bf9f',
            activeBorderColor: '#6b8e7f',
            hoverBorderColor: '#6b8e7f',
            activeShadow: '0 0 0 3px #ebefe7',
          },
          Select: {
            colorBorder: '#c9bf9f',
          },
          Statistic: {
            titleFontSize: 11,
            contentFontSize: 30,
          },
          Drawer: {
            colorBgElevated: '#fbf9f3',
            paddingLG: 24,
          },
          Tooltip: {
            colorBgSpotlight: '#1c1e22',
            borderRadius: 4,
          },
          Badge: {
            statusSize: 8,
          },
          Tabs: {
            inkBarColor: '#6b8e7f',
            itemSelectedColor: '#1c1e22',
            itemHoverColor: '#4a6f60',
            titleFontSize: 14,
            horizontalItemPadding: '12px 4px',
          },
          Form: {
            labelColor: '#4a4d54',
            verticalLabelPadding: '0 0 6px',
          },
        },
      }}
    >
      <AntApp>
        <RouterProvider router={router} />
      </AntApp>
    </ConfigProvider>
  );
}
