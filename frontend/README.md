# Video Proxy & Subclip Platform - Frontend

React + TypeScript + Vite frontend for the Video Proxy & Subclip Platform.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Ant Design 5** - UI component library
- **React Router** - Routing
- **Axios** - HTTP client

## Development

```bash
# Install dependencies
npm install

# Run development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── api/           # API client
│   │   └── client.ts  # Axios HTTP client
│   ├── pages/         # Page components
│   │   └── HomePage.tsx
│   ├── types/         # TypeScript types
│   │   └── index.ts
│   ├── App.tsx        # Main app component
│   ├── App.css        # App styles
│   ├── index.css      # Global styles
│   └── main.tsx       # Entry point
├── index.html         # HTML template
├── vite.config.ts     # Vite configuration
├── tsconfig.json      # TypeScript configuration
└── package.json       # Dependencies
```

## API Integration

The frontend communicates with the FastAPI backend running on `http://localhost:8000`.

Vite proxy configuration automatically forwards `/api/*` requests to the backend.

## Features

- Video library browsing
- Video upload with progress
- Proxy rendering status tracking
- Subclip extraction with timeline editor
- HLS video playback

## Planned Pages

1. **Video Library** - Grid view of all videos with search/filter
2. **Upload Page** - Video upload with drag-and-drop
3. **Player Page** - HLS player with timeline editor for subclip extraction
4. **Clips Page** - List of all extracted clips
