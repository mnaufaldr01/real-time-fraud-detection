import { NavLink, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { Activity, LayoutDashboard, RefreshCw, Shield } from "lucide-react";
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
    <div className="min-h-screen lg:flex">
      <aside className="border-b border-surface-border bg-surface-raised/50 lg:fixed lg:inset-y-0 lg:w-64 lg:border-b-0 lg:border-r">
        <div className="flex h-full flex-col p-5">
          <div className="mb-8 flex items-center gap-3">
            <div className="rounded-xl bg-accent/15 p-2.5 text-accent">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <p className="font-display text-sm font-semibold text-white">Fraud Analytics</p>
              <p className="text-xs text-slate-500">dbt marts · Postgres</p>
            </div>
          </div>

          <nav className="space-y-1">
            <NavItem to="/" end icon={<LayoutDashboard className="h-4 w-4" />}>
              General Overview
            </NavItem>
            <NavItem to="/velocity" icon={<Activity className="h-4 w-4" />}>
              Velocity Deep-Dive
            </NavItem>
          </nav>

          <div className="mt-auto space-y-3 pt-8">
            <button
              type="button"
              onClick={refreshAll}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-border bg-slate-900/60 px-3 py-2 text-sm font-medium text-slate-200 transition hover:border-accent/50 hover:text-white"
            >
              <RefreshCw className="h-4 w-4" />
              Reload data
            </button>
            <div className="rounded-lg border border-surface-border/70 bg-slate-950/40 p-3 text-xs text-slate-500">
              <p>Auto-refresh every {meta?.auto_refresh_seconds ?? 60}s</p>
              <p className="mt-1 truncate">
                Fingerprint: {meta?.fingerprint ?? "waiting for marts…"}
              </p>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 lg:pl-64">
        <div className="mx-auto max-w-[1600px] px-4 py-4 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function NavItem({
  to,
  end,
  icon,
  children,
}: {
  to: string;
  end?: boolean;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        clsx(
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
          isActive
            ? "bg-accent/15 text-accent"
            : "text-slate-400 hover:bg-slate-800/60 hover:text-white",
        )
      }
    >
      {icon}
      {children}
    </NavLink>
  );
}
