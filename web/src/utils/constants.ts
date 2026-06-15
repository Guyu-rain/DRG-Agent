import {
  ApartmentOutlined,
  AuditOutlined,
  DashboardOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SettingOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import type { DocType, DocumentStatus } from '@/types/document';
import type { ScenarioType, TestPriority } from '@/types/testcase';

/** Sage — Clinical Editorial primary accent. See web/src/index.css :root --sage. */
export const brandColor = '#6b8e7f';

export const routeItems = [
  { key: '/', label: '任务中心', icon: DashboardOutlined },
  { key: '/drg', label: 'DRG 入组', icon: ApartmentOutlined },
  { key: '/rules', label: '规则管理', icon: AuditOutlined },
  { key: '/docs', label: '文档系统', icon: FileTextOutlined },
  { key: '/tests', label: '测试用例', icon: ExperimentOutlined },
  { key: '/logs', label: '执行日志', icon: HistoryOutlined },
  { key: '/settings', label: '系统配置', icon: SettingOutlined },
];

export const docTypeLabels: Record<DocType, string> = {
  requirements: '需求分析',
  design: '概要设计',
  testing: '测试文档',
  meeting_minutes: '会议纪要',
  management: '项目管理',
  configuration: '配置管理',
  general: '通用文档',
};

export const docStatusLabels: Record<DocumentStatus, string> = {
  draft: '草稿',
  review: '待审核',
  submitted: '已提交',
  archived: '已归档',
};

export const scenarioLabels: Record<ScenarioType, string> = {
  normal: '正常',
  boundary: '边界',
  abnormal: '异常',
};

export const priorityLabels: Record<TestPriority, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

export const demoCaseText =
  '主诊断：A01.002+G01* 伤寒性脑膜炎\n次要诊断：J96.0 急性呼吸衰竭\n主要手术：38.1000x002 动脉内膜剥脱术';
