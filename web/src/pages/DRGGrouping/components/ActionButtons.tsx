import { FileTextOutlined, SendOutlined, ExperimentOutlined } from '@ant-design/icons';
import { Button, Space, message } from 'antd';

export function ActionButtons() {
  return (
    <Space wrap>
      <Button icon={<SendOutlined />} onClick={() => message.success('已提交复核任务')}>
        提交复核
      </Button>
      <Button icon={<FileTextOutlined />} onClick={() => message.success('已创建文档生成任务')}>
        生成文档
      </Button>
      <Button icon={<ExperimentOutlined />} onClick={() => message.success('已创建测试用例生成任务')}>
        生成测试
      </Button>
    </Space>
  );
}
