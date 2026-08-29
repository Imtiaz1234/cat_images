"use client";

import { useEffect, useMemo, useState } from "react";
import {
  latestGenerators,
  parseTelemetryCsv,
  toStabilitySeries,
  type GeneratorSnapshot,
  type StabilityPoint,
  type TelemetryRow,
} from "@/lib/telemetry";

const TELEMETRY_CSV_URL = "/data/telemetry.csv";
const TICK_MS = 1000;
const STABILITY_WINDOW = 16;

type StreamState = {
  generators: GeneratorSnapshot[];
  stabilitySeries: StabilityPoint[];
  connected: boolean;
  loading: boolean;
  error: string | null;
};

export function useTelemetryStream(): StreamState {
  const [rows, setRows] = useState<TelemetryRow[]>([]);
  const [cursor, setCursor] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function loadCsv() {
      try {
        const response = await fetch(TELEMETRY_CSV_URL, {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`Failed to load telemetry CSV (${response.status})`);
        }
        const text = await response.text();
        const parsed = parseTelemetryCsv(text);
        const generatorsPerTick = new Set(
          parsed.map((row) => row.generatorId),
        ).size;
        if (!controller.signal.aborted) {
          setRows(parsed);
          setCursor(Math.min(generatorsPerTick, parsed.length));
          setError(null);
        }
      } catch (loadError) {
        if (controller.signal.aborted) return;
        const message =
          loadError instanceof Error
            ? loadError.message
            : "Unable to parse telemetry CSV";
        setError(message);
        setRows([]);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadCsv();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (rows.length === 0) return;

    const generatorsPerTick = new Set(rows.map((row) => row.generatorId)).size;
    const interval = window.setInterval(() => {
      setCursor((current) => {
        const next = current + generatorsPerTick;
        return next > rows.length ? generatorsPerTick : next;
      });
    }, TICK_MS);

    return () => window.clearInterval(interval);
  }, [rows]);

  const visibleRows = useMemo(() => rows.slice(0, cursor), [rows, cursor]);

  return {
    generators: latestGenerators(visibleRows),
    stabilitySeries: toStabilitySeries(visibleRows).slice(-STABILITY_WINDOW),
    connected: !loading && error === null && rows.length > 0,
    loading,
    error,
  };
}
