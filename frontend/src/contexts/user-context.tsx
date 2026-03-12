"use client";

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface User {
  id: string;
  nickname: string | null;
  avatar_url: string | null;
  phone: string | null;
  email: string | null;
}

interface UserContextType {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const UserContext = createContext<UserContextType>({
  user: null,
  loading: true,
  refresh: async () => {},
  logout: async () => {},
});

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const retryRef = useRef<ReturnType<typeof setTimeout>>();

  const refresh = async () => {
    try {
      const res = await fetch(`${API}/api/v1/auth/me`, { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setUser(data.data ?? null);
      } else if (res.status === 401 || res.status === 403) {
        setUser(null);
      } else {
        if (!retryRef.current) {
          retryRef.current = setTimeout(() => {
            retryRef.current = undefined;
            refresh();
          }, 3000);
        }
      }
    } catch {
      if (!retryRef.current) {
        retryRef.current = setTimeout(() => {
          retryRef.current = undefined;
          refresh();
        }, 3000);
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await fetch(`${API}/api/v1/auth/logout`, { method: "POST", credentials: "include" });
    } catch {
      // ignore
    } finally {
      setUser(null);
    }
  };

  useEffect(() => {
    refresh();
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <UserContext.Provider value={{ user, loading, refresh, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
