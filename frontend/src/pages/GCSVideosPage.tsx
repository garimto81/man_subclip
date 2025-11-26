import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Typography,
  Card,
  Row,
  Col,
  Button,
  Empty,
  Spin,
  Alert,
  message,
  Space,
  Modal,
  Form,
  InputNumber,
  Progress,
} from 'antd'
import {
  CloudDownloadOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  ScissorOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { apiClient } from '@/api/client'
import type { GCSVideo, GCSClipResponse } from '@/types'

const { Title, Text } = Typography

function GCSVideosPage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const [videos, setVideos] = useState<GCSVideo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [importing, setImporting] = useState<string | null>(null)

  // Clip creation state
  const [clipModalVisible, setClipModalVisible] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState<GCSVideo | null>(null)
  const [creatingClip, setCreatingClip] = useState(false)
  const [clipResult, setClipResult] = useState<GCSClipResponse | null>(null)

  const loadGCSVideos = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.listGCSVideos()
      setVideos(response.videos)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load GCS videos')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGCSVideos()
  }, [])

  const handleImport = async (gcsPath: string, filename: string) => {
    setImporting(gcsPath)

    try {
      const video = await apiClient.importFromGCS(gcsPath)

      message.success({
        content: `"${filename}" import started! Proxy rendering in progress...`,
        duration: 5,
      })

      // Navigate to video library after import
      setTimeout(() => {
        navigate('/')
      }, 1500)
    } catch (err: any) {
      message.error(
        err.response?.data?.detail || err.message || `Failed to import "${filename}"`
      )
    } finally {
      setImporting(null)
    }
  }

  // Open clip creation modal
  const handleOpenClipModal = (video: GCSVideo) => {
    setSelectedVideo(video)
    setClipResult(null)
    form.resetFields()
    form.setFieldsValue({
      start_sec: 0,
      end_sec: 10,
      padding_sec: 0,
    })
    setClipModalVisible(true)
  }

  // Create clip from GCS (streaming)
  const handleCreateClip = async (values: { start_sec: number; end_sec: number; padding_sec: number }) => {
    if (!selectedVideo) return

    setCreatingClip(true)
    setClipResult(null)

    try {
      const result = await apiClient.createClipFromGCS({
        gcs_path: selectedVideo.gcs_path,
        start_sec: values.start_sec,
        end_sec: values.end_sec,
        padding_sec: values.padding_sec,
      })

      setClipResult(result)
      message.success(`Clip created! Size: ${result.file_size_mb}MB, Duration: ${result.duration_sec}s`)
    } catch (err: any) {
      message.error(
        err.response?.data?.detail || err.message || 'Failed to create clip'
      )
    } finally {
      setCreatingClip(false)
    }
  }

  // Download the created clip
  const handleDownloadClip = () => {
    if (!clipResult) return

    const downloadUrl = apiClient.getClipDirectDownloadUrl(clipResult.clip_id)
    window.open(downloadUrl, '_blank')
  }

  // Close modal
  const handleCloseModal = () => {
    setClipModalVisible(false)
    setSelectedVideo(null)
    setClipResult(null)
    form.resetFields()
  }

  return (
    <div>
      <Space
        style={{
          width: '100%',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}
      >
        <div>
          <Title level={2} style={{ margin: 0 }}>
            GCS Videos
          </Title>
          <Text type="secondary">
            Import videos from Google Cloud Storage bucket
          </Text>
        </div>

        <Button
          icon={<ReloadOutlined />}
          onClick={loadGCSVideos}
          loading={loading}
        >
          Refresh
        </Button>
      </Space>

      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 24 }}
        />
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">Loading GCS videos...</Text>
          </div>
        </div>
      ) : videos.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No videos found in GCS bucket"
        >
          <Button type="primary" icon={<ReloadOutlined />} onClick={loadGCSVideos}>
            Refresh
          </Button>
        </Empty>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {videos.map((video) => (
              <Col xs={24} sm={12} md={8} lg={6} key={video.gcs_path}>
                <Card
                  hoverable
                  cover={
                    <div
                      style={{
                        height: 200,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <PlayCircleOutlined
                        style={{
                          fontSize: 64,
                          color: 'white',
                          opacity: 0.8,
                        }}
                      />
                    </div>
                  }
                  actions={[
                    <Button
                      type="default"
                      icon={<ScissorOutlined />}
                      onClick={() => handleOpenClipModal(video)}
                      disabled={importing !== null}
                      key="clip"
                    >
                      Create Clip
                    </Button>,
                    <Button
                      type="primary"
                      icon={<CloudDownloadOutlined />}
                      onClick={() => handleImport(video.gcs_path, video.filename)}
                      loading={importing === video.gcs_path}
                      disabled={importing !== null && importing !== video.gcs_path}
                      key="import"
                    >
                      Import
                    </Button>,
                  ]}
                >
                  <Card.Meta
                    title={
                      <div
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                        title={video.filename}
                      >
                        {video.filename}
                      </div>
                    }
                    description={
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {video.bucket}
                        </Text>
                        <br />
                        <Text
                          type="secondary"
                          style={{
                            fontSize: 11,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            display: 'block',
                          }}
                          title={video.gcs_path}
                        >
                          {video.gcs_path}
                        </Text>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>

          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <Text type="secondary">
              Total: {videos.length} video{videos.length !== 1 ? 's' : ''}
            </Text>
          </div>
        </>
      )}

      {/* Clip Creation Modal */}
      <Modal
        title={
          <Space>
            <ScissorOutlined />
            <span>Create Clip from GCS</span>
          </Space>
        }
        open={clipModalVisible}
        onCancel={handleCloseModal}
        footer={null}
        width={500}
      >
        {selectedVideo && (
          <div>
            <Alert
              message={
                <div>
                  <strong>Selected Video:</strong> {selectedVideo.filename}
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {selectedVideo.gcs_path}
                  </Text>
                </div>
              }
              type="info"
              style={{ marginBottom: 16 }}
            />

            <Alert
              message="GCS Streaming"
              description="This extracts clip directly from GCS without downloading the full video. Fast and efficient!"
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form
              form={form}
              layout="vertical"
              onFinish={handleCreateClip}
              initialValues={{
                start_sec: 0,
                end_sec: 10,
                padding_sec: 0,
              }}
            >
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="start_sec"
                    label="Start (sec)"
                    rules={[{ required: true, message: 'Required' }]}
                  >
                    <InputNumber
                      min={0}
                      step={0.1}
                      style={{ width: '100%' }}
                      placeholder="0"
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="end_sec"
                    label="End (sec)"
                    rules={[{ required: true, message: 'Required' }]}
                  >
                    <InputNumber
                      min={0}
                      step={0.1}
                      style={{ width: '100%' }}
                      placeholder="10"
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="padding_sec"
                    label="Padding (sec)"
                  >
                    <InputNumber
                      min={0}
                      step={0.5}
                      style={{ width: '100%' }}
                      placeholder="0"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={creatingClip}
                  icon={<ScissorOutlined />}
                  block
                  size="large"
                >
                  {creatingClip ? 'Creating Clip...' : 'Create Clip'}
                </Button>
              </Form.Item>
            </Form>

            {creatingClip && (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Spin />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    Extracting clip from GCS (streaming)...
                  </Text>
                </div>
              </div>
            )}

            {clipResult && (
              <Alert
                message="Clip Created Successfully!"
                description={
                  <div>
                    <p><strong>Duration:</strong> {clipResult.duration_sec.toFixed(1)}s</p>
                    <p><strong>File Size:</strong> {clipResult.file_size_mb.toFixed(2)} MB</p>
                    <p><strong>Method:</strong> {clipResult.method}</p>
                    <Button
                      type="primary"
                      icon={<DownloadOutlined />}
                      onClick={handleDownloadClip}
                      style={{ marginTop: 8 }}
                      size="large"
                      block
                    >
                      Download Clip
                    </Button>
                  </div>
                }
                type="success"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default GCSVideosPage
