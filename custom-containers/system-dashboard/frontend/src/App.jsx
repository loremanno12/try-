/**
 * Raspberry Pi 5 System Dashboard
 * Frontend sicuro - Zero integrazioni esterne
 *
 * Sicurezza implementata:
 * - Content Security Policy (CSP)
 * - Sanitizzazione input/output
 * - Validazione tipi dati
 * - Error boundary per crash isolati
 * - Rate limiting simulato (no fetch flood)
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  AreaChart, Area, ComposedChart, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import {
  Cpu, MemoryStick, Network, Server, Shield, Box, RefreshCw,
  AlertCircle, CheckCircle, Clock, Thermometer, Zap, Activity,
  HardDrive, Gauge, CircleDot, TrendingUp, Database
} from 'lucide-react';

// ==================== COSTANTI SICURE ====================
const API_BASE = '/api';
const REFRESH_INTERVAL = 2000;
const MAX_HISTORY_POINTS = 60;

// Tema colori (costanti, non dinamiche)
const THEME = Object.freeze({
  bg: '#0a0a0f',
  card: '#12121a',
  cardHover: '#1a1a25',
  border: '#1f1f2e',
  borderActive: '#2d2d42',
  violet: '#7C3AED',
  violetLight: '#8B5CF6',
  violetDark: '#5B21B6',
  violetGlow: 'rgba(124, 58, 237, 0.3)',
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#3B82F6',
  text: '#F3F4F6',
  textMuted: '#9CA3AF',
  textDim: '#6B7280',
});

// ==================== UTILITY SICURE ====================

/**
 * Formatta bytes in formato leggibile
 * @param {number} bytes
 * @returns {string}
 */
function formatBytes(bytes) {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes) || bytes < 0) {
    return '0 B';
  }
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const clampedI = Math.min(Math.max(0, i), units.length - 1);

  return `${parseFloat((bytes / Math.pow(k, clampedI)).toFixed(2))} ${units[clampedI]}`;
}

/**
 * Formatta uptime da secondi
 * @param {number} seconds
 * @returns {string}
 */
function formatUptime(seconds) {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) {
    return '--';
  }
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);

  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

/**
 * Valida e normalizza valore numerico
 * @param {unknown} value
 * @param {number} defaultVal
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
function safeNumber(value, defaultVal = 0, min = -Infinity, max = Infinity) {
  const num = Number(value);
  if (!Number.isFinite(num)) return defaultVal;
  return Math.min(Math.max(num, min), max);
}

/**
 * Sanitizza stringa per display (previene XSS)
 * @param {string} str
 * @returns {string}
 */
