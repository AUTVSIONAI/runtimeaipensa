# Browser Automation Testing Guide

## Prerequisites

```bash
# Install Python dependencies
pip install browser-use playwright
playwright install chromium

# Install Node dependencies
cd frontend && npm install
```

## Starting the Services

### Terminal 1: Backend Runtime API (port 8000)
```bash
cd C:\OPENMANUS\OpenManus
python -m runtime.api.server
```

### Terminal 2: Frontend (port 3000)
```bash
cd C:\OPENMANUS\OpenManus\frontend
npm run dev
```

### Terminal 3: Preview Server (port 8080) - for generated sites
```bash
cd C:\OPENMANUS\OpenManus
python preview_server.py
```

## Browser Page Features

1. **Session Management**
   - Create new browser sessions with any URL
   - Multiple tabs support
   - Live session listing

2. **Navigation**
   - Address bar with Enter to navigate
   - Back/Forward/Refresh buttons
   - Quick access buttons (Google, GitHub)

3. **Interaction**
   - Element Inspector - click the "Inspector" button, then click elements in screenshot
   - Click elements by selector
   - Type text into inputs
   - Scroll up/down
   - Get element text/attributes (href, src)

4. **Screenshots**
   - Viewport screenshot
   - Full page screenshot
   - Zoom control (25%-200%)

5. **Action Log**
   - History of all executed actions
   - Shows parameters and results

## Testing Steps

1. Open http://localhost:3000/dashboard/browser
2. Enter a URL (e.g., `https://example.com`) and click "Create"
3. Wait for screenshot to load
4. Click "Inspector" button
5. Click any element in the screenshot to inspect it
6. Use "Click", "Get Text", "Get Href" buttons in inspector panel
7. Test navigation with address bar
8. Test scroll buttons

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/browser/sessions` | List all sessions |
| POST | `/api/browser/session` | Create new session |
| GET | `/api/browser/session/{id}/state` | Get session state |
| POST | `/api/browser/session/{id}/action` | Execute action |
| POST | `/api/browser/session/{id}/screenshot` | Take screenshot |
| DELETE | `/api/browser/session/{id}` | Close session |

### Supported Actions

| Action | Parameters | Description |
|--------|------------|-------------|
| `click` | `{selector: string}` | Click element by CSS selector |
| `type` | `{selector: string, text: string}` | Type text into input |
| `Navigate` | `{url: string}` | Navigate to URL |
| `scroll_down` | `{amount?: number}` | Scroll down |
| `scroll_up` | `{amount?: number}` | Scroll up |
| `go_back` | `{}` | Go back in history |
| `go_forward` | `{}` | Go forward in history |
| `refresh` | `{}` | Refresh page |
| `wait` | `{seconds?: number}` | Wait |
| `get_text` | `{selector: string}` | Get element text |
| `get_attribute` | `{selector: string, attribute: string}` | Get element attribute |
| `switch_tab` | `{tab_id: number}` | Switch tab |
| `open_tab` | `{url: string}` | Open new tab |
| `close_tab` | `{}` | Close current tab |

## Troubleshooting

### 404 on /dashboard/browser
- Clear Next.js cache: `rm -rf .next` then `npm run dev`
- Ensure `page.tsx` exists in `src/app/dashboard/browser/`

### Browser module not available
- Check `runtime.toml` has browser module enabled:
```toml
[[runtime.modules.browser]]
name = "local-browser"
enabled = true
required = true
```
- Verify browser-use is installed: `pip list | grep browser-use`

### No screenshot appearing
- Check browser is not headless: `headless = false` in runtime.toml
- Ensure Playwright Chromium is installed: `playwright install chromium`

### Element clicks not working
- The module now supports both:
  - Frontend: CSS selectors (`click` with `selector`)
  - Backend: Element indices (`click` with `index`)

## Architecture

```
Frontend (React)          Backend (FastAPI)           Browser Engine
     │                        │                          │
     ├─ GET /sessions ──────►│                          │
     │◄──── 200 OK ──────────┤                          │
     │                        │                          │
     ├─ POST /session ──────►│                          │
     │   {url: "..."}        │                          │
     │◄──── 201 Created ─────┤                          │
     │                        │                          │
     ├─ POST /action ───────►│                          │
     │   {action:"click",    │     browser-use          │
     │    params:{selector}} ├─────► Playwright ───────►│
     │◄──── Result ──────────┤      (chromium)          │
     │                        │                          │
     ├─ POST /screenshot ───►│                          │
     │◄──── base64 PNG ──────┤                          │
```