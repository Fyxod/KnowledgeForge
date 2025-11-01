/* eslint-disable @typescript-eslint/no-explicit-any */
// Some environments don't ship pdfmake type paths identically; use loose types to avoid TS resolution errors.
type TDocumentDefinitions = any;
type Content = any;
type TableCell = any;

// Import pdfmake (browser build) and its default font VFS shim.
// The vfs shim registers fonts on the global pdfMake; we then copy it onto the imported instance.
import pdfMake from 'pdfmake/build/pdfmake';
import 'pdfmake/build/vfs_fonts';
import type { StrategicRoadmapLLMOutput } from './api';

// Initialize virtual file system for fonts (required by pdfmake in browser)
const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

const colors = {
    primary: '#6D28D9', // violet-700
    accent1: '#D946EF', // fuchsia-500
    accent2: '#0EA5E9', // sky-500
    success: '#10B981',
    warning: '#F59E0B',
    danger: '#EF4444',
    slate600: '#475569',
    slate800: '#1F2937',
    slate500: '#64748B',
    border: '#E5E7EB',
};

function sanitizeText(s: string | undefined | null): string {
    if (!s) return '';
    return String(s)
        .replace(/≥/g, '>=')
        .replace(/≤/g, '<=')
        .replace(/×/g, 'x')
        .replace(/±/g, '+/-')
        .replace(/[–—]/g, '-')
        .replace(/[“”]/g, '"')
        .replace(/\u202F/g, " ")
        .replace(/’/g, "'")
        .replace(/‑/g, "-");
}

function bulletList(items: string[] = [], options?: { color?: string; margin?: [number, number, number, number] }): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        ul: items.map((i) => ({ text: sanitizeText(i), margin: [0, 2, 0, 2] })),
        color: options?.color || colors.slate800,
        margin: options?.margin || [0, 4, 0, 0],
    } as Content;
}

function swotTable(swot: StrategicRoadmapLLMOutput['current_baseline']['swot']): Content {
    const cell = (title: string, points: string[], color: string): TableCell => ({
        stack: [
            { text: title, style: 'swotTitle', color },
            bulletList(points, { color: colors.slate800 }),
        ],
        border: [true, true, true, true],
    });

    return {
        table: {
            widths: ['*', '*'],
            body: [
                [cell('Strengths', swot.strengths, colors.success), cell('Weaknesses', swot.weaknesses, colors.warning)],
                [cell('Opportunities', swot.opportunities, colors.accent2), cell('Threats', swot.threats, colors.danger)],
            ],
        },
        layout: {
            paddingLeft: () => 10,
            paddingRight: () => 10,
            paddingTop: () => 8,
            paddingBottom: () => 8,
            hLineColor: () => colors.border,
            vLineColor: () => colors.border,
        },
        margin: [0, 6, 0, 0],
    };
}

function sectionHeader(title: string, color: string = colors.primary): Content {
    return {
        text: sanitizeText(title),
        style: 'sectionTitle',
        color,
        alignment: 'center',
        margin: [0, 12, 0, 6],
    } as Content;
}

function phasedRoadmap(phases: StrategicRoadmapLLMOutput['phased_roadmap']): Content[] {
    const cards: Content[] = [];
    phases.forEach((ph) => {
        cards.push({
            table: {
                widths: ['*'],
                body: [
                    [
                        {
                            stack: [
                                { columns: [{ text: sanitizeText(ph.phase), style: 'phaseTitle', color: colors.accent1 }, { text: sanitizeText(ph.time_frame), alignment: 'right', color: colors.slate600 }] },
                                { canvas: [{ type: 'line', x1: 0, y1: 2, x2: 515, y2: 2, lineWidth: 0.5, lineColor: colors.border }] },
                                { text: 'Objectives', style: 'subheading' },
                                bulletList(ph.key_objectives),
                                { text: 'Initiatives', style: 'subheading' },
                                bulletList(ph.key_initiatives),
                                { text: 'Expected Outcomes', style: 'subheading' },
                                bulletList(ph.expected_outcomes),
                            ],
                            border: [false, false, false, false],
                            margin: [8, 8, 8, 8],
                        } as any,
                    ],
                ],
            },
            layout: {
                hLineWidth: () => 0.8,
                vLineWidth: () => 0.8,
                hLineColor: () => colors.border,
                vLineColor: () => colors.border,
            },
            margin: [0, 6, 0, 0],
        });
    });
    return cards;
}

