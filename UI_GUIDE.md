# User Interface Guide

The Database Migration Management System provides **two intuitive interfaces**:

1. **Web Dashboard** - Modern, browser-based UI with real-time updates
2. **Terminal UI (TUI)** - Rich terminal interface for CLI enthusiasts

---

## 🌐 Web Dashboard

### Quick Start

```bash
# Terminal 1: Start backend API
export DATABASE_URL="your_database_url"
python -m src.api

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

Access the dashboard at: **http://localhost:3000**

### Features

#### Dashboard Page
- **Real-time Status**: Live updates via WebSocket every 5 seconds
- **Compliance Indicator**: Large visual indicator of system compliance state
- **Metrics Cards**: Applied, Pending, Failed, and Total migration counts
- **Quick Actions**: One-click buttons for common operations
- **Recent Activity**: Timeline of last 5 migrations with execution times

#### Migrations Page
- **Searchable List**: Filter by name, version, or status
- **Inline Actions**: Apply, rollback, or view details per migration
- **Status Indicators**: Color-coded visual cues (✓ green, ○ yellow, ✗ red)
- **Bulk Operations**: Select multiple migrations for batch actions
- **File Upload**: Drag-and-drop SQL/Python migration files

#### Compliance Page
- **Visual Checks**: Green checkmarks for passed checks, red X for violations
- **Severity Levels**: Color-coded violation severity (Critical, High, Medium, Low)
- **DDL Audit Log**: Real-time log of all schema modification attempts
- **Recommendations**: Actionable steps to resolve violations
- **Export Reports**: Download compliance reports as JSON/PDF

#### History Page
- **Timeline View**: Chronological list of all migrations
- **Execution Analytics**: Charts showing execution time trends
- **Success Rate**: Visual percentage of successful migrations
- **Error Details**: Expandable error messages for failed migrations
- **Date Filtering**: Filter by date range or specific time periods

### Keyboard Shortcuts

| Key         | Action                          |
|-------------|---------------------------------|
| `/`         | Focus search                    |
| `n`         | Create new migration            |
| `a`         | Apply pending migrations        |
| `r`         | Refresh current view            |
| `Esc`       | Close modal/cancel action       |
| `?`         | Show keyboard shortcuts         |

### Real-time Updates

The dashboard automatically updates when:
- Migrations are applied or rolled back
- Compliance state changes
- New pending migrations are detected
- Failures occur

WebSocket connection status shown in header:
- **● Green**: Connected
- **○ Yellow**: Reconnecting
- **✗ Red**: Disconnected

### Mobile Support

The web dashboard is fully responsive and works on:
- **Tablets**: Full feature set with touch-optimized controls
- **Phones**: Simplified layout with essential functions
- **Desktop**: Complete experience with all features

### Dark Mode

Toggle dark mode using the theme switcher in the top-right corner.
Your preference is saved in browser local storage.

---

## 💻 Terminal UI (TUI)

### Quick Start

```bash
# Run the TUI
python -m src.tui
```

### Features

The TUI provides a full-featured terminal experience with:

- **Interactive Menu**: Number keys or arrow keys for navigation
- **Live Status**: Real-time migration state display
- **Color-Coded Output**: Red (errors), Green (success), Yellow (warnings)
- **Confirmation Prompts**: Safe operations with "Are you sure?" dialogs
- **Progress Indicators**: Spinners and progress bars for long operations

### Main Menu

```
╔═══════════════════════════════════════════╗
║  DB MIGRATION MANAGER v1.0.0              ║
╠═══════════════════════════════════════════╣
║                                           ║
║  [1] Status        [2] List Migrations    ║
║  [3] Create        [4] Apply Pending      ║
║  [5] Compliance    [R] Refresh            ║
║  [Q] Quit                                 ║
║                                           ║
╚═══════════════════════════════════════════╝
```

### Commands

#### 1. Status
- Current compliance state
- Migration counts (applied, pending, failed)
- Last applied migration info
- Warnings and alerts

#### 2. List Migrations
- Pending migrations (yellow)
- Applied migrations (green ✓)
- Failed migrations (red ✗)
- Execution times

#### 3. Create Migration
- Interactive prompts for:
  - Description
  - File type (SQL or Python)
- Auto-generates timestamped filename
- Opens created file in editor (if configured)

#### 4. Apply Pending
- Shows list of pending migrations
- Confirmation prompt
- Live progress indicator
- Success/failure summary

#### 5. Compliance
- Visual compliance status
- List of violations with severity
- Actionable recommendations
- Checksum validation results

### Navigation

| Key         | Action                    |
|-------------|---------------------------|
| `1-5`       | Select menu option        |
| `R`         | Refresh current view      |
| `Q`         | Quit (with confirmation)  |
| `Ctrl+C`    | Force quit                |
| `Enter`     | Confirm/Continue          |
| `Esc`       | Cancel operation          |

### Color Legend

- **🟢 Green**: Success, compliant, applied
- **🟡 Yellow**: Pending, warning, attention needed
- **🔴 Red**: Failed, error, critical violation
- **🔵 Cyan**: Information, metadata
- **⚪ Gray**: Secondary information

### Tips

1. **Pipe to File**: Redirect output for logging
   ```bash
   python -m src.tui | tee migration-session.log
   ```

2. **Run in tmux/screen**: Keep TUI running in background session
   ```bash
   tmux new -s migrations
   python -m src.tui
   ```

3. **SSH-Friendly**: Works perfectly over SSH connections

---

## 🎨 UI Design Principles

### Minimalism
- Clean, uncluttered layouts
- Essential information prominently displayed
- Progressive disclosure for advanced features
- Generous whitespace

### Consistency
- Uniform color scheme across both UIs
- Consistent terminology and labels
- Predictable interaction patterns
- Standard keyboard shortcuts

### Accessibility
- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader compatible
- High contrast mode available
- Adjustable font sizes

### Performance
- Optimistic UI updates
- Debounced search
- Lazy loading for large lists
- Efficient WebSocket usage
- Minimal bundle size

---

## 🚀 Deployment

### Web Dashboard - Production

1. **Build Frontend**:
   ```bash
   cd frontend
   npm run build
   ```

2. **Serve with Backend**:
   ```python
   # src/ui_server.py will serve static files
   python -m src.ui_server
   ```

3. **Docker**:
   ```bash
   docker build -t migration-manager .
   docker run -p 8000:8000 migration-manager
   ```

### TUI - System-wide Installation

```bash
# Install as command
pip install -e .

