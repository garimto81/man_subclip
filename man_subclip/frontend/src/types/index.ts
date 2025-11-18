/**
 * Frontend Types for Video Proxy & Subclip Platform
 */

export interface Video {
  video_id: string
  filename: string
  original_path: string
  proxy_path: string | null
  proxy_status: 'pending' | 'processing' | 'completed' | 'failed'
  duration_sec: number | null
  fps: number | null
  width: number | null
  height: number | null
  file_size_mb: number | null
  created_at: string
  updated_at: string
}

export interface VideoListResponse {
  total: number
  videos: Video[]
}

export interface Clip {
  clip_id: string
  video_id: string
  start_sec: number
  end_sec: number
  padding_sec: number
  file_path: string
  file_size_mb: number
  duration_sec: number
  created_at: string
}

export interface ClipListResponse {
  total: number
  clips: Clip[]
}

export interface ClipCreateRequest {
  video_id: string
  start_sec: number
  end_sec: number
  padding_sec: number
}

export interface ProxyStatusResponse {
  video_id: string
  proxy_status: string
  proxy_path: string | null
}

export interface HealthResponse {
  status: string
}

export interface RootResponse {
  message: string
  version: string
  status: string
}