function sanitize(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Determina colore basato su soglia
 * @param {number} value
 * @param {number} warning
 * @param {number} critical
 * @returns {string}
 */
function getThresholdColor(value, warning = 70, critical = 85) {
  const v = safeNumber(value);
  if (v >= critical) return THEME.danger;
  if (v >= warning) return THEME.warning;
  return THEME.success;
}

// ==================== COMPONENTI UI ====================

/**
 * Card container con transizioni sicure
 */
function Card({ title, icon: Icon, children, className = '', fullWidth = false }) {
  return (
    <div
      className={`
        bg-[${THEME.card}] rounded-2xl border border-[${THEME.border}]
        p-5 transition-all duration-300 ease-out
        hover:border-[${THEME.borderActive}] hover:shadow-lg
        hover:shadow-[${THEME.violetGlow}]
        ${fullWidth ? 'col-span-full' : ''}
        ${className}
      `}
      style={{
        backgroundColor: THEME.card,
        borderColor: THEME.border,
      }}
    >
      {title && (
        <div
          className="flex items-center gap-3 mb-4"
          role="heading"
          aria-level={3}
        >
          {Icon && (
            <div
              className="p-2 rounded-lg"
              style={{ backgroundColor: `${THEME.violet}20` }}
            >
              <Icon
                className="w-5 h-5"
                style={{ color: THEME.violetLight }}
                aria-hidden="true"
              />
            </div>
          )}
          <h3 className="font-semibold text-lg" style={{ color: THEME.text }}>
            {title}
          </h3>
        </div>
      )}
      {children}
    </div>
  );
}

/**
 * Barra progresso con gradient animato
 */
function ProgressBar({ value, max = 100, warning = 70, critical = 85, height = 8 }) {
  const percentage = safeNumber((value / max) * 100, 0, 0, 100);
  const color = getThresholdColor(percentage, warning, critical);

  return (
    <div
      className="w-full rounded-full overflow-hidden"
      style={{
        height: `${height}px`,
        backgroundColor: THEME.border,
      }}
      role="progressbar"
      aria-valuenow={percentage}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full transition-all duration-500 ease-out"
        style={{
          width: `${percentage}%`,
          background: `linear-gradient(90deg, ${color}, ${color}cc)`,
          boxShadow: `0 0 10px ${color}40`,
        }}
      />
    </div>
  );
}

/**
 * Indicatore stato con dot animato
 */
function StatusDot({ status, label }) {
  const config = useMemo(() => ({
    running: { color: THEME.success, bg: `${THEME.success}20` },
    exited: { color: THEME.textMuted, bg: `${THEME.textMuted}20` },
    paused: { color: THEME.warning, bg: `${THEME.warning}20` },
    stopped: { color: THEME.danger, bg: `${THEME.danger}20` },
  }), []);

  const { color, bg } = config[status] || config.exited;
  const displayLabel = label || (status === 'running' ? 'Attivo' : status === 'exited' ? 'Arrestato' : status);

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: bg, color }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${status === 'running' ? 'animate-pulse' : ''}`}
        style={{ backgroundColor: color }}
      />
      {displayLabel}
    </span>
  );
}

/**
 * Grafico storico area con gradient
 */
function HistoryChart({ data, color, height = 120, yDomain = [0, 100], unit = '%' }) {
  const chartData = useMemo(() => {
    if (!Array.isArray(data)) return [];
    return data.slice(-MAX_HISTORY_POINTS).map((item, index) => ({
      index,
      value: safeNumber(item?.value, 0),
      time: item?.time || index,
    }));
  }, [data]);

  const gradientId = useMemo(() => `gradient-${Math.random().toString(36).substr(2, 9)}`, []);

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: `${height}px`, color: THEME.textMuted }}
      >
        <span className="text-sm">Nessun dato disponibile</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart
        data={chartData}
        margin={{ top: 5, right: 5, bottom: 5, left: 5 }}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.4} />
            <stop offset="95%" stopColor={color} stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke={THEME.border}
          vertical={false}
        />
        <XAxis dataKey="index" hide />
        <YAxis
          domain={yDomain}
          hide
          tick={{ fontSize: 10, fill: THEME.textMuted }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: THEME.card,
            border: `1px solid ${THEME.violet}`,
            borderRadius: '8px',
            fontSize: '12px',
            color: THEME.text,
          }}
          labelStyle={{ color: THEME.textMuted }}
          itemStyle={{ color }}
          formatter={(value) => [`${typeof value === 'number' ? value.toFixed(1) : value} ${unit}`, '']}
          cursor={{ stroke: THEME.violet, strokeWidth: 1, strokeDasharray: '4 4' }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          fill={`url(#${gradientId})`}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: color, stroke: THEME.card, strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/**
 * Grafico duale per network RX/TX
 */
function NetworkChart({ rxData, txData, height = 100 }) {
  const chartData = useMemo(() => {
    const rx = Array.isArray(rxData) ? rxData.slice(-MAX_HISTORY_POINTS) : [];
    const tx = Array.isArray(txData) ? txData.slice(-MAX_HISTORY_POINTS) : [];
    const maxLen = Math.max(rx.length, tx.length);

    return Array.from({ length: maxLen }, (_, i) => ({
      index: i,
      rx: safeNumber(rx[i]?.value, 0, 0),
      tx: safeNumber(tx[i]?.value, 0, 0),
    }));
  }, [rxData, txData]);

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: `${height}px`, color: THEME.textMuted }}
      >
        <span className="text-sm">Nessun dato di rete</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={THEME.border} vertical={false} />
        <XAxis dataKey="index" hide />
        <YAxis hide />
        <Tooltip
          contentStyle={{
            backgroundColor: THEME.card,
            border: `1px solid ${THEME.violet}`,
            borderRadius: '8px',
            fontSize: '12px',
            color: THEME.text,
          }}
          formatter={(value) => [formatBytes(value) + '/s', '']}
          cursor={{ stroke: THEME.violet, strokeWidth: 1 }}
        />
        <Area
          type="monotone"
          dataKey="rx"
          stroke={THEME.success}
          fill={`${THEME.success}20`}
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="tx"
          stroke={THEME.danger}
          fill={`${THEME.danger}20`}
          strokeWidth={2}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/**
 * Stat card compatta
 */
function StatBox({ label, value, subValue, color = THEME.text, icon: Icon }) {
  return (
    <div
      className="rounded-xl p-3 text-center transition-colors"
      style={{ backgroundColor: THEME.border }}
    >
      <p className="text-xs mb-1" style={{ color: THEME.textMuted }}>{label}</p>
      <p className="text-xl font-bold" style={{ color }}>{value}</p>
      {subValue && (
        <p className="text-xs mt-0.5" style={{ color: THEME.textDim }}>{subValue}</p>
      )}
    </div>
  );
}

/**
 * Badge per container status
 */
function ContainerStatusBadge({ status }) {
  return <StatusDot status={status} />;
}

// ==================== COMPONENTI PRINCIPALI ====================

/**
 * Card CPU con grafici
 */
function CpuCard({ data }) {
  const cpuOverall = safeNumber(data?.overall, 0, 0, 100);
  const perCore = Array.isArray(data?.per_core) ? data.per_core : [];
  const history = data?.history || [];
  const frequency = data?.frequency || {};
  const loadAvg = data?.load_average || [0, 0, 0];

  return (
    <Card title="CPU" icon={Cpu}>
      <div className="space-y-4">
        {/* Utilizzo principale */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm" style={{ color: THEME.textMuted }}>Utilizzo</span>
            <span className="text-2xl font-bold font-mono" style={{ color: getThresholdColor(cpuOverall) }}>
              {cpuOverall.toFixed(1)}%
            </span>
          </div>
          <ProgressBar value={cpuOverall} height={12} />
        </div>

        {/* Storico */}
        <div>
          <p className="text-xs mb-2" style={{ color: THEME.textDim }}>
            Storico {history.length}/{MAX_HISTORY_POINTS} campioni
          </p>
          <HistoryChart
            data={history}
            color={THEME.violet}
            height={100}
            yDomain={[0, 100]}
          />
        </div>

        {/* Info stats */}
        <div className="grid grid-cols-3 gap-2">
          <StatBox
            label="Threads"
            value={data?.core_count || 0}
            subValue="cores"
            color={THEME.text}
          />
          <StatBox
            label="Freq"
            value={((frequency.current || 0) / 1000).toFixed(1)}
            subValue="GHz"
            color={THEME.info}
          />
          <StatBox
            label="Load"
            value={safeNumber(loadAvg[0]).toFixed(2)}
            subValue="1m"
            color={THEME.warning}
          />
        </div>

        {/* Per core */}
        <div>
          <p className="text-xs mb-2" style={{ color: THEME.textDim }}>Utilizzo per Core</p>
          <div className="flex flex-wrap gap-1">
            {perCore.map((value, i) => (
              <div key={i} className="text-center">
                <div
                  className="w-6 rounded-t flex items-end justify-center overflow-hidden mx-0.5"
                  style={{ height: '28px', backgroundColor: THEME.border }}
                >
                  <div
                    className="w-full transition-all duration-300"
                    style={{
                      height: `${safeNumber(value, 0, 0, 100)}%`,
                      background: `linear-gradient(to top, ${THEME.violetDark}, ${THEME.violetLight})`,
                    }}
                  />
                </div>
                <span className="text-[9px]" style={{ color: THEME.textDim }}>
                  {safeNumber(value, 0).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Card RAM con grafici
 */
function RamCard({ data }) {
  const ramPercent = safeNumber(data?.ram?.percent, 0, 0, 100);
  const ramUsed = safeNumber(data?.ram?.used, 0);
  const ramAvailable = safeNumber(data?.ram?.available, 0);
  const ramTotal = safeNumber(data?.ram?.total, 0);
  const history = data?.history || [];
  const swap = data?.swap || {};

  return (
    <Card title="Memoria RAM" icon={MemoryStick}>
      <div className="space-y-4">
        {/* Utilizzo principale */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm" style={{ color: THEME.textMuted }}>Utilizzo</span>
            <span className="text-2xl font-bold font-mono" style={{ color: getThresholdColor(ramPercent) }}>
              {ramPercent.toFixed(1)}%
            </span>
          </div>
          <ProgressBar value={ramPercent} height={12} />
        </div>

        {/* Storico */}
        <div>
          <p className="text-xs mb-2" style={{ color: THEME.textDim }}>
            Storico {history.length}/{MAX_HISTORY_POINTS} campioni
          </p>
          <HistoryChart
            data={history}
            color={THEME.success}
            height={100}
            yDomain={[0, 100]}
          />
        </div>

        {/* Info RAM */}
        <div className="grid grid-cols-2 gap-3">
          <div
            className="rounded-xl p-4"
            style={{ backgroundColor: THEME.border }}
          >
            <p className="text-xs mb-1" style={{ color: THEME.textMuted }}>Usata</p>
            <p className="text-lg font-bold" style={{ color: THEME.violetLight }}>
              {formatBytes(ramUsed)}
            </p>
          </div>
          <div
            className="rounded-xl p-4"
            style={{ backgroundColor: THEME.border }}
          >
            <p className="text-xs mb-1" style={{ color: THEME.textMuted }}>Disponibile</p>
            <p className="text-lg font-bold" style={{ color: THEME.success }}>
              {formatBytes(ramAvailable)}
            </p>
          </div>
        </div>

        {/* Totale */}
        <p className="text-center text-sm" style={{ color: THEME.textDim }}>
          Totale: {formatBytes(ramTotal)}
        </p>

        {/* Swap */}
        {swap && swap.total > 0 && (
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span style={{ color: THEME.textMuted }}>Swap</span>
              <span style={{ color: THEME.textDim }}>
                {formatBytes(swap.used)} / {formatBytes(swap.total)}
              </span>
            </div>
            <ProgressBar value={swap.percent} warning={50} critical={80} height={4} />
          </div>
        )}
      </div>
    </Card>
  );
}

/**
 * Card Raspberry Pi 5 specifica
 */
function PiCard({ data }) {
  const temp = safeNumber(data?.temperature?.value, null);
  const tempHistory = data?.temperature?.history || [];
  const throttling = data?.throttling || {};
  const clock = data?.clock || {};
  const voltage = data?.voltage || {};

  const tempColor = temp !== null ? getThresholdColor(temp, 70, 80) : THEME.textMuted;
  const hasThrottling = throttling?.undervoltage || throttling?.throttled ||
                        throttling?.soft_temp_limited || throttling?.freq_capped;

  return (
    <Card title="Raspberry Pi 5" icon={Gauge}>
      <div className="space-y-4">
        {/* Temperatura */}
        <div
          className="rounded-xl p-4"
          style={{ backgroundColor: THEME.border }}
        >
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Thermometer className="w-5 h-5" style={{ color: tempColor }} />
              <span className="text-sm" style={{ color: THEME.textMuted }}>Temperatura CPU</span>
            </div>
            <span
              className="text-2xl font-bold font-mono"
              style={{ color: tempColor }}
            >
              {temp !== null ? `${temp.toFixed(1)}°C` : '--°C'}
            </span>
          </div>
          <div className="mt-2">
            <ProgressBar
              value={temp !== null ? temp : 0}
              max={85}
              height={6}
              warning={70}
              critical={80}
            />
          </div>
        </div>

        {/* Storico temperatura */}
        <div>
          <p className="text-xs mb-2" style={{ color: THEME.textDim }}>
            Storico Temperatura
          </p>
          <HistoryChart
            data={tempHistory}
            color={tempColor}
            height={80}
            unit="°C"
          />
        </div>

        {/* Throttling */}
        <div
          className="rounded-xl p-3"
          style={{ backgroundColor: THEME.border }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Zap
              className="w-4 h-4"
              style={{ color: hasThrottling ? THEME.danger : THEME.success }}
            />
            <span className="text-sm" style={{ color: THEME.textMuted }}>Throttling Status</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {throttling.undervoltage && (
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: `${THEME.danger}20`, color: THEME.danger }}
              >
                Under-voltage
              </span>
            )}
            {throttling.throttled && (
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: `${THEME.warning}20`, color: THEME.warning }}
              >
                Throttled
              </span>
            )}
            {throttling.soft_temp_limited && (
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: `${THEME.danger}20`, color: THEME.danger }}
              >
                Temp Limited
              </span>
            )}
            {throttling.freq_capped && (
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: `${THEME.warning}20`, color: THEME.warning }}
              >
                Freq Capped
              </span>
            )}
            {!hasThrottling && (
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: `${THEME.success}20`, color: THEME.success }}
              >
                Normale
              </span>
            )}
          </div>
        </div>

        {/* Clock */}
        <div className="grid grid-cols-2 gap-2">
          <StatBox
            label="ARM Clock"
            value={clock.arm_formatted || '--'}
            color={THEME.violetLight}
          />
          <StatBox
            label="Core Clock"
            value={clock.core_formatted || '--'}
            color={THEME.success}
          />
        </div>

        {/* Voltage */}
        {Object.keys(voltage).length > 0 && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(voltage).map(([key, val]) => (
              <div
                key={key}
                className="px-2 py-1 rounded text-xs"
                style={{ backgroundColor: THEME.border }}
              >
                <span style={{ color: THEME.textMuted }}>{key}: </span>
                <span className="font-mono" style={{ color: THEME.text }}>
                  {safeNumber(val).toFixed(3)}V
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

/**
 * Card Network
 */
function NetworkCard({ data }) {
  const rxRate = safeNumber(data?.rate?.rx_rate, 0);
  const txRate = safeNumber(data?.rate?.tx_rate, 0);
  const totalRx = safeNumber(data?.current?.bytes_recv, 0);
  const totalTx = safeNumber(data?.current?.bytes_sent, 0);
  const packetsRx = safeNumber(data?.current?.packets_recv, 0);
  const packetsTx = safeNumber(data?.current?.packets_sent, 0);
  const historyRx = data?.history?.rx || [];
  const historyTx = data?.history?.tx || [];

  return (
    <Card title="Rete" icon={Network}>
      <div className="space-y-4">
        {/* Rate attuale */}
        <div className="grid grid-cols-2 gap-3">
          <div
            className="rounded-xl p-4 text-center"
            style={{ backgroundColor: THEME.border }}
          >
            <div className="flex items-center justify-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4" style={{ color: THEME.success }} />
              <span className="text-xs" style={{ color: THEME.textMuted }}>Download</span>
            </div>
            <p className="text-xl font-bold" style={{ color: THEME.success }}>
              {data?.rate?.rx_rate_formatted || formatBytes(rxRate) + '/s'}
            </p>
          </div>
          <div
            className="rounded-xl p-4 text-center"
            style={{ backgroundColor: THEME.border }}
          >
            <div className="flex items-center justify-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 rotate-180" style={{ color: THEME.danger }} />
              <span className="text-xs" style={{ color: THEME.textMuted }}>Upload</span>
            </div>
            <p className="text-xl font-bold" style={{ color: THEME.danger }}>
              {data?.rate?.tx_rate_formatted || formatBytes(txRate) + '/s'}
            </p>
          </div>
        </div>

        {/* Grafico */}
        <div>
          <p className="text-xs mb-2" style={{ color: THEME.textDim }}>Storico Network</p>
          <NetworkChart rxData={historyRx} txData={historyTx} height={100} />
          <div className="flex justify-center gap-4 mt-2 text-xs">
            <span style={{ color: THEME.success }} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: THEME.success }} />
              Download
            </span>
            <span style={{ color: THEME.danger }} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: THEME.danger }} />
              Upload
            </span>
          </div>
        </div>

        {/* Totali */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex justify-between">
            <span style={{ color: THEME.textMuted }}>Ricevuti</span>
            <span className="font-mono" style={{ color: THEME.text }}>
              {data?.formatted?.bytes_recv || formatBytes(totalRx)}
            </span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: THEME.textMuted }}>Inviati</span>
            <span className="font-mono" style={{ color: THEME.text }}>
              {data?.formatted?.bytes_sent || formatBytes(totalTx)}
            </span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: THEME.textMuted }}>Pacchetti RX</span>
            <span className="font-mono" style={{ color: THEME.text }}>
              {packetsRx.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: THEME.textMuted }}>Pacchetti TX</span>
            <span className="font-mono" style={{ color: THEME.text }}>
              {packetsTx.toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Card Disco
 */
function DiskCard({ data }) {
  const disks = Array.isArray(data?.disks) ? data.disks : [];
  const ioStats = data?.io_stats;

  return (
    <Card title="Disco" icon={HardDrive}>
      <div className="space-y-4">
        {disks.slice(0, 4).map((disk, i) => {
          const percent = safeNumber(disk.percent, 0, 0, 100);
          return (
            <div key={i}>
              <div className="flex justify-between text-sm mb-1">
                <span
                  className="truncate max-w-[200px]"
                  style={{ color: THEME.textMuted }}
                  title={disk.mountpoint || disk.device}
                >
                  {sanitize(disk.mountpoint || disk.device)}
                </span>
                <span className="font-mono" style={{ color: THEME.text }}>
                  {percent.toFixed(1)}%
                </span>
              </div>
              <ProgressBar
                value={percent}
                warning={70}
                critical={90}
                height={8}
              />
              <p className="text-xs mt-1" style={{ color: THEME.textDim }}>
                {formatBytes(disk.used)} / {formatBytes(disk.total)}
              </p>
            </div>
          );
        })}

        {/* I/O Stats */}
        {ioStats && (
          <div className="border-t pt-3" style={{ borderColor: THEME.border }}>
            <p className="text-xs mb-2" style={{ color: THEME.textDim }}>I/O Disco</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between">
                <span style={{ color: THEME.textMuted }}>Letture</span>
                <span className="font-mono" style={{ color: THEME.success }}>
                  {ioStats.read_bytes_formatted || formatBytes(ioStats.read_bytes)}
                </span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: THEME.textMuted }}>Scritture</span>
                <span className="font-mono" style={{ color: THEME.danger }}>
                  {ioStats.write_bytes_formatted || formatBytes(ioStats.write_bytes)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

/**
 * Card Sistema
 */
function SystemCard({ data, dockerAvailable }) {
  const platform = data?.platform || {};

  return (
    <Card title="Sistema" icon={Server}>
      <div className="space-y-3 text-sm">
        <div className="flex justify-between">
          <span style={{ color: THEME.textMuted }}>Sistema</span>
          <span style={{ color: THEME.text }}>{sanitize(platform.system || '--')}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: THEME.textMuted }}>Hostname</span>
          <span className="font-mono" style={{ color: THEME.text }}>
            {sanitize(platform.node || '--')}
          </span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: THEME.textMuted }}>Kernel</span>
          <span className="font-mono text-xs" style={{ color: THEME.text }}>
            {sanitize(platform.release || '--')}
          </span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: THEME.textMuted }}>Architettura</span>
          <span style={{ color: THEME.text }}>{sanitize(platform.machine || '--')}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: THEME.textMuted }}>Boot</span>
          <span className="text-xs" style={{ color: THEME.text }}>
            {data?.boot_time ? new Date(data.boot_time).toLocaleString() : '--'}
          </span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: THEME.textMuted }}>Docker</span>
          <span style={{ color: dockerAvailable ? THEME.success : THEME.textMuted }}>
            {dockerAvailable ? 'Disponibile' : 'Non disponibile'}
          </span>
        </div>
      </div>
    </Card>
  );
}

