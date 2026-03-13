"use client";

import { EVENT_THEMES, getThemeCoverStyle } from "@/lib/themes";

interface ThemePickerProps {
  value: string;
  onChange: (themeId: string) => void;
  disabled?: boolean;
}

export function ThemePicker({ value, onChange, disabled }: ThemePickerProps) {
  return (
    <div className={disabled ? "opacity-40 pointer-events-none" : ""}>
      <p className="text-sm font-medium mb-2">
        {disabled ? "已上传封面图，主题不生效" : "或选择预设主题"}
      </p>
      <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
        {EVENT_THEMES.map((theme) => {
          const selected = value === theme.id;
          return (
            <button
              key={theme.id}
              type="button"
              onClick={() => onChange(selected ? "" : theme.id)}
              className={`
                group relative h-16 rounded-lg overflow-hidden transition-all
                ${selected ? "ring-2 ring-primary ring-offset-2" : "ring-1 ring-border hover:ring-primary/50"}
              `}
              style={getThemeCoverStyle(theme)}
              title={theme.name}
            >
              <span
                className={`
                  absolute inset-0 flex items-center justify-center text-xs font-medium
                  ${theme.textColor === "white" ? "text-white" : "text-gray-800"}
                `}
              >
                {theme.name}
              </span>
              {selected && (
                <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground">
                  ✓
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
