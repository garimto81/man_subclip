import { Card, Tag, Typography, Space, Button, Tooltip } from 'antd'
import {
  PlayCircleOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  FileOutlined,
  ScissorOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { Video } from '@/types'

const { Text } = Typography

interface VideoCardProps {
  video: Video
}

function VideoCard({ video }: VideoCardProps) {
  const navigate = useNavigate()

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

  const getProxyStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Ready'
      case 'processing':
        return 'Processing'
      case 'failed':
        return 'Failed'
      default:
        return 'Pending'
    }
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatFileSize = (mb: number | null) => {
    if (!mb) return 'N/A'
    if (mb > 1024) {
      return `${(mb / 1024).toFixed(2)} GB`
    }
    return `${mb.toFixed(2)} MB`
  }

  return (
    <Card
      hoverable
      className="video-card"
      cover={
        <div
          className="video-thumbnail"
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
          }}
        >
          <PlayCircleOutlined style={{ fontSize: 64, opacity: 0.8 }} />
        </div>
      }
      actions={[
        <Tooltip title="View Details">
          <Button
            type="text"
            icon={<PlayCircleOutlined />}
            onClick={() => navigate(`/video/${video.video_id}`)}
          >
            View
          </Button>
        </Tooltip>,
        <Tooltip title="Extract Clip">
          <Button
            type="text"
            icon={<ScissorOutlined />}
            disabled={video.proxy_status !== 'completed'}
            onClick={() => navigate(`/video/${video.video_id}?action=clip`)}
          >
            Clip
          </Button>
        </Tooltip>,
      ]}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Text strong ellipsis={{ tooltip: video.filename }}>
          {video.filename}
        </Text>

        <Tag color={getProxyStatusColor(video.proxy_status)}>
          {getProxyStatusText(video.proxy_status)}
        </Tag>

        <Space size="small" wrap>
          <Tooltip title="Duration">
            <Text type="secondary" style={{ fontSize: 12 }}>
              <ClockCircleOutlined /> {formatDuration(video.duration_sec)}
            </Text>
          </Tooltip>

          {video.fps && (
            <Tooltip title="Frame Rate">
              <Text type="secondary" style={{ fontSize: 12 }}>
                <DashboardOutlined /> {video.fps} fps
              </Text>
            </Tooltip>
          )}

          {video.width && video.height && (
            <Tooltip title="Resolution">
              <Text type="secondary" style={{ fontSize: 12 }}>
                {video.width}x{video.height}
              </Text>
            </Tooltip>
          )}
        </Space>

        <Text type="secondary" style={{ fontSize: 12 }}>
          <FileOutlined /> {formatFileSize(video.file_size_mb)}
        </Text>
      </Space>
    </Card>
  )
}

export default VideoCard
