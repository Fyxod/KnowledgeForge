/* eslint-disable @typescript-eslint/no-explicit-any */
// Some environments don't ship pdfmake type paths identically; use loose types to avoid TS resolution errors.
type TDocumentDefinitions = any;
type Content = any;
type TableCell = any;

// Import pdfmake (browser build) and its default font VFS shim.
import pdfMake from 'pdfmake/build/pdfmake';
import 'pdfmake/build/vfs_fonts';
import type { StrategicRoadmapLLMOutput } from './api';

// Initialize virtual file system for fonts (required by pdfmake in browser)
const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

// ── Color palette (matches UI Tailwind colors) ──────────────────────────────
const colors = {
    // Banner
    bannerBg: '#7C3AED',       // violet-600
    // Section tones
    emerald: { bg: '#D1FAE5', text: '#047857' },
    sky:     { bg: '#E0F2FE', text: '#0369A1' },
    violet:  { bg: '#EDE9FE', text: '#6D28D9' },
    fuchsia: { bg: '#FAE8FF', text: '#A21CAF' },
    rose:    { bg: '#FFE4E6', text: '#BE123C' },
    amber:   { bg: '#FEF3C7', text: '#B45309' },
    muted:   { bg: '#F1F5F9', text: '#475569' },
    // SWOT quadrant colors
    swotStrengths:     { bg: '#D1FAE5', text: '#047857', headerBg: '#10B981' },
    swotWeaknesses:    { bg: '#FEF3C7', text: '#B45309', headerBg: '#F59E0B' },
    swotOpportunities: { bg: '#E0F2FE', text: '#0369A1', headerBg: '#0284C7' },
    swotThreats:       { bg: '#FFE4E6', text: '#BE123C', headerBg: '#EF4444' },
    // General
    slate600: '#475569',
    slate800: '#1F2937',
    slate500: '#64748B',
    border: '#E2E8F0',
    codeBg: '#F1F5F9',
};

function sanitizeText(s: string | undefined | null): string {
    if (!s) return '';
    return String(s)
        .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/×/g, 'x')
        .replace(/±/g, '+/-').replace(/[–—]/g, '-').replace(/[""]/g, '"')
        .replace(/\u202F/g, ' ').replace(/'/g, "'").replace(/‑/g, '-');
}

// ── PDF helpers matching UI visual style ────────────────────────────────────

/** Colored banner block */
function banner(title: string, subtitle: string): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{
                stack: [
                    { text: sanitizeText(title), fontSize: 20, bold: true, color: '#FFFFFF', alignment: 'center', margin: [0, 0, 0, 4] },
                    ...(subtitle ? [{ text: sanitizeText(subtitle), fontSize: 10, color: '#FFFFFF', alignment: 'center' }] : []),
                ],
                fillColor: colors.bannerBg,
                margin: [12, 14, 12, 14],
            }]],
        },
        layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
        margin: [0, 0, 0, 10],
    };
}

/** Section header with tinted background */
function sectionBlock(title: string, tone: { bg: string; text: string }): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{
                text: sanitizeText(title),
                fontSize: 13, bold: true, color: tone.text,
                fillColor: tone.bg,
                margin: [10, 6, 10, 6],
            }]],
        },
        layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
        margin: [0, 14, 0, 8],
    };
}

/** Card wrapper — bordered single-cell table */
function card(content: Content[], borderColor: string = colors.border): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{ stack: content, margin: [8, 8, 8, 8] }]],
        },
        layout: {
            hLineWidth: () => 0.75,
            vLineWidth: () => 0.75,
            hLineColor: () => borderColor,
            vLineColor: () => borderColor,
        },
        margin: [0, 3, 0, 3],
    };
}

/** Pill badges */
function pills(items: string[], tone: { bg: string; text: string }): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        columns: items.map((item) => ({
            text: sanitizeText(item),
            fontSize: 8, bold: true,
            color: tone.text,
            background: tone.bg,
            margin: [4, 3, 4, 3],
        })),
        columnGap: 6,
        margin: [0, 4, 0, 6],
    };
}

function bulletList(items: string[] = []): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        ul: items.map((i) => ({ text: sanitizeText(i), margin: [0, 2, 0, 2] })),
        margin: [0, 4, 0, 0],
    } as Content;
}

// ── Section content builders ────────────────────────────────────────────────

