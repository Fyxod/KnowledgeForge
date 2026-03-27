import React, { useState, useMemo, useCallback } from 'react';

interface RadarItem {
  name: string;
  quadrant: string;
  ring: string;
  description: string;
  is_new: boolean;
  moved_in?: string | null;
}

interface TechRadarProps {
  items: RadarItem[];
}

const QUADRANTS: Record<string, { start: number; end: number; color: string; label: string }> = {
  'Techniques': { start: 90, end: 180, color: '#1ebccd', label: 'Techniques' },
  'Platforms': { start: 0, end: 90, color: '#f38a3e', label: 'Platforms' },
  'Tools': { start: 270, end: 360, color: '#86b82a', label: 'Tools' },
  'Languages & Frameworks': { start: 180, end: 270, color: '#b32059', label: 'Languages & Frameworks' },
};

const RINGS: Record<string, { inner: number; outer: number; label: string }> = {
  'Adopt': { inner: 0, outer: 0.25, label: 'Adopt' },
  'Trial': { inner: 0.25, outer: 0.50, label: 'Trial' },
  'Assess': { inner: 0.50, outer: 0.75, label: 'Assess' },
  'Hold': { inner: 0.75, outer: 1.0, label: 'Hold' },
};

const RING_ORDER = ['Adopt', 'Trial', 'Assess', 'Hold'];

