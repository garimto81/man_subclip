/**
 * UploadPage Component Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import UploadPage from '../UploadPage'
import { apiClient } from '@/api/client'

// Mock API client
vi.mock('@/api/client', () => ({
  apiClient: {
    uploadVideo: vi.fn(),
  },
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('UploadPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload page with instructions', () => {
    render(
      <BrowserRouter>
        <UploadPage />
      </BrowserRouter>
    )

    expect(screen.getByText('Upload Video')).toBeInTheDocument()
    expect(
      screen.getByText(/Upload your original video file/)
    ).toBeInTheDocument()
    expect(screen.getByText('Supported Formats')).toBeInTheDocument()
  })

  it('displays allowed file formats', () => {
    render(
      <BrowserRouter>
        <UploadPage />
      </BrowserRouter>
    )

    const formatsText = screen.getByText(/Formats:/)
    expect(formatsText.textContent).toContain('.mp4')
    expect(formatsText.textContent).toContain('.mov')
    expect(formatsText.textContent).toContain('.avi')
  })

  it('displays maximum file size', () => {
    render(
      <BrowserRouter>
        <UploadPage />
      </BrowserRouter>
    )

    expect(screen.getByText(/Maximum size: 10GB/)).toBeInTheDocument()
  })

  it('shows workflow explanation', () => {
    render(
      <BrowserRouter>
        <UploadPage />
      </BrowserRouter>
    )

    expect(screen.getByText('What happens after upload?')).toBeInTheDocument()
    expect(screen.getByText(/Metadata Extraction/)).toBeInTheDocument()
    expect(screen.getByText(/Proxy Rendering/)).toBeInTheDocument()
    expect(screen.getByText(/Subclip Extraction/)).toBeInTheDocument()
  })

  it('has upload dragger component', () => {
    render(
      <BrowserRouter>
        <UploadPage />
      </BrowserRouter>
    )

    expect(
      screen.getByText(/Click or drag video file to this area/)
    ).toBeInTheDocument()
  })

  it('has navigation button to video library', () => {
    render(
      <BrowserRouter>
        <UploadPage />
      </BrowserRouter>
    )

    const libraryButton = screen.getByText('Go to Video Library')
    expect(libraryButton).toBeInTheDocument()
  })
})