# Run from anywhere
migration-tui
```

---

## 📊 Comparison

| Feature                | Web Dashboard | Terminal UI |
|------------------------|:-------------:|:-----------:|
| Real-time Updates      | ✓             | ✗           |
| Mouse Support          | ✓             | ✗           |
| Keyboard Navigation    | ✓             | ✓           |
| Mobile Friendly        | ✓             | ✗           |
| SSH Compatible         | ✗             | ✓           |
| No Browser Required    | ✗             | ✓           |
| Visual Charts          | ✓             | ✗           |
| Code Editor            | ✓             | ✗           |
| Resource Usage         | Medium        | Low         |
| Offline Capable        | With PWA      | ✓           |

### When to Use Web Dashboard
- Team collaboration
- Mobile/tablet access
- Visual analytics needed
- Multi-user environment
- Remote monitoring

### When to Use TUI
- SSH-only access
- Server administration
- Low-bandwidth connections
- Terminal workflow preference
- Automated scripting

---

## 🛠️ Customization

### Web Dashboard

**Colors** - Edit `frontend/tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      primary: {
        600: '#YOUR_COLOR',
      },
    },
  },
}
```

**Layout** - Edit `frontend/src/App.tsx`
**Components** - Modify files in `frontend/src/components/`

### Terminal UI

**Colors** - Edit `src/tui.py` styles:
```python
console.print("[your_color]Text[/your_color]")
```

**Menu Options** - Modify `show_menu()` method
**Commands** - Add cases in `run()` method

---

## 🐛 Troubleshooting

### Web Dashboard

**Port 3000 already in use**
```bash
# Change port in frontend/vite.config.ts
server: { port: 3001 }
```

**API connection refused**
- Ensure backend is running on port 8000
- Check VITE_API_URL in .env file
- Verify no firewall blocking

**WebSocket disconnected**
- Check backend WebSocket endpoint is running
- Verify WS URL in configuration
- Look for CORS issues in browser console

### Terminal UI

**Import errors**
```bash
pip install rich
```

**Display issues**
- Ensure terminal supports 256 colors
- Try a different terminal emulator
- Check TERM environment variable

**Slow performance**
- Reduce status update frequency
- Limit number of displayed migrations
- Check database connection latency

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Main README**: ../README.md
- **Frontend README**: ../frontend/README.md
- **GitHub Issues**: [Report bugs here]

---

For questions or issues, consult the main project documentation or open an issue on GitHub.
