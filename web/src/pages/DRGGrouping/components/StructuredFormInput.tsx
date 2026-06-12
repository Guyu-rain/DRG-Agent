import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Col, Form, Input, InputNumber, Row, Select, Space } from 'antd';
import { useEffect } from 'react';
import type { StructuredCaseInput } from '@/types/case';

interface StructuredFormInputProps {
  value: StructuredCaseInput;
  onChange: (value: StructuredCaseInput) => void;
}

export function StructuredFormInput({ value, onChange }: StructuredFormInputProps) {
  const [form] = Form.useForm<StructuredCaseInput>();

  useEffect(() => {
    form.setFieldsValue(value);
  }, [form, value]);

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={value}
      onValuesChange={(_, values) => onChange(values)}
      className="structured-form"
    >
      <Row gutter={12}>
        <Col xs={24} md={12}>
          <Form.Item label="患者编号" name="patientId">
            <Input placeholder="P001" />
          </Form.Item>
        </Col>
        <Col xs={12} md={6}>
          <Form.Item label="年龄" name="age">
            <InputNumber min={0} max={120} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col xs={12} md={6}>
          <Form.Item label="性别" name="gender">
            <Select options={['男', '女', '未知'].map((item) => ({ value: item, label: item }))} />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col xs={24} md={10}>
          <Form.Item label="主诊断编码" name={['primaryDiagnosis', 'code']}>
            <Input placeholder="A01.002+G01*" />
          </Form.Item>
        </Col>
        <Col xs={24} md={14}>
          <Form.Item label="主诊断名称" name={['primaryDiagnosis', 'name']}>
            <Input placeholder="伤寒性脑膜炎" />
          </Form.Item>
        </Col>
      </Row>
      <Form.List name="secondaryDiagnoses">
        {(fields, { add, remove }) => (
          <Space direction="vertical" style={{ width: '100%' }} size={0}>
            {fields.map((field, index) => (
              <Row gutter={12} key={field.key} align="middle">
                <Col xs={24} md={9}>
                  <Form.Item label={`次要诊断 ${index + 1} 编码`} name={[field.name, 'code']}>
                    <Input placeholder="J96.0" />
                  </Form.Item>
                </Col>
                <Col xs={20} md={13}>
                  <Form.Item label={`次要诊断 ${index + 1} 名称`} name={[field.name, 'name']}>
                    <Input placeholder="急性呼吸衰竭" />
                  </Form.Item>
                </Col>
                <Col xs={4} md={2}>
                  <Button
                    type="text"
                    danger
                    aria-label={`删除次要诊断 ${index + 1}`}
                    icon={<MinusCircleOutlined />}
                    onClick={() => remove(field.name)}
                  />
                </Col>
              </Row>
            ))}
            <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ code: '', name: '' })}>
              添加次要诊断
            </Button>
          </Space>
        )}
      </Form.List>
      <Row gutter={12}>
        <Col xs={24} md={10}>
          <Form.Item label="主要手术编码" name={['primaryProcedure', 'code']}>
            <Input placeholder="38.1000x002" />
          </Form.Item>
        </Col>
        <Col xs={20} md={10}>
          <Form.Item label="主要手术名称" name={['primaryProcedure', 'name']}>
            <Input placeholder="动脉内膜剥脱术" />
          </Form.Item>
        </Col>
        <Col xs={4} md={4}>
          <Form.Item label="级别" name={['primaryProcedure', 'surgeryLevel']}>
            <InputNumber min={1} max={4} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
      <Form.List name="otherProcedures">
        {(fields, { add, remove }) => (
          <Space direction="vertical" style={{ width: '100%' }} size={0}>
            {fields.map((field, index) => (
              <Row gutter={12} key={field.key} align="middle">
                <Col xs={24} md={9}>
                  <Form.Item label={`其他手术 ${index + 1} 编码`} name={[field.name, 'code']}>
                    <Input placeholder="其他手术编码" />
                  </Form.Item>
                </Col>
                <Col xs={20} md={13}>
                  <Form.Item label={`其他手术 ${index + 1} 名称`} name={[field.name, 'name']}>
                    <Input placeholder="其他手术名称" />
                  </Form.Item>
                </Col>
                <Col xs={4} md={2}>
                  <Button
                    type="text"
                    danger
                    aria-label={`删除其他手术 ${index + 1}`}
                    icon={<MinusCircleOutlined />}
                    onClick={() => remove(field.name)}
                  />
                </Col>
              </Row>
            ))}
            <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ code: '', name: '' })}>
              添加其他手术
            </Button>
          </Space>
        )}
      </Form.List>
    </Form>
  );
}
