/* eslint-disable @typescript-eslint/no-explicit-any */
// Keep pdfmake types loose to avoid environment-specific resolution issues
type TDocumentDefinitions = any;
type Content = any;
type TableCell = any;

import pdfMake from 'pdfmake/build/pdfmake';
import 'pdfmake/build/vfs_fonts';
import type { TechnicalRoadmapLLMOutput } from './api';

// Initialize virtual file system for fonts (required by pdfmake in browser)
const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

const colors = {
    primary: '#0EA5E9', // sky-500
    accent1: '#7C3AED', // violet-600
    accent2: '#D946EF', // fuchsia-500
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
        .replace(/\u202F/g, ' ')
        .replace(/’/g, "'")
        .replace(/‑/g, '-');
}

function bulletList(items: string[] = [], options?: { color?: string; margin?: [number, number, number, number] }): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        ul: items.map((i) => ({ text: sanitizeText(i), margin: [0, 2, 0, 2] })),
        color: options?.color || colors.slate800,
        margin: options?.margin || [0, 4, 0, 0],
    } as Content;
}

function sectionHeader(title: string, color: string = colors.primary): Content {
    return { text: sanitizeText(title), style: 'sectionTitle', color, alignment: 'center', margin: [0, 12, 0, 6] } as Content;
}

function phasedCard(label: string, phase: TechnicalRoadmapLLMOutput['phased_roadmap']['short_term']): Content {
    // Do NOT prefix with a bullet here because bulletList() renders the list bullets already.
    const initiatives = phase.key_initiatives.map((it) => `${it.initiative}: ${it.objective} (Outcome: ${it.expected_outcome})`);
    return {
        table: {
            widths: ['*'],
            body: [[{
                stack: [
                    { columns: [{ text: sanitizeText(label), style: 'phaseTitle', color: colors.accent2 }, { text: sanitizeText(phase.time_frame), alignment: 'right', color: colors.slate600 }] },
                    { canvas: [{ type: 'line', x1: 0, y1: 2, x2: 515, y2: 2, lineWidth: 0.5, lineColor: colors.border }] },
                    { text: 'Focus Areas', style: 'subheading' },
                    bulletList(phase.focus_areas),
                    { text: 'Initiatives', style: 'subheading' },
                    bulletList(initiatives),
                    { text: 'Dependencies', style: 'subheading' },
                    bulletList(phase.dependencies),
                ],
                border: [false, false, false, false],
                margin: [8, 8, 8, 8],
            }]],
        },
        layout: {
            hLineWidth: () => 0.8,
            vLineWidth: () => 0.8,
            hLineColor: () => colors.border,
            vLineColor: () => colors.border,
        },
        margin: [0, 6, 0, 0],
    } as Content;
}

function risksTable(risks: TechnicalRoadmapLLMOutput['risks_and_mitigations']): Content {
    const body: TableCell[][] = [[
        { text: 'Risk', style: 'tableHeader', color: colors.slate800 },
        { text: 'Mitigation', style: 'tableHeader', color: colors.slate800 },
    ]];
    risks.forEach((r) => {
        body.push([
            { text: sanitizeText(r.risk), margin: [0, 3, 0, 3] },
            { text: sanitizeText(r.mitigation), margin: [0, 3, 0, 3] },
        ]);
    });
    return {
        table: { widths: ['*', '*'], body },
        layout: {
            fillColor: (rowIndex: number) => (rowIndex === 0 ? '#F8FAFC' : undefined),
            hLineColor: () => colors.border,
            vLineColor: () => colors.border,
        },
        margin: [0, 6, 0, 0],
    };
}

function domainsContent(domains: TechnicalRoadmapLLMOutput['technology_domains']): Content {
    const rows: Content[] = domains.map((d) => ({
        stack: [
            { text: sanitizeText(d.domain_name), style: 'pillTitle', color: colors.accent1 },
            { text: sanitizeText(d.description), margin: [0, 2, 0, 0], color: colors.slate800 },
        ],
        margin: [0, 4, 0, 4],
    }));
    // two columns
    const left: Content[] = []; const right: Content[] = [];
    rows.forEach((c, i) => (i % 2 === 0 ? left.push(c) : right.push(c)));
    return { columns: [left, right], columnGap: 16 };
}

