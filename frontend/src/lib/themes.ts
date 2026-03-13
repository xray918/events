export interface EventTheme {
  id: string;
  name: string;
  gradient: string;
  pattern?: string;
  textColor: "white" | "dark";
  accentColor: string;
}

function svgPattern(svg: string): string {
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

const wave = (color: string) =>
  `<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg"><path d="M0 80c40-20 60 20 100 0s60-20 100 0v120H0z" fill="${color}" opacity="0.15"/><path d="M0 120c40-15 60 15 100 0s60-15 100 0v80H0z" fill="${color}" opacity="0.1"/></svg>`;

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _circles = (color: string) =>
  `<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="8" fill="${color}" opacity="0.12"/><circle cx="70" cy="50" r="5" fill="${color}" opacity="0.08"/><circle cx="40" cy="80" r="10" fill="${color}" opacity="0.1"/><circle cx="85" cy="15" r="6" fill="${color}" opacity="0.09"/></svg>`;

const dots = (color: string) =>
  `<svg width="60" height="60" xmlns="http://www.w3.org/2000/svg"><circle cx="10" cy="10" r="2" fill="${color}" opacity="0.2"/><circle cx="30" cy="30" r="2" fill="${color}" opacity="0.2"/><circle cx="50" cy="50" r="2" fill="${color}" opacity="0.2"/><circle cx="50" cy="10" r="1.5" fill="${color}" opacity="0.15"/><circle cx="10" cy="50" r="1.5" fill="${color}" opacity="0.15"/></svg>`;

const geo = (color: string) =>
  `<svg width="120" height="120" xmlns="http://www.w3.org/2000/svg"><line x1="0" y1="40" x2="120" y2="40" stroke="${color}" stroke-width="0.5" opacity="0.15"/><line x1="0" y1="80" x2="120" y2="80" stroke="${color}" stroke-width="0.5" opacity="0.15"/><line x1="40" y1="0" x2="40" y2="120" stroke="${color}" stroke-width="0.5" opacity="0.15"/><line x1="80" y1="0" x2="80" y2="120" stroke="${color}" stroke-width="0.5" opacity="0.15"/><rect x="35" y="35" width="10" height="10" fill="none" stroke="${color}" stroke-width="0.5" opacity="0.12"/></svg>`;

const stars = (color: string) =>
  `<svg width="150" height="150" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="30" r="1" fill="${color}" opacity="0.6"/><circle cx="60" cy="15" r="1.5" fill="${color}" opacity="0.4"/><circle cx="100" cy="45" r="1" fill="${color}" opacity="0.5"/><circle cx="130" cy="20" r="0.8" fill="${color}" opacity="0.3"/><circle cx="45" cy="70" r="1.2" fill="${color}" opacity="0.5"/><circle cx="110" cy="80" r="0.8" fill="${color}" opacity="0.4"/><circle cx="25" cy="110" r="1" fill="${color}" opacity="0.3"/><circle cx="80" cy="100" r="1.5" fill="${color}" opacity="0.6"/><circle cx="140" cy="130" r="1" fill="${color}" opacity="0.35"/><circle cx="70" cy="140" r="0.8" fill="${color}" opacity="0.45"/></svg>`;

const petals = (color: string) =>
  `<svg width="120" height="120" xmlns="http://www.w3.org/2000/svg"><ellipse cx="30" cy="30" rx="8" ry="4" transform="rotate(30 30 30)" fill="${color}" opacity="0.12"/><ellipse cx="80" cy="50" rx="6" ry="3" transform="rotate(-20 80 50)" fill="${color}" opacity="0.1"/><ellipse cx="50" cy="90" rx="7" ry="3.5" transform="rotate(45 50 90)" fill="${color}" opacity="0.11"/><ellipse cx="110" cy="20" rx="5" ry="2.5" transform="rotate(15 110 20)" fill="${color}" opacity="0.09"/></svg>`;

const inkSplash = () =>
  `<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg"><path d="M40 60c10-30 50-20 60 0s30 40 10 50-60 10-70-20z" fill="#000" opacity="0.06"/><path d="M120 30c15 5 20 30 5 40s-30 10-25-15 10-30 20-25z" fill="#000" opacity="0.04"/><circle cx="160" cy="150" r="20" fill="#000" opacity="0.03"/></svg>`;

const flame = (color: string) =>
  `<svg width="160" height="160" xmlns="http://www.w3.org/2000/svg"><path d="M40 140c0-30 15-50 20-70s-5-30 10-50c10 25 25 35 20 60s15 30 10 60z" fill="${color}" opacity="0.1"/><path d="M90 140c0-20 10-35 15-55s-3-25 8-40c8 18 18 25 14 45s10 25 7 50z" fill="${color}" opacity="0.08"/></svg>`;

const crystal = (color: string) =>
  `<svg width="120" height="120" xmlns="http://www.w3.org/2000/svg"><polygon points="30,10 45,35 15,35" fill="none" stroke="${color}" stroke-width="0.6" opacity="0.15"/><polygon points="70,50 90,80 50,80" fill="none" stroke="${color}" stroke-width="0.6" opacity="0.12"/><polygon points="100,5 115,30 85,30" fill="none" stroke="${color}" stroke-width="0.5" opacity="0.1"/><line x1="30" y1="35" x2="70" y2="50" stroke="${color}" stroke-width="0.3" opacity="0.08"/></svg>`;

const mountain = (color: string) =>
  `<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg"><path d="M0 100 L40 40 L70 70 L110 20 L150 60 L200 30 L200 100z" fill="${color}" opacity="0.12"/><path d="M0 100 L60 55 L100 80 L160 45 L200 65 L200 100z" fill="${color}" opacity="0.08"/></svg>`;

export const EVENT_THEMES: EventTheme[] = [
  {
    id: "aurora",
    name: "极光",
    gradient: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    pattern: svgPattern(wave("#fff")),
    textColor: "white",
    accentColor: "#667eea",
  },
  {
    id: "sunset",
    name: "日落",
    gradient: "linear-gradient(135deg, #f6844a 0%, #ee5a84 50%, #b04386 100%)",
    pattern: svgPattern(mountain("#fff")),
    textColor: "white",
    accentColor: "#ee5a84",
  },
  {
    id: "ocean",
    name: "深海",
    gradient: "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)",
    pattern: svgPattern(wave("#4fc3f7")),
    textColor: "white",
    accentColor: "#4fc3f7",
  },
  {
    id: "forest",
    name: "森林",
    gradient: "linear-gradient(135deg, #134e5e 0%, #71b280 100%)",
    pattern: svgPattern(petals("#fff")),
    textColor: "white",
    accentColor: "#71b280",
  },
  {
    id: "neon",
    name: "霓虹",
    gradient: "linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%)",
    pattern: svgPattern(geo("#00f5d4")),
    textColor: "white",
    accentColor: "#00f5d4",
  },
  {
    id: "minimal",
    name: "极简",
    gradient: "linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)",
    pattern: svgPattern(geo("#94a3b8")),
    textColor: "dark",
    accentColor: "#475569",
  },
  {
    id: "warm",
    name: "暖阳",
    gradient: "linear-gradient(135deg, #f7971e 0%, #ffd200 100%)",
    pattern: svgPattern(dots("#fff")),
    textColor: "dark",
    accentColor: "#f7971e",
  },
  {
    id: "cosmic",
    name: "星空",
    gradient: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
    pattern: svgPattern(stars("#fff")),
    textColor: "white",
    accentColor: "#a78bfa",
  },
  {
    id: "cherry",
    name: "樱花",
    gradient: "linear-gradient(135deg, #fbc2eb 0%, #f8a4c8 50%, #a6c1ee 100%)",
    pattern: svgPattern(petals("#fff")),
    textColor: "dark",
    accentColor: "#ec4899",
  },
  {
    id: "ink",
    name: "水墨",
    gradient: "linear-gradient(135deg, #2c3e50 0%, #bdc3c7 100%)",
    pattern: svgPattern(inkSplash()),
    textColor: "white",
    accentColor: "#64748b",
  },
  {
    id: "fire",
    name: "烈焰",
    gradient: "linear-gradient(135deg, #cb2d3e 0%, #ef473a 50%, #f7971e 100%)",
    pattern: svgPattern(flame("#fff")),
    textColor: "white",
    accentColor: "#ef473a",
  },
  {
    id: "arctic",
    name: "冰川",
    gradient: "linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 50%, #80deea 100%)",
    pattern: svgPattern(crystal("#0097a7")),
    textColor: "dark",
    accentColor: "#0097a7",
  },
];

export function getThemeById(id: string): EventTheme | undefined {
  return EVENT_THEMES.find((t) => t.id === id);
}

export function getThemeByIndex(index: number): EventTheme {
  return EVENT_THEMES[index % EVENT_THEMES.length];
}

export function getThemeForEvent(event: {
  id: string;
  theme?: Record<string, unknown> | null;
}): EventTheme {
  if (event.theme && typeof event.theme.preset === "string") {
    const found = getThemeById(event.theme.preset);
    if (found) return found;
  }
  const idx =
    parseInt(event.id.replace(/-/g, "").slice(0, 8), 16) % EVENT_THEMES.length;
  return EVENT_THEMES[idx];
}

export function getThemeCoverStyle(theme: EventTheme): React.CSSProperties {
  const bg = theme.pattern
    ? `${theme.pattern}, ${theme.gradient}`
    : theme.gradient;
  return { background: bg };
}

export function getCoverStyle(event: {
  id: string;
  cover_image_url?: string | null;
  theme?: Record<string, unknown> | null;
}): React.CSSProperties {
  const theme = getThemeForEvent(event);
  const themeBg = getThemeCoverStyle(theme).background as string;

  if (event.cover_image_url) {
    return {
      background: `url("${event.cover_image_url}") center/cover no-repeat, ${themeBg}`,
    };
  }
  return { background: themeBg };
}
