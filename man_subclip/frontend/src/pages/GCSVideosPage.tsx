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
} from 'antd'
import {
  CloudDownloadOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { apiClient } from '@/api/client'
import type { GCSVideo } from '@/types'

const { Title, Text } = Typography

function GCSVideosPage() {
  const navigate = useNavigate()

  const [videos, setVideos] = useState<GCSVideo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [importing, setImporting] = useState<string | null>(null)

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
                      type="primary"
                      icon={<CloudDownloadOutlined />}
                      onClick={() => handleImport(video.gcs_path, video.filename)}
                      loading={importing === video.gcs_path}
                      disabled={importing !== null && importing !== video.gcs_path}
                      block
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
    </div>
  )
}

export default GCSVideosPage