function tabularSummaryTable(rows: TechnicalRoadmapLLMOutput['tabular_summary']): Content {
    const body: TableCell[][] = [[
        { text: 'Time Frame', style: 'tableHeader', color: colors.slate800 },
        { text: 'Key Points', style: 'tableHeader', color: colors.slate800 },
    ]];
    rows.forEach((r) => {
        body.push([
            { text: sanitizeText(r.time_frame), margin: [0, 3, 0, 3] },
            { stack: (r.key_points || []).map((p) => ({ text: sanitizeText(p), margin: [0, 1, 0, 1] })) },
        ]);
    });
    return {
        table: { widths: ['25%', '75%'], body },
        layout: { hLineColor: () => colors.border, vLineColor: () => colors.border },
        margin: [0, 6, 0, 0],
    };
}

function buildDocDefinition(roadmap: TechnicalRoadmapLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    return {
        info: {
            title: `${roadmap.roadmap_title} - Technical Roadmap`,
            author: 'NotebookLM',
            subject: 'Technical Roadmap',
            keywords: 'technical roadmap, enablers, risks, phases',
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
                    { text: 'Technical roadmap with vision, domains, phased plan, enablers, and risks.', style: 'subtitle', alignment: 'center' },
                ],
                margin: [0, 0, 0, 10],
            },

            // Vision
            sectionHeader('Overall Vision', colors.success),
            { text: sanitizeText(roadmap.overall_vision.goal), margin: [0, 2, 0, 4] },
            bulletList(roadmap.overall_vision.success_metrics),

            // Current State
            sectionHeader('Current State Analysis', colors.primary),
            { text: sanitizeText(roadmap.current_state_analysis.summary), margin: [0, 2, 0, 4] },
            {
                columns: [
                    { stack: [{ text: 'Key Challenges', style: 'subheading' }, bulletList(roadmap.current_state_analysis.key_challenges)] },
                    { stack: [{ text: 'Existing Capabilities', style: 'subheading' }, bulletList(roadmap.current_state_analysis.existing_capabilities)] },
                ], columnGap: 16
            },

            // Domains
            sectionHeader('Technology Domains', colors.accent1),
            domainsContent(roadmap.technology_domains),

            // Phases
            sectionHeader('Phased Technical Roadmap', colors.accent2),
            phasedCard('Short Term', roadmap.phased_roadmap.short_term),
            phasedCard('Mid Term', roadmap.phased_roadmap.mid_term),
            phasedCard('Long Term', roadmap.phased_roadmap.long_term),

            // Enablers
            sectionHeader('Key Technology Enablers', colors.primary),
            bulletList(roadmap.key_technology_enablers.map((e) => `${e.enabler}: ${e.impact}`)),

            // Risks
            sectionHeader('Risks & Mitigation', colors.danger),
            risksTable(roadmap.risks_and_mitigations),

            // Innovation
            sectionHeader('Innovation Opportunities', colors.primary),
            ...roadmap.innovation_opportunities.map((iop) => ({
                stack: [
                    { text: sanitizeText(`${iop.idea} (${iop.maturity_level})`), style: 'subheading', color: colors.accent1 },
                    { text: sanitizeText(iop.description), margin: [0, 2, 0, 6] },
                ],
            })),

            // Summary table
            sectionHeader('Tabular Summary', colors.accent1),
            tabularSummaryTable(roadmap.tabular_summary),

            // LLM additions
            ...(roadmap.llm_inferred_additions && roadmap.llm_inferred_additions.length > 0
                ? [sectionHeader('LLM Inferred Additions', colors.slate600), ...roadmap.llm_inferred_additions.map((a) => ({
                    stack: [
                        { text: sanitizeText(a.section_title), style: 'subheading', color: colors.slate800 },
                        { text: sanitizeText(a.content), margin: [0, 2, 0, 6] },
                    ],
                }))]
                : []),
        ],
        styles: {
            title: { fontSize: 20, bold: true, color: colors.slate800, margin: [0, 0, 0, 4] },
            subtitle: { fontSize: 10, color: colors.slate600 },
            sectionTitle: { fontSize: 13, bold: true },
            phaseTitle: { fontSize: 11, bold: true },
            subheading: { fontSize: 11, bold: true, margin: [0, 6, 0, 2] },
            pillTitle: { fontSize: 11, bold: true },
            tableHeader: { bold: true, fillColor: '#F3F4F6', margin: [0, 4, 0, 4] },
        },
        defaultStyle: { fontSize: 10, color: colors.slate800 },
    };
}

export function downloadTechnicalRoadmapPdf(roadmap: TechnicalRoadmapLLMOutput, filename?: string) {
    const doc = buildDocDefinition(roadmap);
    const safe = roadmap.roadmap_title?.replace(/[^a-z0-9\-\s]/gi, '').trim() || 'technical-roadmap';
    const name = filename || `${safe}.pdf`;
    pdfMake.createPdf(doc).download(name);
}
