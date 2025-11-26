import { Typography } from 'antd'

const { Title, Paragraph } = Typography

function HomePage() {
  return (
    <div>
      <Title level={2}>Welcome to Video Proxy & Subclip Platform</Title>
      <Paragraph>
        This platform allows you to:
      </Paragraph>
      <ul>
        <li>Upload original videos and convert them to HLS proxy format for web playback</li>
        <li>Extract subclips from original videos with frame-accurate timecodes</li>
        <li>Download and manage your video clips</li>
      </ul>
      <Paragraph style={{ marginTop: 24 }}>
        Get started by uploading a video or browsing your library.
      </Paragraph>
    </div>
  )
}

export default HomePage
