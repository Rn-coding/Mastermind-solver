# Architectural Design & Reasoning: Dynamic Interactive Terminal UI (TUI)

## 1. Context & Objective
The requirement for Feature 2 is to transform the terminal interface from a sequential scrolling CLI into a **dynamic, full-screen, in-place reactive TUI** with:
1. **Single Board Render**: The game board occupies fixed coordinates on the screen and updates in-place after every turn rather than printing a new table below the old one.
2. **Keyboard & Mouse Interaction**: Users can click pegs or buttons on screen, select colors with the mouse or arrow keys, click turns in history to inspect past decisions, and trigger AI hints/evaluations with keyboard shortcuts or buttons.

---

## 2. Evaluation of Implementation Approaches

### Approach A: `rich.live.Live` with Manual Input Polling & ANSI Mouse Tracking
- **How it works**:
  - `rich.console.Console(screen=True)` enters the terminal's **Alternate Screen Buffer** (preventing scroll clutter).
  - `rich.live.Live(renderable, refresh_per_second=15, screen=True)` updates the UI in-place whenever application state changes.
  - Keyboard/Mouse handling: Python's standard `sys.stdin` operates in line-buffered mode. To capture single keypresses (arrows, Enter, Esc) and mouse clicks on Windows without blocking:
    - On Windows: Use `msvcrt.kbhit()` and `msvcrt.getwch()` for keyboard events, and enable `ENABLE_MOUSE_INPUT` via `ctypes.windll.kernel32.SetConsoleMode`.
    - Alternatively: Use `prompt_toolkit.input.create_input()` which normalizes ANSI mouse escape sequences (`\x1b[<0;x;yM` for left click) across Windows and Unix.
- **Strengths**: Zero new dependencies beyond what we already have (`rich` and `prompt_toolkit` are already in the project).
- **Weaknesses**: Requires writing custom low-level hit-testing logic (e.g. mapping `(x, y)` mouse coordinates to peg widgets or buttons).

### Approach B: `Textual` (Recommended for Full Production TUI)
- **How it works**:
  - `Textual` is the official TUI application framework developed by the creators of `Rich`.
  - Built specifically for reactive, component-based terminal applications with first-class mouse support, click events (`on_button_pressed`, `on_click`), keybindings (`BINDINGS = [("h", "hint"), ("e", "eval")]`), and CSS-like styling (`TCSS`).
- **Strengths**:
  - Native cross-platform mouse support (hover states, clickable color palettes, drag-and-drop or click-to-place pegs).
  - Reactive state (`reactive[int]`): Changing `turn_number` or `selected_color` automatically updates only the dependent UI components.
  - Built-in layout containers: `Horizontal`, `Vertical`, `TabbedContent`, `ModalScreen` for popups (e.g. partition distribution viewer).
- **Weaknesses**: Introduces `textual` dependency.

---

## 3. Recommended Widget Architecture for Mastermind TUI

```text
+-----------------------------------------------------------------------------------+
| MASTERMIND AI -- Dynamic Reactive Dashboard                      [?] Help  [Q] Exit|
+-------------------------------------------------+---------------------------------+
| GAME BOARD (Fixed In-Place View)                | AI REASONING & TELEMETRY PANEL  |
|                                                 |                                 |
| Turn 01: [● R] [● G] [● B] [● Y]  ●● ○ · (1, 1) | Active Method: Anytime Entropy  |
| Turn 02: [● O] [● P] [● R] [● G]  ● · · · (1, 0) | Candidates: 32 / 1,296          |
| Turn 03: [● ·] [● ·] [● ·] [● ·]  (Current Turn)| Latency: 12.4 ms | Depth: 1 ply  |
| ...                                             | Current Entropy: 2.14 bits      |
+-------------------------------------------------+---------------------------------+
| COLOR PALETTE SELECTOR (Clickable / Keys 0-5)   | INTERACTIVE INSPECTION TABS     |
| [ 0:Red ] [ 1:Green ] [ 2:Blue ] [ 3:Yellow ]   | [Partitions] [Candidates] [Eval]|
| [ 4:Orange ] [ 5:Purple ]                       | ------------------------------- |
+-------------------------------------------------| Frequency Distribution Bar Chart|
| CONTROLS: [Submit Guess] [AI Hint] [Auto AI]    | (exact=1, mis=1): 18 (56.2%) ███|
+-------------------------------------------------+---------------------------------+
```

### Component Breakdown
1. **`GameBoardWidget`**:
   - Displays history of turns.
   - Clicking an old turn opens the detailed feedback partition analysis for that guess.
2. **`PegInputWidget`**:
   - Interactive slots for the current turn.
   - Clicking a slot activates it; clicking a color from `ColorPaletteWidget` assigns that color.
   - Keyboard navigation: Arrow keys move between peg slots; typing number (`0-5`) or letter (`R, G, B...`) fills the slot.
3. **`TelemetryPanelWidget`**:
   - Updates asynchronously while search executes.
   - Shows live progress bar when AI searches across larger state spaces.
4. **`DistributionTabWidget`**:
   - Interactive bar chart showing partition frequencies for the selected or suggested guess.

---

## 4. Implementation Steps for Feature 2
1. **Event Dispatcher**:
   Create `src/mastermind/ui/tui.py` implementing the screen loop.
2. **State Store (`GameState`)**:
   Hold active `MastermindEnvironment`, `BeliefState`, `selected_pegs`, and `active_tab`.
3. **In-Place Update Cycle**:
   Trigger `render()` only upon input events (keypress, click, or turn completion), eliminating terminal flicker and redrawing within $< 16$ ms.
