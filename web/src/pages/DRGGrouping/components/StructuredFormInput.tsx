import { Col, Form, Input, InputNumber, Row, Select } from 'antd';
import type { StructuredCaseInput } from '@/types/case';

interface StructuredFormInputProps {
  value: StructuredCaseInput;
  onChange: (value: StructuredCaseInput) => void;
}

export function StructuredFormInput({ value, onChange }: StructuredFormInputProps) {
  const [form] = Form.useForm<StructuredCaseInput>();

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={value}
      onValuesChange={(_, values) => onChange(values)}
      className="structured-form"
    >
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="患者编号" name="patientId">
            <Input placeholder="P001" />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="年龄" name="age">
            <InputNumber min={0} max={120} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="性别" name="gender">
            <Select options={['男', '女', '未知'].map((item) => ({ value: item, label: item }))} />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col span={10}>
          <Form.Item label="主诊断编码" name={['primaryDiagnosis', 'code']}>
            <Input placeholder="A01.002+G01*" />
          </Form.Item>
        </Col>
        <Col span={14}>
          <Form.Item label="主诊断名称" name={['primaryDiagnosis', 'name']}>
            <Input placeholder="伤寒性脑膜炎" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col span={10}>
          <Form.Item label="次要诊断编码" name={['secondaryDiagnoses', 0, 'code']}>
            <Input placeholder="J96.0" />
          </Form.Item>
        </Col>
        <Col span={14}>
          <Form.Item label="次要诊断名称" name={['secondaryDiagnoses', 0, 'name']}>
            <Input placeholder="急性呼吸衰竭" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col span={10}>
          <Form.Item label="主要手术编码" name={['primaryProcedure', 'code']}>
            <Input placeholder="38.1000x002" />
          </Form.Item>
        </Col>
        <Col span={10}>
          <Form.Item label="主要手术名称" name={['primaryProcedure', 'name']}>
            <Input placeholder="动脉内膜剥脱术" />
          </Form.Item>
        </Col>
        <Col span={4}>
          <Form.Item label="级别" name={['primaryProcedure', 'surgeryLevel']}>
            <InputNumber min={1} max={4} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );
}
