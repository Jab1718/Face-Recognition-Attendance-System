MODERN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #f4f7f6;
    --surface: #ffffff;
    --border: #e2e8f0;
    --text: #0f172a;
    --text-secondary: #475569;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --success: #059669;
    --danger: #dc2626;
    --radius: 16px;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* Base & Typography */
.stApp {
    background-color: var(--bg);
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--text);
}

h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
    color: var(--text) !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em;
}

p, .stCaption, [data-testid="stCaptionContainer"] {
    color: var(--text-secondary) !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    box-shadow: var(--shadow-md);
    border-right: 1px solid var(--border);
}

/* Camera Placeholder (Glassmorphism feel) */
.cam-placeholder {
    aspect-ratio: 16 / 9;
    max-height: 420px;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 2px dashed #cbd5e1;
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    text-align: center;
    padding: 2rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.cam-placeholder:hover {
    border-color: var(--accent);
    background: #eff6ff;
}

/* Live Feed Camera Input */
[data-testid="stCameraInput"] {
    width: 100%;
    border-radius: var(--radius);
    overflow: hidden;
    border: 3px solid var(--surface);
    box-shadow: var(--shadow-lg);
    margin-bottom: 0.75rem;
}

/* User Table Restyling */
.user-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    background: var(--surface);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border);
}
.user-table th {
    background: #f8fafc;
    color: var(--text-secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 16px;
    text-align: left;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
}
.user-table td {
    padding: 16px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    font-weight: 500;
    transition: background 0.2s ease;
}
.user-table tr:hover td {
    background: #f1f5f9;
}
.user-table tr:last-child td {
    border-bottom: none;
}

/* Primary Buttons with Hover Animations */
.stButton > button[kind="primary"],
[data-testid="stCameraInputButton"] {
    background: var(--accent) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    box-shadow: var(--shadow-md) !important;
    transition: all 0.2s ease-in-out !important;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stCameraInputButton"]:hover {
    background: var(--accent-hover) !important;
    box-shadow: var(--shadow-lg) !important;
    transform: translateY(-2px);
}
.stButton > button[kind="primary"] * {
    color: #ffffff !important;
}

/* Secondary Buttons */
.stButton > button[kind="secondary"] {
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    background: var(--surface) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--text-secondary) !important;
    background: #f8fafc !important;
}

/* Badges & Status */
.status-stable::before { background: var(--success); }
.status-needs_update::before { background: #eab308; }
.status-error::before { background: var(--danger); }

/* Dialog / Modal Styling */
div[data-testid="stDialog"] {
    background: var(--surface) !important;
    border-radius: var(--radius) !important;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
    border: none !important;
}
</style>
"""