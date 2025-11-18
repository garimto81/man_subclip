/**
 * VideoCard Component Tests
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import VideoCard from '../VideoCard'
import type { Video } from '@/types'

const mockVideo: Video = {
  video_id: '123e4567-e89b-12d3-a456-426614174000',
  filename: 'test_video.mp4',
  original_path: '/nas/originals/test_video.mp4',
  proxy_path: '/nas/proxy/123/master.m3u8',
  proxy_status: 'completed',
  duration_sec: 125.5,
  fps: 30,
  width: 1920,
  height: 1080,
  file_size_mb: 150.5,
  created_at: '2025-01-18T10:00:00Z',
  updated_at: '2025-01-18T10:05:00Z',
}

describe('VideoCard', () => {
  it('renders video filename', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    expect(screen.getByText('test_video.mp4')).toBeInTheDocument()
  })

  it('shows proxy status tag', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    expect(screen.getByText('Ready')).toBeInTheDocument()
  })

  it('displays duration in MM:SS format', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    // 125.5 seconds = 2:05
    expect(screen.getByText(/2:05/)).toBeInTheDocument()
  })

  it('shows fps when available', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    expect(screen.getByText(/30 fps/)).toBeInTheDocument()
  })

  it('shows resolution when available', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    expect(screen.getByText('1920x1080')).toBeInTheDocument()
  })

  it('displays file size in MB', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    expect(screen.getByText(/150.50 MB/)).toBeInTheDocument()
  })

  it('displays file size in GB for large files', () => {
    const largeVideo = { ...mockVideo, file_size_mb: 2048 }

    render(
      <BrowserRouter>
        <VideoCard video={largeVideo} />
      </BrowserRouter>
    )

    expect(screen.getByText(/2.00 GB/)).toBeInTheDocument()
  })

  it('has View button', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    expect(screen.getByText('View')).toBeInTheDocument()
  })

  it('has Clip button enabled when proxy is ready', () => {
    render(
      <BrowserRouter>
        <VideoCard video={mockVideo} />
      </BrowserRouter>
    )

    const clipButton = screen.getByText('Clip')
    expect(clipButton).toBeInTheDocument()
    expect(clipButton).not.toBeDisabled()
  })

  it('disables Clip button when proxy is not ready', () => {
    const pendingVideo = { ...mockVideo, proxy_status: 'pending' as const }

    render(
      <BrowserRouter>
        <VideoCard video={pendingVideo} />
      </BrowserRouter>
    )

    const clipButton = screen.getByText('Clip')
    expect(clipButton).toBeDisabled()
  })
})