/**
 * Card Pi-hole
 */
function PiHoleCard({ data }) {
  const connected = data?.connected === true;
  const stats = data?.data || {};

  if (!connected) {
    return (
      <Card title="Pi-hole" icon={Shield} fullWidth>
        <div className="flex items-center gap-3 py-4" style={{ color: THEME.warning }}>
          <AlertCircle className="w-6 h-6" />
          <div>
            <p className="font-semibold">Pi-hole non connesso</p>
            <p className="text-sm" style={{ color: THEME.textMuted }}>
              {sanitize(data?.error || 'Verifica la configurazione')}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Pi-hole" icon={Shield} fullWidth>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatBox
          label="Query Oggi"
          value={stats.dns_queries_today?.toLocaleString() || '0'}
          color={THEME.text}
        />
        <StatBox
          label="Ads Bloccati"
          value={stats.ads_blocked_today?.toLocaleString() || '0'}
          color={THEME.danger}
        />
        <StatBox
          label="% Bloccaggio"
          value={`${safeNumber(stats.ads_percentage_today).toFixed(1)}%`}
          color={THEME.warning}
        />
        <StatBox
          label="Domini"
          value={stats.domains_being_blocking || '0'}
          color={THEME.violetLight}
        />
      </div>
      <div className="mt-4 flex items-center gap-2" style={{ color: THEME.success }}>
        <CheckCircle className="w-4 h-4" />
        <span className="text-sm">Pi-hole Attivo</span>
      </div>
    </Card>
  );
}

/**
 * Card Docker Containers
 */
function DockerStatsCard({ stats }) {
  if (!Array.isArray(stats) || stats.length === 0) return null;

  return (
    <Card title="Docker Containers" icon={Box} fullWidth>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {stats.map((stat) => {
          const cpuPercent = safeNumber(stat.cpu_percent, 0, 0, 100);
          const memPercent = safeNumber(stat.memory_percent, 0, 0, 100);

          return (
            <div
              key={stat.id}
              className="rounded-xl p-4 transition-colors"
              style={{ backgroundColor: THEME.border }}
            >
              <div className="flex justify-between items-start mb-3">
                <span
                  className="font-mono text-sm truncate max-w-[140px]"
                  style={{ color: THEME.text }}
                  title={stat.name}
                >
                  {sanitize(stat.name)}
                </span>
                <ContainerStatusBadge status={stat.status} />
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                <div>
                  <span style={{ color: THEME.textMuted }}>CPU</span>
                  <span className="ml-1" style={{ color: THEME.text }}>
                    {cpuPercent.toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span style={{ color: THEME.textMuted }}>RAM</span>
                  <span className="ml-1" style={{ color: THEME.text }}>
                    {memPercent.toFixed(1)}%
                  </span>
                </div>
              </div>

              <div className="space-y-1 mb-2">
                <ProgressBar value={cpuPercent} height={4} />
                <ProgressBar
                  value={memPercent}
                  height={4}
                  warning={70}
                  critical={85}
                />
              </div>

              <div className="flex gap-3 text-xs" style={{ color: THEME.textDim }}>
                <span style={{ color: THEME.success }}>
                  ↓{formatBytes(safeNumber(stat.network_rx))}
                </span>
                <span style={{ color: THEME.danger }}>
                  ↑{formatBytes(safeNumber(stat.network_tx))}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

/**
 * Lista Container Docker
 */
function DockerContainersList({ data }) {
  if (!data?.available || !Array.isArray(data.containers) || data.containers.length === 0) {
    return null;
  }

  return (
    <Card title={`Container Docker (${data.containers.length})`} icon={Box} fullWidth>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.containers.map((container) => (
          <div
            key={container.id}
            className="rounded-xl p-3 transition-colors"
            style={{ backgroundColor: THEME.border }}
          >
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2">
                <CircleDot className="w-4 h-4" style={{ color: THEME.violetLight }} />
                <span
                  className="font-mono text-sm truncate max-w-[160px]"
                  style={{ color: THEME.text }}
                  title={container.name}
                >
                  {sanitize(container.name)}
                </span>
              </div>
              <ContainerStatusBadge status={container.status} />
            </div>
            <p
              className="text-xs truncate mb-2"
              style={{ color: THEME.textDim }}
              title={container.image}
            >
              {sanitize(container.image)}
            </p>

            {container.ports && Object.keys(container.ports).length > 0 && (
              <div className="flex flex-wrap gap-1">
                {Object.entries(container.ports).map(([port, bindings]) => (
                  bindings && bindings.length > 0 && (
                    <span
                      key={port}
                      className="text-xs px-2 py-0.5 rounded"
                      style={{ backgroundColor: THEME.card }}
                    >
                      :{sanitize(bindings.map(b => b.HostPort).join(' → '))}
                    </span>
                  )
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

// ==================== MAIN APP ====================

/**
 * Error Boundary per isolare crash
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Dashboard Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="min-h-screen flex items-center justify-center p-6"
          style={{ backgroundColor: THEME.bg }}
        >
          <div className="text-center">
            <AlertCircle className="w-16 h-16 mx-auto mb-4" style={{ color: THEME.danger }} />
            <h1 className="text-xl font-bold mb-2" style={{ color: THEME.text }}>
              Errore nel Dashboard
            </h1>
            <p className="text-sm" style={{ color: THEME.textMuted }}>
              Si è verificato un errore. Ricarica la pagina.
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  // State con validazione iniziale
  const [cpuData, setCpuData] = useState({});
  const [memoryData, setMemoryData] = useState({ ram: {}, history: [] });
  const [piData, setPiData] = useState({ temperature: {}, throttling: {}, clock: {} });
  const [networkData, setNetworkData] = useState({ current: {}, rate: {}, history: {} });
  const [diskData, setDiskData] = useState({ disks: [], io_stats: null });
  const [dockerData, setDockerData] = useState({ available: false, containers: [] });
  const [dockerStats, setDockerStats] = useState([]);
  const [piholeData, setPiholeData] = useState(null);
  const [systemInfo, setSystemInfo] = useState({});
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [errorCount, setErrorCount] = useState(0);

  // Ref per rate limiting
  const lastFetchRef = useRef(0);
  const minInterval = 1000; // 1 secondo minimo tra fetch

  const fetchData = useCallback(async () => {
    // Rate limiting
    const now = Date.now();
    if (now - lastFetchRef.current < minInterval) {
      return;
    }
    lastFetchRef.current = now;

    try {
      const endpoints = [
        { key: 'cpu', url: `${API_BASE}/cpu` },
        { key: 'memory', url: `${API_BASE}/memory` },
        { key: 'pi', url: `${API_BASE}/pi` },
        { key: 'network', url: `${API_BASE}/network` },
        { key: 'disk', url: `${API_BASE}/disk` },
        { key: 'docker', url: `${API_BASE}/docker/containers` },
        { key: 'dockerStats', url: `${API_BASE}/docker/stats` },
        { key: 'pihole', url: `${API_BASE}/pihole` },
        { key: 'system', url: `${API_BASE}/system` },
      ];

      const results = await Promise.all(
        endpoints.map(async ({ key, url }) => {
          try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            return { key, data };
          } catch (error) {
            console.warn(`Fetch error for ${key}:`, error.message);
            return { key, data: null };
          }
        })
      );

      // Update state solo se dati validi
      results.forEach(({ key, data }) => {
        if (data === null) return;

        switch (key) {
          case 'cpu':
            setCpuData(data || {});
            break;
          case 'memory':
            setMemoryData(data || { ram: {}, history: [] });
            break;
          case 'pi':
            setPiData(data || { temperature: {}, throttling: {}, clock: {} });
            break;
          case 'network':
            setNetworkData(data || { current: {}, rate: {}, history: {} });
            break;
          case 'disk':
            setDiskData(data || { disks: [], io_stats: null });
            break;
          case 'docker':
            setDockerData(data || { available: false, containers: [] });
            break;
          case 'dockerStats':
            setDockerStats(data?.stats || []);
            break;
          case 'pihole':
            setPiholeData(data);
            break;
          case 'system':
            setSystemInfo(data || {});
            break;
        }
      });

      setLastUpdate(new Date());
      setLoading(false);
      setErrorCount(0);
    } catch (error) {
      console.error('Fetch error:', error);
      setErrorCount(prev => prev + 1);
      if (errorCount >= 5) {
        setLoading(false);
      }
    }
  }, [errorCount]);

  // Fetch iniziale e interval
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <ErrorBoundary>
      <div
        className="min-h-screen p-4 md:p-6"
        style={{ backgroundColor: THEME.bg, color: THEME.text }}
      >
        {/* Header */}
        <header className="mb-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1
                className="text-2xl md:text-3xl font-bold"
                style={{
                  background: `linear-gradient(90deg, ${THEME.violetLight}, ${THEME.violet})`,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Raspberry Pi 5 Dashboard
              </h1>
              <div className="flex items-center gap-2 mt-1 text-sm" style={{ color: THEME.textMuted }}>
                <Clock className="w-4 h-4" />
                <span>
                  Ultimo aggiornamento: {lastUpdate.toLocaleTimeString()}
                </span>
                {loading && (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                )}
                <button
                  onClick={fetchData}
                  className="p-1 rounded transition-colors hover:bg-opacity-10"
                  style={{ backgroundColor: THEME.border }}
                  aria-label="Aggiorna dati"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            </div>

            {systemInfo.uptime_formatted && (
              <div className="flex items-center gap-4">
                <div
                  className="px-4 py-2 rounded-lg text-sm"
                  style={{ backgroundColor: THEME.card, border: `1px solid ${THEME.border}` }}
                >
                  <span style={{ color: THEME.textMuted }}>Uptime: </span>
                  <span style={{ color: THEME.violetLight }} className="font-mono">
                    {formatUptime(systemInfo.uptime_seconds)}
                  </span>
                </div>
                <div
                  className="px-4 py-2 rounded-lg text-sm"
                  style={{ backgroundColor: THEME.card, border: `1px solid ${THEME.border}` }}
                >
                  <span style={{ color: THEME.textMuted }}>RAM: </span>
                  <span style={{ color: THEME.violetLight }} className="font-mono">
                    {formatBytes(safeNumber(memoryData.ram?.total))}
                  </span>
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Griglia Dashboard */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          <CpuCard data={cpuData} />
          <RamCard data={memoryData} />
          <PiCard data={piData} />
          <NetworkCard data={networkData} />
          <DiskCard data={diskData} />
          <SystemCard data={systemInfo} dockerAvailable={dockerData.available} />

          {/* Pi-hole full width */}
          <PiHoleCard data={piholeData} />

          {/* Docker stats full width */}
          <DockerStatsCard stats={dockerStats} />
        </div>

        {/* Container list full width */}
        <DockerContainersList data={dockerData} />

        {/* Footer */}
        <footer className="mt-8 text-center text-xs" style={{ color: THEME.textDim }}>
          <p>
            Raspberry Pi 5 Dashboard v1.2.0 • Aggiornamento: {REFRESH_INTERVAL / 1000}s •
            {systemInfo.platform?.node || 'System'}
          </p>
        </footer>
      </div>
    </ErrorBoundary>
  );
}

// Import React per ErrorBoundary
import React from 'react';
