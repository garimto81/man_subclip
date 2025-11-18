import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Typography,
  Input,
  Select,
  Row,
  Col,
  Space,
  Button,
  Empty,
  Spin,
  Alert,
  Pagination,
} from 'antd'
import {
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { apiClient } from '@/api/client'
import type { Video } from '@/types'
import VideoCard from '@/components/VideoCard'

const { Title } = Typography
const { Search } = Input

function VideoLibraryPage() {
  const navigate = useNavigate()

  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [proxyStatusFilter, setProxyStatusFilter] = useState<string>('all')

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(12)
  const [total, setTotal] = useState(0)

  const loadVideos = async () => {
    setLoading(true)
    setError(null)

    try {
      const skip = (currentPage - 1) * pageSize
      const response = await apiClient.listVideos(skip, pageSize)

      setVideos(response.videos)
      setTotal(response.total)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load videos')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadVideos()
  }, [currentPage])

  // Filter videos based on search query and proxy status
  const filteredVideos = videos.filter((video) => {
    // Search filter
    const matchesSearch = video.filename
      .toLowerCase()
      .includes(searchQuery.toLowerCase())

    // Proxy status filter
    const matchesProxy =
      proxyStatusFilter === 'all' || video.proxy_status === proxyStatusFilter

    return matchesSearch && matchesProxy
  })

  const handleSearch = (value: string) => {
    setSearchQuery(value)
    setCurrentPage(1) // Reset to first page on search
  }

  const handleProxyFilterChange = (value: string) => {
    setProxyStatusFilter(value)
    setCurrentPage(1) // Reset to first page on filter change
  }

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ margin: 0 }}>
            Video Library
          </Title>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/upload')}
          >
            Upload Video
          </Button>
        </Col>
      </Row>

      {/* Filters */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Search
            placeholder="Search videos..."
            prefix={<SearchOutlined />}
            allowClear
            onSearch={handleSearch}
            onChange={(e) => setSearchQuery(e.target.value)}
            value={searchQuery}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Select
            style={{ width: '100%' }}
            placeholder="Filter by proxy status"
            value={proxyStatusFilter}
            onChange={handleProxyFilterChange}
            suffixIcon={<FilterOutlined />}
            options={[
              { label: 'All Videos', value: 'all' },
              { label: 'Ready for Playback', value: 'completed' },
              { label: 'Processing', value: 'processing' },
              { label: 'Pending', value: 'pending' },
              { label: 'Failed', value: 'failed' },
            ]}
          />
        </Col>
        <Col>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadVideos()}
            loading={loading}
          >
            Refresh
          </Button>
        </Col>
      </Row>

      {/* Error Alert */}
      {error && (
        <Alert
          message="Error Loading Videos"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" tip="Loading videos..." />
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredVideos.length === 0 && (
        <Empty
          description={
            searchQuery || proxyStatusFilter !== 'all'
              ? 'No videos match your filters'
              : 'No videos uploaded yet'
          }
          style={{ padding: '60px 0' }}
        >
          {!searchQuery && proxyStatusFilter === 'all' && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/upload')}
            >
              Upload Your First Video
            </Button>
          )}
        </Empty>
      )}

      {/* Video Grid */}
      {!loading && filteredVideos.length > 0 && (
        <>
          <Row gutter={[16, 16]}>
            {filteredVideos.map((video) => (
              <Col xs={24} sm={12} md={8} lg={6} key={video.video_id}>
                <VideoCard video={video} />
              </Col>
            ))}
          </Row>

          {/* Pagination */}
          {total > pageSize && (
            <Row justify="center" style={{ marginTop: 32 }}>
              <Pagination
                current={currentPage}
                pageSize={pageSize}
                total={total}
                onChange={(page) => setCurrentPage(page)}
                showSizeChanger={false}
                showTotal={(total, range) =>
                  `${range[0]}-${range[1]} of ${total} videos`
                }
              />
            </Row>
          )}
        </>
      )}

      {/* Stats */}
      {!loading && filteredVideos.length > 0 && (
        <Row justify="center" style={{ marginTop: 24 }}>
          <Space size="large">
            <span>
              Total: <strong>{total}</strong> videos
            </span>
            <span>
              Showing: <strong>{filteredVideos.length}</strong>
            </span>
          </Space>
        </Row>
      )}
    </div>
  )
}

export default VideoLibraryPage
