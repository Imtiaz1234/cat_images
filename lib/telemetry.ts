export type NodeStatus = "online" | "degraded" | "offline" | "critical";

export type TelemetryRow = {
  timestamp: string;
  generatorId: string;
  name: string;
  loadMw: number;
  voltageKv: number;
  nodeStatus: NodeStatus;
  frequencyHz: number;
};

export type GeneratorSnapshot = {
  generatorId: string;
  name: string;
  loadMw: number;
  voltageKv: number;
  nodeStatus: NodeStatus;
  timestamp: string;
};

export type StabilityPoint = {
  time: string;
  frequencyHz: number;
};

const NODE_STATUSES = new Set<NodeStatus>([
  "online",
  "degraded",
  "offline",
  "critical",
]);

function isNodeStatus(value: string): value is NodeStatus {
  return NODE_STATUSES.has(value as NodeStatus);
}

function parseNumber(value: string, field: string, line: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Invalid ${field} on line ${line}: "${value}"`);
  }
  return parsed;
}

export function parseTelemetryCsv(text: string): TelemetryRow[] {
  const lines = text.split(/\r?\n/);
  const rows: TelemetryRow[] = [];

  for (let i = 0; i < lines.length; i += 1) {
    const raw = lines[i]?.trim();
    if (!raw) continue;
    if (i === 0 && raw.toLowerCase().startsWith("timestamp")) continue;

    const cols = raw.split(",");
    if (cols.length < 7) {
      throw new Error(`Expected 7 CSV columns on line ${i + 1}, got ${cols.length}`);
    }

    const [
      timestamp,
      generatorId,
      name,
      loadRaw,
      voltageRaw,
      statusRaw,
      frequencyRaw,
    ] = cols.map((col) => col.trim());

    if (!timestamp || !generatorId || !name) {
      throw new Error(`Missing required identity fields on line ${i + 1}`);
    }
    if (!isNodeStatus(statusRaw)) {
      throw new Error(`Invalid node_status on line ${i + 1}: "${statusRaw}"`);
    }

    rows.push({
      timestamp,
      generatorId,
      name,
      loadMw: parseNumber(loadRaw, "load_mw", i + 1),
      voltageKv: parseNumber(voltageRaw, "voltage_kv", i + 1),
      nodeStatus: statusRaw,
      frequencyHz: parseNumber(frequencyRaw, "frequency_hz", i + 1),
    });
  }

  if (rows.length === 0) {
    throw new Error("Telemetry CSV contained no data rows");
  }

  return rows;
}

export function latestGenerators(rows: TelemetryRow[]): GeneratorSnapshot[] {
  const latest = new Map<string, GeneratorSnapshot>();

  for (const row of rows) {
    latest.set(row.generatorId, {
      generatorId: row.generatorId,
      name: row.name,
      loadMw: row.loadMw,
      voltageKv: row.voltageKv,
      nodeStatus: row.nodeStatus,
      timestamp: row.timestamp,
    });
  }

  return Array.from(latest.values()).sort((a, b) =>
    a.generatorId.localeCompare(b.generatorId),
  );
}

export function toStabilitySeries(rows: TelemetryRow[]): StabilityPoint[] {
  const byTime = new Map<string, { sum: number; count: number }>();

  for (const row of rows) {
    const bucket = byTime.get(row.timestamp) ?? { sum: 0, count: 0 };
    bucket.sum += row.frequencyHz;
    bucket.count += 1;
    byTime.set(row.timestamp, bucket);
  }

  return Array.from(byTime.entries()).map(([time, { sum, count }]) => ({
    time,
    frequencyHz: Number((sum / count).toFixed(3)),
  }));
}
