# ESGBuddy Frontend

Intelligent ESG Compliance Copilot - React Frontend Application

## Overview

The ESGBuddy frontend is a modern, production-grade React application with a distinctive UI design. It provides an intuitive interface for uploading ESG documents, browsing compliance clauses, and viewing detailed compliance reports.

## Design Philosophy

This interface follows a refined, editorial aesthetic with:

- **Typography**: Playfair Display (display), DM Sans (body), JetBrains Mono (code)
- **Color Palette**: Forest green primary, Clay beige background, Ink dark text
- **Animations**: Smooth, purposeful animations using Framer Motion
- **Layout**: Clean, spacious design with generous white space

The design avoids generic AI aesthetics and creates a memorable, professional experience appropriate for ESG compliance professionals.

## Features

### 1. Home Page

- System overview and statistics
- Feature highlights
- Supported frameworks overview
- Call-to-action for uploading documents

### 2. Upload Page

- Drag-and-drop PDF upload
- Real-time upload progress
- Document processing feedback
- Automatic redirect after success

### 3. Documents Page

- List all uploaded documents
- Search and filter functionality
- Quick evaluation with framework selection
- Document management (delete)

### 4. Clauses Page

- Browse ESG clauses by framework
- Search functionality
- Expandable clause details
- Validation rules display
- Evidence types and keywords

### 5. Reports Page

- View all compliance reports
- Summary statistics
- Status distribution
- Quick navigation to detailed views

### 6. Report Detail Page

- Comprehensive clause evaluations
- AI analysis explanations
- Retrieved evidence display
- Rule validation results
- Status filtering
- Confidence scores

## Tech Stack

- **React 18** - UI framework
- **React Router** - Navigation
- **Framer Motion** - Animations
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **Axios** - API requests
- **Vite** - Build tool

## Setup

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create a `.env` file (optional):

```
VITE_API_URL=http://localhost:8000
```

If not set, the app will use `/api` as the base URL (proxied through Vite dev server).

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── Layout.jsx          # Main layout with navigation
│   ├── pages/
│   │   ├── Home.jsx             # Landing page
│   │   ├── Upload.jsx           # Document upload
│   │   ├── Documents.jsx        # Document management
│   │   ├── Clauses.jsx          # ESG clauses browser
│   │   ├── Reports.jsx          # Reports list
│   │   └── ReportDetail.jsx     # Detailed report view
│   ├── lib/
│   │   └── api.js               # API client functions
│   ├── App.jsx                  # Root component
│   ├── main.jsx                 # Entry point
│   └── index.css                # Global styles
├── public/
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## API Integration

All API calls are centralized in `src/lib/api.js`. The frontend communicates with the backend FastAPI server through the following endpoints:

- **Documents**: Upload, list, delete
- **Clauses**: Browse, search, filter
- **Compliance**: Evaluate, view reports
- **Accuracy**: Metrics and benchmarking
- **System**: Health check, stats

## Customization

### Colors

Edit `tailwind.config.js` to change the color palette:

```js
colors: {
  'forest': { ... },  // Primary green
  'clay': { ... },    // Background beige
  'ink': { ... },     // Text colors
}
```

### Fonts

Fonts are loaded from Google Fonts in `index.html`. Change the font families in `tailwind.config.js`:

```js
fontFamily: {
  'display': ['"Playfair Display"', ...],
  'sans': ['"DM Sans"', ...],
  'mono': ['"JetBrains Mono"', ...],
}
```

### Animations

Framer Motion animations can be customized in individual components. Global animation utilities are defined in `tailwind.config.js`.

## Responsive Design

The application is fully responsive with breakpoints:

- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Code splitting with React Router
- Lazy loading of images
- Optimized animations
- Efficient re-renders with React best practices

## Contributing

When adding new features:

1. Follow the existing design system
2. Use Tailwind classes consistently
3. Add smooth animations for state changes
4. Ensure mobile responsiveness
5. Test all API integrations

## License

All rights reserved.
