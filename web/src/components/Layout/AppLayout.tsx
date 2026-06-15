import { BellOutlined, MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { Avatar, Badge, Button, Layout, Menu, Tooltip } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Logo } from '@/components/Common/Logo';
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

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(id);
  }, []);
  return now;
}

function formatClock(d: Date) {
  const pad = (n: number) => String(n).padStart(2, '0');
  const weekday = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()];
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} 周${weekday} · ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const now = useClock();

  useEffect(() => {
    const media = window.matchMedia('(max-width: 720px)');
    const syncCollapsed = () => {
      if (media.matches) setCollapsed(true);
    };
    syncCollapsed();
    media.addEventListener('change', syncCollapsed);
    return () => media.removeEventListener('change', syncCollapsed);
  }, []);

  const activeKey = selectedKey(location.pathname);
  const activeItem = routeItems.find((r) => r.key === activeKey) ?? routeItems[0];
  const isDocumentWorkspace = location.pathname === '/docs';

  const menuItems = useMemo(
    () =>
      routeItems.map((item, idx) => {
        const Icon = item.icon;
        return {
          key: item.key,
          icon: <Icon />,
          label: (
            <span className="app-nav-row">
              <span className="app-nav-row__num">{String(idx + 1).padStart(2, '0')}</span>
              <span className="app-nav-row__label">{item.label}</span>
            </span>
          ),
        };
      }),
    [],
  );

  return (
    <Layout className="app-shell">
      <Sider
        collapsible
        collapsed={collapsed}
        trigger={null}
        className="app-sider"
        width={248}
        collapsedWidth={72}
      >
        <div className="app-brand">
          <Logo size={28} />
          {!collapsed && (
            <div className="app-brand__text">
              <span className="app-brand__name">DRG-Agent</span>
              <span className="app-brand__sub">
                <em>Clinical grouping intelligence</em>
              </span>
            </div>
          )}
        </div>

        {!collapsed && (
          <div className="app-sider__rubric">
            <span className="eyebrow">章节 · Navigation</span>
          </div>
        )}

        <Menu
          mode="inline"
          selectedKeys={[activeKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className={collapsed ? 'app-menu app-menu--collapsed' : 'app-menu'}
        />

        {!collapsed && (
          <div className="app-sider__foot">
            <div className="app-sider__foot-rule" />
            <p className="app-sider__foot-text">
              <span className="eyebrow">Issue №24‑05</span>
              <span>
                医保 DRG 入组 ·
                <br />
                确定性引擎 + LLM 解释 + 文档生成
              </span>
            </p>
          </div>
        )}
      </Sider>

      <Layout>
        <Header className="app-header">
          <div className="app-header__left">
            <Tooltip title={collapsed ? '展开导航' : '收起导航'}>
              <Button
                type="text"
                aria-label={collapsed ? '展开导航' : '收起导航'}
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed((value) => !value)}
              />
            </Tooltip>
            <nav className="app-crumbs" aria-label="breadcrumb">
              <span className="app-crumbs__root">DRG-AGENT</span>
              <span className="app-crumbs__sep">／</span>
              <span className="app-crumbs__leaf">{activeItem.label}</span>
            </nav>
          </div>

          <div className="app-header__right">
            <span className="app-pill app-pill--env">
              <span className="app-pill__dot" />
              <span>本地 · v0.3</span>
            </span>
            <span className="app-clock mono">{formatClock(now)}</span>
            <Tooltip title="系统通知">
              <Badge dot color="#c08552" offset={[-4, 4]}>
                <Button type="text" shape="circle" aria-label="通知" icon={<BellOutlined />} />
              </Badge>
            </Tooltip>
            <Avatar className="app-avatar" size={32}>
              医
            </Avatar>
          </div>
        </Header>

        <Content
          className={isDocumentWorkspace ? 'app-content app-content--workspace' : 'app-content'}
        >
          <Outlet />
        </Content>

        <Footer className="app-footer">
          <span className="mono">DRG-Agent · clinical grouping intelligence</span>
          <span className="app-footer__rule" />
          <span>编修于 {now.getFullYear()} 年 · 内部测试版</span>
        </Footer>
      </Layout>
    </Layout>
  );
}
