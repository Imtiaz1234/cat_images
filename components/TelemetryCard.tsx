import type { GeneratorSnapshot, NodeStatus } from "@/lib/telemetry";

const STATUS_STYLES: Record<NodeStatus, string> = {
  online: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/30",
  degraded: "bg-amber-500/15 text-amber-300 ring-amber-400/30",
  offline: "bg-rose-500/15 text-rose-300 ring-rose-400/30",
  critical: "bg-red-500/25 text-red-100 ring-red-300/70",
};

const STATUS_DOT: Record<NodeStatus, string> = {
  online: "bg-emerald-400",
  degraded: "bg-amber-400",
  offline: "bg-rose-400",
  critical: "bg-red-200",
};

function formatNumber(value: number, digits: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function TelemetryCard({ generator }: { generator: GeneratorSnapshot }) {
  const isCritical = generator.nodeStatus === "critical";

  return (
    <article
      className={
        isCritical
          ? "telemetry-card-critical rounded-xl border p-5 text-red-50"
          : "rounded-xl border border-white/10 bg-slate-900/70 p-5 shadow-lg shadow-black/20 backdrop-blur"
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p
            className={`font-mono text-xs tracking-wide ${
              isCritical ? "text-red-200/80" : "text-slate-400"
            }`}
          >
            {generator.generatorId}
          </p>
          <h2
            className={`mt-1 text-lg font-semibold ${
              isCritical ? "text-white" : "text-slate-50"
            }`}
          >
            {generator.name}
          </h2>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium capitalize ring-1 ${STATUS_STYLES[generator.nodeStatus]}`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[generator.nodeStatus]}`}
            aria-hidden
          />
          {generator.nodeStatus}
        </span>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-5">
        <div>
          <dt
            className={`text-xs uppercase tracking-wider ${
              isCritical ? "text-red-200/80" : "text-slate-400"
            }`}
          >
            Active load
          </dt>
          <dd
            className={`mt-2 flex flex-wrap items-baseline gap-x-2 font-mono text-[clamp(2.75rem,5vw,4.5rem)] font-semibold leading-none tracking-tight tabular-nums ${
              isCritical ? "text-white" : "text-slate-50"
            }`}
          >
            {formatNumber(generator.loadMw, 1)}
            <span
              className={`text-xl font-normal ${
                isCritical ? "text-red-100/80" : "text-slate-400"
              }`}
            >
              MW
            </span>
          </dd>
        </div>
        <div>
          <dt
            className={`text-xs uppercase tracking-wider ${
              isCritical ? "text-red-200/80" : "text-slate-400"
            }`}
          >
            Voltage
          </dt>
          <dd
            className={`mt-2 flex flex-wrap items-baseline gap-x-2 font-mono text-[clamp(2.75rem,5vw,4.5rem)] font-semibold leading-none tracking-tight tabular-nums ${
              isCritical ? "text-white" : "text-slate-50"
            }`}
          >
            {formatNumber(generator.voltageKv, 2)}
            <span
              className={`text-xl font-normal ${
                isCritical ? "text-red-100/80" : "text-slate-400"
              }`}
            >
              kV
            </span>
          </dd>
        </div>
      </dl>

      <p
        className={`mt-5 font-mono text-xs ${
          isCritical ? "text-red-200/70" : "text-slate-500"
        }`}
      >
        Sample {generator.timestamp}
      </p>
    </article>
  );
}
