/**
 * API Client for Video Proxy & Subclip Platform
 *
 * Uses axios for HTTP requests with automatic error handling
 */
import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  Video,
  VideoListResponse,
  Clip,
  ClipListResponse,
  ClipCreateRequest,
  ProxyStatusResponse,
  HealthResponse,
  RootResponse,
} from '@/types'

class ApiClient {
  private client: AxiosInstance

  constructor(baseURL: string = '/api') {
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          // Server responded with error status
          console.error('API Error:', error.response.data)
        } else if (error.request) {
          // Request made but no response
          console.error('Network Error:', error.message)
        } else {
          console.error('Error:', error.message)
        }
        return Promise.reject(error)
      }
    )
  }

  // ========== Health & Root ==========

  async getHealth(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health')
    return response.data
  }

  async getRoot(): Promise<RootResponse> {
    const response = await this.client.get<RootResponse>('/')
    return response.data
  }

  // ========== Videos ==========

  async listVideos(skip: number = 0, limit: number = 100): Promise<VideoListResponse> {
    const response = await this.client.get<VideoListResponse>('/videos', {
      params: { skip, limit },
    })
    return response.data
  }

  async getVideo(videoId: string): Promise<Video> {
    const response = await this.client.get<Video>(`/videos/${videoId}`)
    return response.data
  }

  async uploadVideo(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<Video> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post<Video>('/videos/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 300000, // 5 minutes for large uploads
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(percentCompleted)
        }
      },
    })
    return response.data
  }

  async deleteVideo(videoId: string): Promise<void> {
    await this.client.delete(`/videos/${videoId}`)
  }

  async startProxyRendering(videoId: string): Promise<{ message: string }> {
    const response = await this.client.post(`/videos/${videoId}/proxy`)
    return response.data
  }

  async getProxyStatus(videoId: string): Promise<ProxyStatusResponse> {
    const response = await this.client.get<ProxyStatusResponse>(
      `/videos/${videoId}/proxy/status`
    )
    return response.data
  }

  // ========== Clips ==========

  async listClips(
    videoId?: string,
    skip: number = 0,
    limit: number = 100
  ): Promise<ClipListResponse> {
    const params: Record<string, any> = { skip, limit }
    if (videoId) {
      params.video_id = videoId
    }

    const response = await this.client.get<ClipListResponse>('/clips', {
      params,
    })
    return response.data
  }

  async getClip(clipId: string): Promise<Clip> {
    const response = await this.client.get<Clip>(`/clips/${clipId}`)
    return response.data
  }

  async createClip(request: ClipCreateRequest): Promise<Clip> {
    const response = await this.client.post<Clip>('/clips/create', request, {
      timeout: 120000, // 2 minutes for clip extraction
    })
    return response.data
  }

  async deleteClip(clipId: string): Promise<void> {
    await this.client.delete(`/clips/${clipId}`)
  }

  async getClipDownloadUrl(clipId: string): string {
    return `${this.client.defaults.baseURL}/clips/${clipId}/download`
  }

  async listVideoClips(
    videoId: string,
    skip: number = 0,
    limit: number = 100
  ): Promise<ClipListResponse> {
    const response = await this.client.get<ClipListResponse>(
      `/clips/videos/${videoId}/clips`,
      {
        params: { skip, limit },
      }
    )
    return response.data
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

// Export class for testing
export { ApiClient }
