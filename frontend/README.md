# Academic Content Generator - Frontend

Next.js-based frontend for the academic content generation system.

## Tech Stack
- **Framework**: Next.js 14
- **UI**: React 18 + Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Markdown**: react-markdown
- **Icons**: lucide-react

## Features
- ChatGPT/Gemini-like UI
- Real-time streaming responses
- Multi-threaded conversations
- File upload support
- Responsive design

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Build

```bash
npm run build
npm start
```

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── components/      # React components
├── hooks/          # Custom hooks
├── lib/            # Utilities and API client
├── pages/          # Next.js pages
├── public/         # Static assets
├── store/          # Zustand stores
├── styles/         # Global styles
├── types/          # TypeScript types
└── package.json
```
