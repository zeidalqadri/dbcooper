# DB Migration Manager - Web UI

Modern, minimalistic web interface for the Database Migration Management System.

## Features

- Real-time migration status updates via WebSocket
- Interactive dashboard with system health monitoring
- Migration management (create, apply, rollback)
- Compliance validation and reporting
- Migration history with analytics
- Dark mode support (coming soon)
- Mobile responsive design

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **State Management**: Zustand + SWR
- **Charts**: Chart.js
- **Code Editor**: Monaco Editor
- **HTTP Client**: Axios
- **Real-time**: WebSocket

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   ├── pages/              # Page components
│   │   ├── Dashboard.tsx    # Main dashboard
│   │   ├── Migrations.tsx   # Migration management
│   │   ├── Compliance.tsx   # Compliance dashboard
│   │   └── History.tsx      # Migration history
│   ├── services/           # API and WebSocket services
│   │   ├── api.ts          # HTTP API client
│   │   └── websocket.ts    # WebSocket client
│   ├── types/              # TypeScript type definitions
│   ├── hooks/              # Custom React hooks
│   ├── stores/             # Global state stores
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── index.html             # HTML template
├── package.json           # Dependencies
├── vite.config.ts         # Vite configuration
├── tailwind.config.js     # Tailwind configuration
└── tsconfig.json          # TypeScript configuration
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Lint code

## Development

### Adding a New Page

1. Create a new file in `src/pages/`
2. Add the route in `src/App.tsx`
3. Add navigation link if needed

### Adding a New API Endpoint

1. Add the function in `src/services/api.ts`
2. Define types in `src/types/index.ts`
3. Use SWR hook in components for caching

### WebSocket Events

Listen to WebSocket events using the `wsService`:

```typescript
import wsService from './services/websocket';

useEffect(() => {
  const handleUpdate = (data) => {
    console.log('Update received:', data);
  };

  wsService.on('status_update', handleUpdate);

  return () => {
    wsService.off('status_update', handleUpdate);
  };
}, []);
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### Tailwind Customization

Edit `tailwind.config.js` to customize colors, spacing, etc.

### Vite Proxy

The Vite dev server proxies API requests to avoid CORS issues.
Configure in `vite.config.ts`.

## Deployment

### Static Hosting

Build the project and deploy the `dist/` folder to:
- Netlify
- Vercel
- GitHub Pages
- AWS S3 + CloudFront

### Docker

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### With Backend

The backend API can serve the frontend:

```bash
# Build frontend
cd frontend && npm run build

# Backend serves from dist/
python -m src.ui_server
```

## Browser Support

- Chrome/Edge: Last 2 versions
- Firefox: Last 2 versions
- Safari: Last 2 versions
- Mobile browsers: iOS Safari 14+, Chrome Android 90+

## Contributing

See main project README for contribution guidelines.

## License

[Your License Here]
