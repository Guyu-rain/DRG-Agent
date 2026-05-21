import { BellOutlined, MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { Button, Layout, Menu, Space, Tooltip, Typography } from 'antd';
import { useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { routeItems } from '@/utils/constants';
import './AppLayout.css';

const { Header, Sider, Content, Footer } = Layout;

function selectedKey(pathname: string) {
  if (pathname.startsWith('/drg')) return '/drg';
  if (pathname.startsWith('/rules')) return '/rules';
  if (pathname.startsWith('/docs')) return '/docs';
  if (pathname.startsWith('/tests')) return '/tests';
  if (pathname.startsWith('/logs')) return '/logs';
  if (pathname.startsWith('/settings')) return '/settings';
  return '/';
}

export function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = useMemo(
    () =>
      routeItems.map((item) => {
        const Icon = item.icon;
        return {
          key: item.key,
          icon: <Icon />,
          label: item.label,
        };
      }),
    [],
  );

  return (
    <Layout className="app-shell">
      <Sider collapsible collapsed={collapsed} trigger={null} className="app-sider" width={224}>
        <div className="app-logo">
          <span className="logo-mark">D</span>
          {!collapsed ? <span>DRG-Agent</span> : null}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey(location.pathname)]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space>
            <Tooltip title={collapsed ? '展开导航' : '收起导航'}>
              <Button
                type="text"
                aria-label={collapsed ? '展开导航' : '收起导航'}
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed((value) => !value)}
              />
            </Tooltip>
            <Typography.Text strong>医保 DRG 入组智能体系统</Typography.Text>
          </Space>
          <Tooltip title="通知">
            <Button shape="circle" aria-label="通知" icon={<BellOutlined />} />
          </Tooltip>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
        <Footer className="app-footer">DRG-Agent © 2026</Footer>
      </Layout>
    </Layout>
  );
}
