import { NavLink, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { api } from "../api/client";

export function Layout() {
  const queryClient = useQueryClient();
  const { data: meta } = useQuery({
    queryKey: ["meta"],
    queryFn: api.meta,
    refetchInterval: (query) =>
      (query.state.data?.auto_refresh_seconds ?? 60) * 1000,
  });

  const refreshAll = () => {
    void queryClient.invalidateQueries();
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="topbar">
        <div className="flex min-w-0 items-center gap-3">
          <h1 className="truncate text-[1.3rem] font-bold text-white">
            Fraud Analytics Dashboard
          </h1>
        </div>

        <nav className="flex shrink-0 gap-1.5">
          <NavTab to="/" end>
            General Overview
          </NavTab>
          <NavTab to="/velocity">Velocity Deep-Dive</NavTab>
        </nav>

        <button
          type="button"
          onClick={refreshAll}
          className="ml-2 inline-flex shrink-0 items-center gap-1.5 rounded-card bg-white/15 px-3 py-1.5 text-[0.75rem] font-semibold text-white transition hover:bg-white/25"
          title="Reload all dashboard data"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Reload</span>
        </button>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-end gap-3 border-b border-surface-border bg-white px-4 py-1.5 text-[10px] text-ink-muted">
          <span>Auto-refresh every {meta?.auto_refresh_seconds ?? 60}s</span>
          <span className="hidden truncate sm:inline">
            Fingerprint: {meta?.fingerprint ?? "waiting for marts…"}
          </span>
        </div>

        <main className="flex-1 overflow-y-auto bg-surface p-3.5">
          <div className="mx-auto max-w-[1600px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

function NavTab({
  to,
  end,
  children,
}: {
  to: string;
  end?: boolean;
  children: ReactNode;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) => clsx("nav-tab whitespace-nowrap", isActive && "nav-tab-active")}
    >
      {children}
    </NavLink>
  );
}
