import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Typography,
  Card,
  Row,
  Col,
  Button,
  Space,
  Descriptions,
  Tag,
  message,
  Spin,
  Alert,
  InputNumber,
  Form,
} from 'antd'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  ScissorOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { apiClient } from '@/api/client'
import type { Video, ClipCreateRequest } from '@/types'

const { Title, Text } = Typography

function VideoPlayerPage() {
  const { videoId } = useParams<{ videoId: string }>()
  const navigate = useNavigate()

  const [video, setVideo] = useState<Video | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [extracting, setExtracting] = useState(false)

  // Clip extraction form
  const [form] = Form.useForm()
  const [startTime, setStartTime] = useState(0)
  const [endTime, setEndTime] = useState(10)
  const [padding, setPadding] = useState(0)

  const loadVideo = async () => {
    if (!videoId) return

    setLoading(true)
    setError(null)

    try {
      const videoData = await apiClient.getVideo(videoId)
      setVideo(videoData)

      // Set default end time to video duration
      if (videoData.duration_sec) {
        setEndTime(Math.min(10, videoData.duration_sec))
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load video')
    } finally {
      setLoading(false)
    }
  }

  const handleStartProxy = async () => {
    if (!videoId) return

    try {
      await apiClient.startProxyRendering(videoId)
      message.success('Proxy rendering started')

      // Reload video status
      setTimeout(() => loadVideo(), 1000)
    } catch (err: any) {
      message.error(
        `Failed to start proxy: ${err.response?.data?.detail || err.message}`
      )
    }
  }

  const handleExtractClip = async () => {
    if (!videoId || !video) return

    // Validate times
    if (startTime >= endTime) {
      message.error('End time must be greater than start time')
      return
    }

    if (video.duration_sec && endTime > video.duration_sec) {
      message.error('End time cannot exceed video duration')
      return
    }

    setExtracting(true)

    try {
      const request: ClipCreateRequest = {
        video_id: videoId,
        start_sec: startTime,
        end_sec: endTime,
        padding_sec: padding,
      }

      const clip = await apiClient.createClip(request)

      message.success(`Clip extracted successfully: ${clip.clip_id}`)
      navigate('/clips')
    } catch (err: any) {
      message.error(
        `Failed to extract clip: ${err.response?.data?.detail || err.message}`
      )
    } finally {
      setExtracting(false)
    }
  }

  useEffect(() => {
    loadVideo()
  }, [videoId])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Spin size="large" tip="Loading video..." />
      </div>
    )
  }

  if (error || !video) {
    return (
      <div>
        <Alert
          message="Error Loading Video"
          description={error || 'Video not found'}
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          Back to Library
        </Button>
      </div>
    )
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getProxyStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'processing':
        return 'processing'
      case 'failed':
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/')}
        style={{ marginBottom: 16 }}
      >
        Back to Library
      </Button>

      <Title level={2}>{video.filename}</Title>

      <Row gutter={[16, 16]}>
        {/* Video Player / Placeholder */}
        <Col xs={24} lg={16}>
          <Card title="Video Player">
            {video.proxy_status === 'completed' && video.proxy_path ? (
              <div
                style={{
                  width: '100%',
                  aspectRatio: '16/9',
                  background: '#000',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                }}
              >
                <Space direction="vertical" align="center">
                  <PlayCircleOutlined style={{ fontSize: 64 }} />
                  <Text style={{ color: '#fff' }}>
                    HLS Player would be rendered here
                  </Text>
                  <Text type="secondary" style={{ color: '#888' }}>
                    Path: {video.proxy_path}
                  </Text>
                </Space>
              </div>
            ) : (
              <div
                style={{
                  width: '100%',
                  aspectRatio: '16/9',
                  background: '#f0f0f0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Space direction="vertical" align="center">
                  <Tag color={getProxyStatusColor(video.proxy_status)}>
                    Proxy Status: {video.proxy_status}
                  </Tag>
                  {video.proxy_status === 'pending' && (
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={handleStartProxy}
                    >
                      Start Proxy Rendering
                    </Button>
                  )}
                  {video.proxy_status === 'processing' && (
                    <Button icon={<ReloadOutlined />} onClick={loadVideo}>
                      Refresh Status
                    </Button>
                  )}
                  {video.proxy_status === 'failed' && (
                    <Button
                      type="primary"
                      danger
                      icon={<ReloadOutlined />}
                      onClick={handleStartProxy}
                    >
                      Retry Proxy Rendering
                    </Button>
                  )}
                </Space>
              </div>
            )}
          </Card>
        </Col>

        {/* Video Info & Clip Extraction */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Video Information */}
            <Card title="Video Information" size="small">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Duration">
                  {formatDuration(video.duration_sec)}
                </Descriptions.Item>
                <Descriptions.Item label="FPS">{video.fps || 'N/A'}</Descriptions.Item>
                <Descriptions.Item label="Resolution">
                  {video.width && video.height
                    ? `${video.width}x${video.height}`
                    : 'N/A'}
                </Descriptions.Item>
                <Descriptions.Item label="File Size">
                  {video.file_size_mb?.toFixed(2)} MB
                </Descriptions.Item>
                <Descriptions.Item label="Proxy Status">
                  <Tag color={getProxyStatusColor(video.proxy_status)}>
                    {video.proxy_status}
                  </Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* Clip Extraction */}
            <Card title="Extract Clip" size="small">
              <Form form={form} layout="vertical">
                <Form.Item label="Start Time (seconds)" required>
                  <InputNumber
                    min={0}
                    max={video.duration_sec || 0}
                    value={startTime}
                    onChange={(value) => setStartTime(value || 0)}
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item label="End Time (seconds)" required>
                  <InputNumber
                    min={startTime + 0.1}
                    max={video.duration_sec || 0}
                    value={endTime}
                    onChange={(value) => setEndTime(value || 0)}
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item label="Padding (seconds)">
                  <InputNumber
                    min={0}
                    max={10}
                    value={padding}
                    onChange={(value) => setPadding(value || 0)}
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Clip duration: {formatDuration(endTime - startTime)}
                    {padding > 0 &&
                      ` (+ ${padding * 2}s padding = ${formatDuration(
                        endTime - startTime + padding * 2
                      )})`}
                  </Text>
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    icon={<ScissorOutlined />}
                    onClick={handleExtractClip}
                    loading={extracting}
                    disabled={video.proxy_status !== 'completed'}
                    block
                  >
                    Extract Clip
                  </Button>
                </Form.Item>

                {video.proxy_status !== 'completed' && (
                  <Alert
                    message="Proxy rendering required"
                    description="Please complete proxy rendering before extracting clips."
                    type="info"
                    showIcon
                    style={{ marginTop: 8 }}
                  />
                )}
              </Form>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  )
}

export default VideoPlayerPage