function swotTable(swot: StrategicRoadmapLLMOutput['current_baseline']['swot']): Content {
    const quadrant = (
        title: string,
        points: string[],
        tone: { bg: string; text: string; headerBg: string },
    ): TableCell => ({
        stack: [
            {
                table: {
                    widths: ['*'],
                    body: [[{
                        text: title, fontSize: 11, bold: true, color: '#FFFFFF',
                        fillColor: tone.headerBg, margin: [6, 4, 6, 4],
                    }]],
                },
                layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
            },
            bulletList(points),
        ],
        fillColor: tone.bg,
        margin: [4, 4, 4, 4],
    });

    return {
        table: {
            widths: ['*', '*'],
            body: [
                [
                    quadrant('Strengths', swot.strengths, colors.swotStrengths),
                    quadrant('Weaknesses', swot.weaknesses, colors.swotWeaknesses),
                ],
                [
                    quadrant('Opportunities', swot.opportunities, colors.swotOpportunities),
                    quadrant('Threats', swot.threats, colors.swotThreats),
                ],
            ],
        },
        layout: {
            paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0,
            hLineColor: () => '#FFFFFF', vLineColor: () => '#FFFFFF',
            hLineWidth: () => 2, vLineWidth: () => 2,
        },
        margin: [0, 6, 0, 0],
    };
}

function pillarsContent(pillars: StrategicRoadmapLLMOutput['strategic_pillars']): Content[] {
    return pillars.map((p) =>
        card([
            { text: sanitizeText(p.pillar_name), fontSize: 11, bold: true, color: colors.violet.text, margin: [0, 0, 0, 3] },
            { text: sanitizeText(p.description), fontSize: 10, color: colors.slate600 },
        ], '#DDD6FE'), // violet-200
    );
}

function phasedRoadmap(phases: StrategicRoadmapLLMOutput['phased_roadmap']): Content[] {
    return phases.map((ph) => ({
        table: {
            widths: ['*'],
            body: [[{
                stack: [
                    {
                        columns: [
                            { text: sanitizeText(ph.phase), fontSize: 11, bold: true, color: colors.fuchsia.text },
                            { text: sanitizeText(ph.time_frame), fontSize: 10, alignment: 'right', color: colors.slate600 },
                        ],
                    },
                    { canvas: [{ type: 'line', x1: 0, y1: 2, x2: 490, y2: 2, lineWidth: 0.5, lineColor: colors.border }] },
                    { text: 'Objectives', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 6, 0, 2] },
                    bulletList(ph.key_objectives),
                    { text: 'Initiatives', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 6, 0, 2] },
                    bulletList(ph.key_initiatives),
                    { text: 'Expected Outcomes', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 6, 0, 2] },
                    bulletList(ph.expected_outcomes),
                ],
                margin: [8, 8, 8, 8],
            }]],
        },
        layout: {
            hLineWidth: () => 0.75, vLineWidth: () => 0.75,
            hLineColor: () => '#E9D5FF', // violet-200
            vLineColor: () => '#E9D5FF',
        },
        margin: [0, 6, 0, 0],
    }));
}

