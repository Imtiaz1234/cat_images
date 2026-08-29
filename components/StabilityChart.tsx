"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StabilityPoint } from "@/lib/telemetry";

export function StabilityChart({ series }: { series: StabilityPoint[] }) {
  return (
    <section className="rounded-xl border border-white/10 bg-slate-900/70 p-5 shadow-lg shadow-black/20 backdrop-blur">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-50">
            System stability
          </h2>
          <p className="text-sm text-slate-400">
            Grid frequency (Hz) replayed from the mock telemetry stream
          </p>
        </div>
        <p className="font-mono text-xs text-slate-500">Target 60.000 Hz</p>
      </div>

      <div className="h-72 w-full">
        {series.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Waiting for frequency samples…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.15)" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: "#94a3b8", fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: "rgba(148,163,184,0.25)" }}
              />
              <YAxis
                domain={[59.9, 60.1]}
                tick={{ fill: "#94a3b8", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value: number) => value.toFixed(2)}
                width={48}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid rgba(148,163,184,0.25)",
                  borderRadius: 8,
                  color: "#e2e8f0",
                }}
                formatter={(value) => {
                  const hz = typeof value === "number" ? value.toFixed(3) : String(value);
                  return [`${hz} Hz`, "Frequency"];
                }}
              />
              <ReferenceArea y1={59.95} y2={60.05} fill="#22c55e" fillOpacity={0.08} />
              <Line
                type="monotone"
                dataKey="frequencyHz"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
