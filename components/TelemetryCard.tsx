import type { GeneratorSnapshot, NodeStatus } from "@/lib/telemetry";

const STATUS_STYLES: Record<NodeStatus, string> = {
  online: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/30",
  degraded: "bg-amber-500/15 text-amber-300 ring-amber-400/30",
  offline: "bg-rose-500/15 text-rose-300 ring-rose-400/30",
};

const STATUS_DOT: Record<NodeStatus, string> = {
  online: "bg-emerald-400",
  degraded: "bg-amber-400",
  offline: "bg-rose-400",
};

function formatNumber(value: number, digits: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function TelemetryCard({ generator }: { generator: GeneratorSnapshot }) {
  return (
    <article className="rounded-xl border border-white/10 bg-slate-900/70 p-5 shadow-lg shadow-black/20 backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs tracking-wide text-slate-400">
            {generator.generatorId}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-50">
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

      <dl className="mt-5 grid grid-cols-2 gap-4">
        <div>
          <dt className="text-xs uppercase tracking-wider text-slate-400">
            Active load
          </dt>
          <dd className="mt-1 font-mono text-2xl font-semibold tabular-nums text-slate-50">
            {formatNumber(generator.loadMw, 1)}
            <span className="ml-1 text-sm font-normal text-slate-400">MW</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wider text-slate-400">
            Voltage
          </dt>
          <dd className="mt-1 font-mono text-2xl font-semibold tabular-nums text-slate-50">
            {formatNumber(generator.voltageKv, 2)}
            <span className="ml-1 text-sm font-normal text-slate-400">kV</span>
          </dd>
        </div>
      </dl>

      <p className="mt-4 font-mono text-xs text-slate-500">
        Sample {generator.timestamp}
      </p>
    </article>
  );
}