function risksTable(risks: StrategicRoadmapLLMOutput['risks_and_mitigation']): Content {
    const body: TableCell[][] = [
        [
            { text: 'Risk', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
            { text: 'Mitigation', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
        ],
    ];
    risks.forEach((r) => {
        body.push([
            { text: sanitizeText(r.risk), margin: [4, 4, 4, 4] },
            { text: sanitizeText(r.mitigation_strategy), margin: [4, 4, 4, 4] },
        ]);
    });
    return {
        table: { widths: ['*', '*'], body },
        layout: {
            hLineColor: () => '#FECDD3',
            vLineColor: () => '#FECDD3',
            hLineWidth: () => 0.75,
            vLineWidth: () => 0.75,
        },
        margin: [0, 6, 0, 0],
    };
}

function metricsContent(metrics: StrategicRoadmapLLMOutput['key_metrics_and_milestones']): Content[] {
    return metrics.map((m) =>
        card([
            { text: sanitizeText(m.year_or_phase), fontSize: 11, bold: true, color: colors.violet.text, margin: [0, 0, 0, 3] },
            bulletList(m.metrics),
        ], '#DDD6FE'),
    );
}

// ── Document definition builder ─────────────────────────────────────────────

function buildDocDefinition(roadmap: StrategicRoadmapLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    const content: Content[] = [];

    // Banner
    content.push(banner(roadmap.roadmap_title, 'Strategic, phased plan with goals, enablers, risks, and measurable milestones.'));

    // Vision & End Goal
    content.push(sectionBlock('Vision & End Goal', colors.emerald));
    content.push({ text: sanitizeText(roadmap.vision_and_end_goal.description), fontSize: 10, color: colors.slate600, margin: [0, 2, 0, 4] });
    if (roadmap.vision_and_end_goal.success_criteria?.length > 0) {
        content.push({ text: 'Success Criteria', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 4, 0, 4] });
        content.push(pills(roadmap.vision_and_end_goal.success_criteria, colors.emerald));
    }

    // Current Baseline + SWOT
    content.push(sectionBlock('Current Baseline', colors.sky));
    content.push({ text: sanitizeText(roadmap.current_baseline.summary), fontSize: 10, color: colors.slate600, margin: [0, 2, 0, 4] });
    content.push(swotTable(roadmap.current_baseline.swot));

    // Strategic Pillars
    content.push(sectionBlock('Strategic Pillars', colors.violet));
    content.push(...pillarsContent(roadmap.strategic_pillars));

    // Phased Roadmap
    content.push(sectionBlock('Phased Strategic Roadmap', colors.fuchsia));
    content.push(...phasedRoadmap(roadmap.phased_roadmap));

    // Enablers & Dependencies
    content.push(sectionBlock('Enablers & Dependencies', colors.sky));
    content.push({
        columns: [
            {
                stack: [
                    { text: 'Technologies', fontSize: 10, bold: true, color: colors.sky.text, margin: [0, 0, 0, 4] },
                    bulletList(roadmap.enablers_and_dependencies.technologies),
                ],
            },
            {
                stack: [
                    { text: 'Skills & Resources', fontSize: 10, bold: true, color: colors.sky.text, margin: [0, 0, 0, 4] },
                    bulletList(roadmap.enablers_and_dependencies.skills_and_resources),
                ],
            },
        ],
        columnGap: 16,
    });
    content.push({ text: 'Stakeholders', fontSize: 10, bold: true, color: colors.sky.text, margin: [0, 8, 0, 4] });
    content.push(bulletList(roadmap.enablers_and_dependencies.stakeholders));

    // Risks & Mitigation
    content.push(sectionBlock('Risks & Mitigation', colors.rose));
    content.push(risksTable(roadmap.risks_and_mitigation));

    // Key Metrics & Milestones
    content.push(sectionBlock('Key Metrics & Milestones', colors.violet));
    content.push(...metricsContent(roadmap.key_metrics_and_milestones));

    // Future Opportunities
    if (roadmap.future_opportunities?.length > 0) {
        content.push(sectionBlock('Future Opportunities', colors.sky));
        content.push(bulletList(roadmap.future_opportunities));
    }

    // Additional Insights
    if (roadmap.llm_inferred_additions?.length > 0) {
        content.push(sectionBlock('Additional Insights', colors.muted));
        roadmap.llm_inferred_additions.forEach((a) => {
            content.push(card([
                { text: sanitizeText(a.section_title), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
                { text: sanitizeText(a.content), fontSize: 10, color: colors.slate600 },
            ]));
        });
    }

    return {
        info: {
            title: `${roadmap.roadmap_title} - Strategic Roadmap`,
            author: 'Knowledge Synthesis Platform',
            subject: 'Strategic Roadmap',
            keywords: 'roadmap, strategy, milestones, risks, enablers',
        },
        pageMargins: [40, 60, 40, 60],
        footer: (currentPage: number, pageCount: number) => ({
            columns: [
                { text: date, color: colors.slate500 },
                { text: `${currentPage} / ${pageCount}`, alignment: 'right', color: colors.slate500 },
            ],
            margin: [40, 10, 40, 0],
        }),
        content,
        defaultStyle: {
            fontSize: 10,
            color: colors.slate800,
        },
    };
}

export function downloadStrategicRoadmapPdf(roadmap: StrategicRoadmapLLMOutput, filename?: string) {
    const doc = buildDocDefinition(roadmap);
    const name = filename || `${roadmap.roadmap_title.replace(/[^a-z0-9\-\s]/gi, '').trim() || 'strategic-roadmap'}.pdf`;
    pdfMake.createPdf(doc).download(name);
}
