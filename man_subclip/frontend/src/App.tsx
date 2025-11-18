import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { Layout, Menu, Typography } from 'antd'
import {
  VideoCameraOutlined,
  FolderOutlined,
  ScissorOutlined,
} from '@ant-design/icons'
import VideoLibraryPage from './pages/VideoLibraryPage'
import UploadPage from './pages/UploadPage'
import './App.css'

const { Header, Content, Footer } = Layout
const { Title } = Typography

function App() {
  const menuItems = [
    {
      key: 'home',
      icon: <FolderOutlined />,
      label: <Link to="/">Video Library</Link>,
    },
    {
      key: 'upload',
      icon: <VideoCameraOutlined />,
      label: <Link to="/upload">Upload Video</Link>,
    },
    {
      key: 'clips',
      icon: <ScissorOutlined />,
      label: <Link to="/clips">Clips</Link>,
    },
  ]

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center', padding: '0 24px' }}>
          <Title level={3} style={{ color: 'white', margin: 0, marginRight: 40 }}>
            Video Proxy & Subclip Platform
          </Title>
          <Menu
            theme="dark"
            mode="horizontal"
            defaultSelectedKeys={['home']}
            items={menuItems}
            style={{ flex: 1, minWidth: 0 }}
          />
        </Header>

        <Content style={{ padding: '24px' }}>
          <div style={{ background: '#fff', padding: 24, minHeight: 'calc(100vh - 134px)' }}>
            <Routes>
              <Route path="/" element={<VideoLibraryPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/video/:videoId" element={<div>Video Player Page (Coming Soon)</div>} />
              <Route path="/clips" element={<div>Clips Page (Coming Soon)</div>} />
            </Routes>
          </div>
        </Content>

        <Footer style={{ textAlign: 'center' }}>
          Video Proxy & Subclip Platform ©2025
        </Footer>
      </Layout>
    </Router>
  )
}

export default App