function risksTable(risks: StrategicRoadmapLLMOutput['risks_and_mitigation']): Content {
    const body: TableCell[][] = [
        [
            { text: 'Risk', style: 'tableHeader', color: colors.slate800 },
            { text: 'Mitigation', style: 'tableHeader', color: colors.slate800 },
        ],
    ];
    risks.forEach((r) => {
        body.push([
            { text: sanitizeText(r.risk), margin: [0, 3, 0, 3] },
            { text: sanitizeText(r.mitigation_strategy), margin: [0, 3, 0, 3] },
        ]);
    });
    return {
        table: {
            widths: ['*', '*'],
            body,
        },
        layout: {
            fillColor: (rowIndex: number) => (rowIndex === 0 ? '#F8FAFC' : undefined),
            hLineColor: () => colors.border,
            vLineColor: () => colors.border,
        },
        margin: [0, 6, 0, 0],
    };
}

function metricsContent(metrics: StrategicRoadmapLLMOutput['key_metrics_and_milestones']): Content[] {
    return metrics.map((m) => ({
        stack: [
            { text: sanitizeText(m.year_or_phase), style: 'subheading', color: colors.accent2, alignment: 'left' },
            bulletList(m.metrics),
        ],
        margin: [0, 4, 0, 0],
    }));
}

function pillarsContent(pillars: StrategicRoadmapLLMOutput['strategic_pillars']): Content {
    const cols: Content[] = pillars.map((p) => ({
        stack: [
            { text: sanitizeText(p.pillar_name), style: 'pillTitle', color: colors.primary },
            { text: sanitizeText(p.description), margin: [0, 2, 0, 0], color: colors.slate800 },
        ],
        margin: [0, 4, 0, 4],
    }));
    // Arrange into two columns
    const left: Content[] = [];
    const right: Content[] = [];
    cols.forEach((c, i) => (i % 2 === 0 ? left.push(c) : right.push(c)));
    return { columns: [left, right], columnGap: 16 };
}

function buildDocDefinition(roadmap: StrategicRoadmapLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    return {
        info: {
            title: `${roadmap.roadmap_title} - Strategic Roadmap`,
            author: 'NotebookLM',
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
        content: [
            // Title
            {
                stack: [
                    { text: sanitizeText(roadmap.roadmap_title), style: 'title', alignment: 'center' },
                    { text: 'Strategic, phased plan with goals, enablers, risks, and measurable milestones.', style: 'subtitle', alignment: 'center' },
                ],
                margin: [0, 0, 0, 10],
            },

            // Vision & Baseline
            sectionHeader('Vision & End Goal', colors.success),
            { text: sanitizeText(roadmap.vision_and_end_goal.description), margin: [0, 2, 0, 4] },
            bulletList(roadmap.vision_and_end_goal.success_criteria),

            sectionHeader('Current Baseline', colors.accent2),
            { text: sanitizeText(roadmap.current_baseline.summary), margin: [0, 2, 0, 4] },
            swotTable(roadmap.current_baseline.swot),

            // Pillars
            sectionHeader('Strategic Pillars', colors.primary),
            pillarsContent(roadmap.strategic_pillars),

            // Phased Roadmap
            sectionHeader('Phased Strategic Roadmap', colors.accent1),
            ...phasedRoadmap(roadmap.phased_roadmap),

            // Enablers & Dependencies
            sectionHeader('Enablers & Dependencies', colors.primary),
            {
                columns: [
                    { stack: [{ text: 'Technologies', style: 'subheading' }, bulletList(roadmap.enablers_and_dependencies.technologies)] },
                    { stack: [{ text: 'Skills & Resources', style: 'subheading' }, bulletList(roadmap.enablers_and_dependencies.skills_and_resources)] },
                ],
                columnGap: 16,
            },
            { stack: [{ text: 'Stakeholders', style: 'subheading' }, bulletList(roadmap.enablers_and_dependencies.stakeholders)] },

            // Risks
            sectionHeader('Risks & Mitigation', colors.danger),
            risksTable(roadmap.risks_and_mitigation),

            // Metrics & Milestones
            sectionHeader('Key Metrics & Milestones', colors.accent2),
            ...metricsContent(roadmap.key_metrics_and_milestones),

            // Future & Additions
            sectionHeader('Future Opportunities', colors.accent2),
            bulletList(roadmap.future_opportunities),

            sectionHeader('Additional Insights', colors.slate600),
            ...roadmap.llm_inferred_additions.map((a) => ({
                stack: [{ text: sanitizeText(a.section_title), style: 'subheading', color: colors.slate800 }, { text: sanitizeText(a.content), margin: [0, 2, 0, 6] }],
            })),
        ],
        styles: {
            title: { fontSize: 20, bold: true, color: colors.slate800, margin: [0, 0, 0, 4] },
            subtitle: { fontSize: 10, color: colors.slate600 },
            sectionTitle: { fontSize: 13, bold: true },
            swotTitle: { fontSize: 11, bold: true },
            phaseTitle: { fontSize: 11, bold: true },
            subheading: { fontSize: 11, bold: true, margin: [0, 6, 0, 2] },
            pillTitle: { fontSize: 11, bold: true },
            tableHeader: { bold: true, fillColor: '#F3F4F6', margin: [0, 4, 0, 4] },
        },
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
