# Consolidated User Feedback - 15 Jan 2026

Feedback from: Abhishek, Jay

---

## Frontend / UI

### Layout & Responsiveness
- [ ] **Resizable panels** - Add sliders to adjust sidebar, analytics panel, and session viewer widths (Jay)
- [ ] **Remember dashboard state** - Persist collapsed/minimized state across sessions (Jay)
- [ ] **Logo click** - Should navigate to quickcall.dev website (Jay)

### Dark Mode
- [ ] **Reduce contrast** - Use greyish background instead of pitch black (Jay)
- [ ] **Soften colors** - Dark mode colors should not pop/be too vibrant (Jay)

### Analytics Panel
- [ ] **Add session title** - Display the session name from sidebar in analytics to clarify it's session-specific, not global (Jay)
- [ ] **Session usage display** - Show realtime session usage in analytics dashboard (Jay)
- [ ] **Planning highlight toggle** - Add toggle to highlight when planning was done in the session (Jay)
- [ ] **Click-to-jump hint** - Show tooltip/hint while scrolling that clicking on prompt index in token chart jumps to that prompt (Jay)

### Session View
- [ ] **Search in chat** - Enable searching within a conversation/session (Jay)
- [ ] **Better plan visualization** - Improved way to view plans done in session viewer (Jay)

---

## Backend / Ingestion

### Real-time Updates
- [ ] **Near realtime polling** - Current 120s interval feels glitchy; users expect near-instant updates (Jay)
  - Consider: WebSocket push on file change detection, reduce poll interval, or use file watchers
- [ ] **Instant refresh** - Useful for viewing ongoing conversations when CC auto-scrolls (Jay)

### Data Retention
- [ ] **Backup button** - CC has 30-day limit; offer local backup option in UI (Abhishek)

---

## Metrics System

### New Metrics
- [ ] **Off-hours computation** - Calculate weekly metrics during off hours to avoid token usage blocking (Abhishek)

---

## AI-Powered Features (New)

### Prompt Analysis
- [ ] **Weekly analysis** - Analyze how user's week was with CC (Abhishek)
- [ ] **Prompt quality feedback** - Are you being specific? Detailed enough? (Abhishek)
- [ ] **Introspect button** - Where did I go wrong? Where did Claude make mistakes? How to improve? (Jay)

### Intent Capture
- [ ] **Tag conversations by intent** - Extract user prompts, identify 2-3 intent blurbs to summarize session (Abhishek)

### Skills Identification
- [ ] **Identify repetitive tasks** - Suggest skills for common patterns (Abhishek)
- [ ] **Shared team skills** - Support for org-wide skill repos (e.g., React skills) (Abhishek)

---

## Enterprise Features (New)

### Org Insights
- [ ] **Best/worst prompt engineers** - Identify top and bottom performers in org (Abhishek)
- [ ] **Gap analysis** - What skills gap exists? How to bridge it? (Abhishek)

---

## Infrastructure

### Telemetry
- [ ] **Add usage telemetry** - Track installs and events (Abhishek)
- [ ] **Opt-in/out during onboarding** - Let users choose telemetry preference (Abhishek)

### Distribution
- [ ] **Simplified install** - `curl something | sh` that auto-updates shell config (zshrc/bashrc) (Jay)
- [ ] **Auto-update PATH** - Reduce friction for lazy devs (Jay)

---

## User Settings (New)

- [ ] **Profile section** - User profile management (Abhishek)
- [ ] **Settings section** - App configuration (Abhishek)
- [ ] **Custom backup location** - Let users choose where to backup chats (Abhishek)

---

## Positive Feedback

- Learning curve is close to 0 - intuitive UI (Jay)
- Primary usecase of referring ongoing chats is already useful without metrics (Jay)
- Curiosity will drive learning of the product (Jay)

---

## User Tips (from Abhishek)

- Having task-specific CC sessions is very helpful
- Keep separate sessions for: planning, backend, frontend

---

## Priority Suggestions

### High Priority (Core UX)
1. Near realtime updates (polling/WebSocket improvement)
2. Search in chat
3. Dark mode contrast fix
4. Session title in analytics panel
5. Resizable panels

### Medium Priority (Polish)
1. Remember dashboard state
2. Logo click navigation
3. Simplified curl install
4. Backup button for 30-day limit

### Future / Exploration
1. AI-powered prompt analysis and introspection
2. Intent capture and tagging
3. Enterprise insights
4. Skills identification
