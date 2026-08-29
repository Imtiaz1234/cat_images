import type { GeneratorSnapshot } from "@/lib/telemetry";
import { TelemetryCard } from "@/components/TelemetryCard";

export function TelemetryGrid({
  generators,
  loading,
}: {
  generators: GeneratorSnapshot[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <div
            key={index}
            className="h-44 animate-pulse rounded-xl border border-white/10 bg-slate-900/50"
          />
        ))}
      </div>
    );
  }

  if (generators.length === 0) {
    return (
      <p className="rounded-xl border border-white/10 bg-slate-900/50 px-4 py-8 text-center text-sm text-slate-400">
        No generator samples in the current telemetry window.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {generators.map((generator) => (
        <TelemetryCard key={generator.generatorId} generator={generator} />
      ))}
    </div>
  );
}
