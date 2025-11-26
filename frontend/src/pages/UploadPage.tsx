import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload,
  Button,
  message,
  Typography,
  Card,
  Space,
  Alert,
  Progress,
} from 'antd'
import { InboxOutlined, CloudUploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { apiClient } from '@/api/client'
import type { Video } from '@/types'

const { Title, Paragraph, Text } = Typography
const { Dragger } = Upload

function UploadPage() {
  const navigate = useNavigate()
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedVideo, setUploadedVideo] = useState<Video | null>(null)

  // Allowed video extensions
  const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mxf', '.mkv']
  const MAX_FILE_SIZE_GB = 10

  const handleUpload = async (file: File): Promise<void> => {
    // Validate file extension
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(fileExtension)) {
      message.error(
        `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`
      )
      return
    }

    // Validate file size
    const fileSizeGB = file.size / (1024 * 1024 * 1024)
    if (fileSizeGB > MAX_FILE_SIZE_GB) {
      message.error(`File too large. Maximum size: ${MAX_FILE_SIZE_GB}GB`)
      return
    }

    setUploading(true)
    setUploadProgress(0)

    try {
      // Upload file with progress tracking
      const video = await apiClient.uploadVideo(file, (progress) => {
        setUploadProgress(progress)
      })

      message.success(`Video uploaded successfully: ${video.filename}`)
      setUploadedVideo(video)

      // Redirect to library after 2 seconds
      setTimeout(() => {
        navigate('/')
      }, 2000)
    } catch (error: any) {
      message.error(
        `Upload failed: ${error.response?.data?.detail || error.message}`
      )
    } finally {
      setUploading(false)
    }
  }

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: ALLOWED_EXTENSIONS.join(','),
    showUploadList: false,
    beforeUpload: (file) => {
      handleUpload(file)
      return false // Prevent default upload behavior
    },
  }

  return (
    <div>
      <Title level={2}>Upload Video</Title>
      <Paragraph>
        Upload your original video file. It will be automatically processed for web
        playback.
      </Paragraph>

      <Card style={{ marginTop: 24, maxWidth: 800 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Alert
            message="Supported Formats"
            description={
              <div>
                <Text>Formats: {ALLOWED_EXTENSIONS.join(', ')}</Text>
                <br />
                <Text>Maximum size: {MAX_FILE_SIZE_GB}GB</Text>
              </div>
            }
            type="info"
            showIcon
          />

          <Dragger {...uploadProps} disabled={uploading}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">
              Click or drag video file to this area to upload
            </p>
            <p className="ant-upload-hint">
              Support for single file upload. Video will be processed for HLS
              streaming.
            </p>
          </Dragger>

          {uploading && (
            <div>
              <Text>Uploading...</Text>
              <Progress percent={uploadProgress} status="active" />
            </div>
          )}

          {uploadedVideo && (
            <Alert
              message="Upload Successful"
              description={
                <div>
                  <Text strong>{uploadedVideo.filename}</Text>
                  <br />
                  <Text type="secondary">
                    Duration: {uploadedVideo.duration_sec?.toFixed(2)}s | FPS:{' '}
                    {uploadedVideo.fps} | Resolution: {uploadedVideo.width}x
                    {uploadedVideo.height}
                  </Text>
                  <br />
                  <Text type="secondary">
                    Size: {uploadedVideo.file_size_mb?.toFixed(2)}MB
                  </Text>
                  <br />
                  <br />
                  <Text>Redirecting to video library...</Text>
                </div>
              }
              type="success"
              showIcon
            />
          )}

          <div style={{ textAlign: 'center' }}>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={() => navigate('/')}
              disabled={uploading}
            >
              Go to Video Library
            </Button>
          </div>
        </Space>
      </Card>

      <Card style={{ marginTop: 24, maxWidth: 800 }}>
        <Title level={4}>What happens after upload?</Title>
        <ol>
          <li>
            <Text strong>Metadata Extraction:</Text> Duration, FPS, resolution, and
            file size are automatically extracted.
          </li>
          <li>
            <Text strong>Storage:</Text> Original video is saved to NAS storage.
          </li>
          <li>
            <Text strong>Proxy Rendering:</Text> Video is queued for HLS conversion
            for web playback (you can trigger this manually).
          </li>
          <li>
            <Text strong>Subclip Extraction:</Text> Once proxy is ready, you can
            extract subclips with frame-accurate timecodes.
          </li>
        </ol>
      </Card>
    </div>
  )
}

export default UploadPage