// Seeded pseudo-random for deterministic positioning
function seededRandom(seed: number): number {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function hashString(s: string): number {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = ((hash << 5) - hash) + s.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

const TechRadar: React.FC<TechRadarProps> = ({ items }) => {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; item: RadarItem } | null>(null);
  const [selectedQuadrant, setSelectedQuadrant] = useState<string | null>(null);

  const size = 600;
  const center = size / 2;
  const maxRadius = size / 2 - 40;

  const blips = useMemo(() => {
    return items.map((item, idx) => {
      const q = QUADRANTS[item.quadrant];
      const r = RINGS[item.ring];
      if (!q || !r) return null;

      const seed = hashString(item.name + idx);
      const anglePad = 8; // degrees padding from edges
      const angleRange = (q.end - q.start) - 2 * anglePad;
      const angle = (q.start + anglePad + seededRandom(seed) * angleRange) * (Math.PI / 180);

      const radiusPad = 0.03;
      const rMin = (r.inner + radiusPad) * maxRadius;
      const rMax = (r.outer - radiusPad) * maxRadius;
      const radius = rMin + seededRandom(seed + 1) * (rMax - rMin);

      const x = center + radius * Math.cos(angle);
      const y = center - radius * Math.sin(angle);

      return { ...item, x, y, color: q.color };
    }).filter(Boolean) as (RadarItem & { x: number; y: number; color: string })[];
  }, [items, center, maxRadius]);

  const filteredBlips = selectedQuadrant
    ? blips.filter(b => b.quadrant === selectedQuadrant)
    : blips;

  const handleMouseEnter = useCallback((e: React.MouseEvent, item: RadarItem & { x: number; y: number }) => {
    setTooltip({ x: item.x, y: item.y, item });
  }, []);

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  return (
    <div className="flex flex-col items-center gap-4 w-full">
      {/* Legend */}
      <div className="flex flex-wrap gap-3 justify-center">
        {Object.entries(QUADRANTS).map(([key, q]) => (
          <button
            key={key}
            onClick={() => setSelectedQuadrant(selectedQuadrant === key ? null : key)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all border ${
              selectedQuadrant === key
                ? 'ring-2 ring-offset-1 opacity-100'
                : selectedQuadrant
                ? 'opacity-40'
                : 'opacity-100'
            }`}
            style={{
              borderColor: q.color,
              color: q.color,
              ...(selectedQuadrant === key ? { backgroundColor: q.color + '20', ringColor: q.color } : {}),
            }}
          >
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: q.color }}
            />
            {q.label}
          </button>
        ))}
      </div>

      {/* Ring legend */}
      <div className="flex gap-4 text-xs text-muted-foreground">
        {RING_ORDER.map(ring => (
          <span key={ring} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-muted-foreground/40" />
            {ring}
          </span>
        ))}
        <span className="flex items-center gap-1 ml-2">
          <svg width="10" height="10"><polygon points="5,0 10,10 0,10" fill="currentColor" /></svg>
          New
        </span>
      </div>

      {/* Radar SVG */}
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full max-w-[600px] h-auto"
        style={{ fontFamily: 'ui-sans-serif, system-ui, sans-serif' }}
      >
        {/* Ring circles */}
        {RING_ORDER.map((ring) => {
          const r = RINGS[ring];
          return (
            <circle
              key={ring}
              cx={center}
              cy={center}
              r={r.outer * maxRadius}
              fill="none"
              stroke="currentColor"
              strokeOpacity={0.15}
              strokeWidth={1}
            />
          );
        })}

        {/* Ring labels */}
        {RING_ORDER.map((ring) => {
          const r = RINGS[ring];
          const labelR = ((r.inner + r.outer) / 2) * maxRadius;
          return (
            <text
              key={`label-${ring}`}
              x={center + labelR}
              y={center - 4}
              fontSize={9}
              fill="currentColor"
              fillOpacity={0.35}
              textAnchor="middle"
            >
              {ring}
            </text>
          );
        })}

        {/* Quadrant dividing lines */}
        {[0, 90, 180, 270].map(deg => {
          const rad = deg * (Math.PI / 180);
          return (
            <line
              key={`line-${deg}`}
              x1={center}
              y1={center}
              x2={center + maxRadius * Math.cos(rad)}
              y2={center - maxRadius * Math.sin(rad)}
              stroke="currentColor"
              strokeOpacity={0.15}
              strokeWidth={1}
            />
          );
        })}

        {/* Quadrant labels */}
        {Object.entries(QUADRANTS).map(([key, q]) => {
          const midAngle = ((q.start + q.end) / 2) * (Math.PI / 180);
          const labelR = maxRadius + 20;
          const lx = center + labelR * Math.cos(midAngle);
          const ly = center - labelR * Math.sin(midAngle);
          return (
            <text
              key={`qlabel-${key}`}
              x={lx}
              y={ly}
              fontSize={10}
              fontWeight="600"
              fill={q.color}
              textAnchor="middle"
              dominantBaseline="central"
            >
              {q.label}
            </text>
          );
        })}

        {/* Blips */}
        {filteredBlips.map((blip, idx) => (
          <g
            key={`${blip.name}-${idx}`}
            onMouseEnter={(e) => handleMouseEnter(e, blip)}
            onMouseLeave={handleMouseLeave}
            className="cursor-pointer"
          >
            {blip.is_new ? (
              <polygon
                points={`${blip.x},${blip.y - 6} ${blip.x + 5.2},${blip.y + 3} ${blip.x - 5.2},${blip.y + 3}`}
                fill={blip.color}
                stroke="white"
                strokeWidth={1}
              />
            ) : (
              <circle
                cx={blip.x}
                cy={blip.y}
                r={5}
                fill={blip.color}
                stroke="white"
                strokeWidth={1}
              />
            )}
          </g>
        ))}

        {/* Tooltip */}
        {tooltip && (
          <g>
            <rect
              x={tooltip.x + 10}
              y={tooltip.y - 30}
              width={Math.max(tooltip.item.name.length * 7, tooltip.item.description.length * 4.5, 160)}
              height={38}
              rx={4}
              fill="hsl(var(--popover))"
              stroke="hsl(var(--border))"
              strokeWidth={1}
              opacity={0.95}
            />
            <text
              x={tooltip.x + 16}
              y={tooltip.y - 16}
              fontSize={11}
              fontWeight="600"
              fill="hsl(var(--popover-foreground))"
            >
              {tooltip.item.name}
            </text>
            <text
              x={tooltip.x + 16}
              y={tooltip.y - 2}
              fontSize={9}
              fill="hsl(var(--muted-foreground))"
            >
              {tooltip.item.description.slice(0, 45)}{tooltip.item.description.length > 45 ? '...' : ''}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
};

export default TechRadar;
