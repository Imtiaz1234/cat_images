"use client";

import { StabilityChart } from "@/components/StabilityChart";
import { TelemetryGrid } from "@/components/TelemetryGrid";
import { useTelemetryStream } from "@/hooks/useTelemetryStream";

export function Dashboard() {
  const { generators, stabilitySeries, connected, loading, error } =
    useTelemetryStream();

  return (
    <div className="flex flex-1 flex-col bg-slate-950 text-slate-100">
      <header className="border-b border-white/10 px-4 py-5 sm:px-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-sky-400">
              telemetry-dash
            </p>
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Electrical telemetry
            </h1>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span
              className={`h-2 w-2 rounded-full ${
                connected ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-slate-500"
              }`}
              aria-hidden
            />
            <span className="font-mono text-slate-300">
              {error
                ? "Stream error"
                : loading
                  ? "Connecting"
                  : connected
                    ? "Live mock stream"
                    : "Disconnected"}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 sm:px-8">
        {error ? (
          <p
            role="alert"
            className="rounded-xl border border-rose-500/30 bg-rose-950/40 px-4 py-3 text-sm text-rose-200"
          >
            {error}
          </p>
        ) : null}

        <TelemetryGrid generators={generators} loading={loading} />
        <StabilityChart series={stabilitySeries} />
      </main>
    </div>
  );
}
