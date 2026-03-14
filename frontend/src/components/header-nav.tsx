"use client";

import { useUser } from "@/contexts/user-context";

function shortName(nickname: string | null): string {
  if (!nickname) return "我";
  // 手机号自动生成的昵称"用户XXXX" → 只显示"XXXX"
  if (/^用户\d+$/.test(nickname)) return nickname.slice(2);
  return nickname.length > 10 ? nickname.slice(0, 10) + "…" : nickname;
}

export function HeaderNav() {
  const { user, loading, logout } = useUser();

  if (loading) {
    return <div className="h-8 w-16 animate-pulse rounded bg-muted" />;
  }

  if (!user) {
    return (
      <nav className="flex items-center gap-4 text-sm">
        <a
          href="/login"
          className="rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          登录
        </a>
      </nav>
    );
  }

  return (
    <nav className="flex items-center gap-4 text-sm">
      <a href="/my" className="text-muted-foreground hover:text-foreground transition-colors">
        我的活动
      </a>
      <a href="/create" className="text-muted-foreground hover:text-foreground transition-colors">
        创建活动
      </a>
      <div className="flex items-center gap-2">
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt=""
            className="h-7 w-7 rounded-full"
          />
        ) : (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
            {(user.nickname || "U")[0]}
          </div>
        )}
        <span className="hidden text-sm sm:inline">{shortName(user.nickname)}</span>
        <button
          onClick={logout}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          退出
        </button>
      </div>
    </nav>
  );
}
