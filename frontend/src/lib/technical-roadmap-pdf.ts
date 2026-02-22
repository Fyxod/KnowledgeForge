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

// ── Color palette (matches UI Tailwind colors) ──────────────────────────────
const colors = {
    // Banner
    bannerBg: '#0284C7',      // sky-600
    // Section tones
    sky:     { bg: '#E0F2FE', text: '#0369A1' },
    emerald: { bg: '#D1FAE5', text: '#047857' },
    violet:  { bg: '#EDE9FE', text: '#6D28D9' },
    fuchsia: { bg: '#FAE8FF', text: '#A21CAF' },
    rose:    { bg: '#FFE4E6', text: '#BE123C' },
    muted:   { bg: '#F1F5F9', text: '#475569' },
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

function card(content: Content[], borderColor: string = colors.border): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{ stack: content, margin: [8, 8, 8, 8] }]],
        },
        layout: {
            hLineWidth: () => 0.75, vLineWidth: () => 0.75,
            hLineColor: () => borderColor, vLineColor: () => borderColor,
        },
        margin: [0, 3, 0, 3],
    };
}

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

function phasedCard(label: string, phase: TechnicalRoadmapLLMOutput['phased_roadmap']['short_term']): Content {
    const initiatives = phase.key_initiatives.map((it) => `${it.initiative}: ${it.objective} (Outcome: ${it.expected_outcome})`);
    return {
        table: {
            widths: ['*'],
            body: [[{
                stack: [
                    {
                        columns: [
                            { text: sanitizeText(label), fontSize: 11, bold: true, color: colors.fuchsia.text },
                            { text: sanitizeText(phase.time_frame), fontSize: 10, alignment: 'right', color: colors.slate600 },
                        ],
                    },
                    { canvas: [{ type: 'line', x1: 0, y1: 2, x2: 490, y2: 2, lineWidth: 0.5, lineColor: colors.border }] },
                    { text: 'Focus Areas', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 6, 0, 2] },
                    bulletList(phase.focus_areas),
                    { text: 'Initiatives', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 6, 0, 2] },
                    bulletList(initiatives),
                    { text: 'Dependencies', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 6, 0, 2] },
                    bulletList(phase.dependencies),
                ],
                margin: [8, 8, 8, 8],
            }]],
        },
        layout: {
            hLineWidth: () => 0.75, vLineWidth: () => 0.75,
            hLineColor: () => '#E9D5FF', vLineColor: () => '#E9D5FF',
        },
        margin: [0, 6, 0, 0],
    };
}

function risksTable(risks: TechnicalRoadmapLLMOutput['risks_and_mitigations']): Content {
    const body: TableCell[][] = [[
        { text: 'Risk', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
        { text: 'Mitigation', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
    ]];
    risks.forEach((r) => {
        body.push([
            { text: sanitizeText(r.risk), margin: [4, 4, 4, 4] },
            { text: sanitizeText(r.mitigation), margin: [4, 4, 4, 4] },
        ]);
    });
    return {
        table: { widths: ['*', '*'], body },
        layout: {
            hLineColor: () => '#FECDD3', vLineColor: () => '#FECDD3',
            hLineWidth: () => 0.75, vLineWidth: () => 0.75,
        },
        margin: [0, 6, 0, 0],
    };
}

function domainsContent(domains: TechnicalRoadmapLLMOutput['technology_domains']): Content[] {
    return domains.map((d) =>
        card([
            { text: sanitizeText(d.domain_name), fontSize: 11, bold: true, color: colors.emerald.text, margin: [0, 0, 0, 3] },
            { text: sanitizeText(d.description), fontSize: 10, color: colors.slate600 },
        ], '#A7F3D0'), // emerald-200
    );
}

function tabularSummaryTable(rows: TechnicalRoadmapLLMOutput['tabular_summary']): Content {
    const body: TableCell[][] = [[
        { text: 'Time Frame', bold: true, fillColor: colors.violet.bg, color: colors.violet.text, margin: [4, 4, 4, 4] },
        { text: 'Key Points', bold: true, fillColor: colors.violet.bg, color: colors.violet.text, margin: [4, 4, 4, 4] },
    ]];
    rows.forEach((r) => {
        body.push([
            { text: sanitizeText(r.time_frame), margin: [4, 4, 4, 4] },
            { stack: (r.key_points || []).map((p) => ({ text: sanitizeText(p), margin: [0, 1, 0, 1] })), margin: [4, 4, 4, 4] },
        ]);
    });
    return {
        table: { widths: ['25%', '75%'], body },
        layout: {
            hLineColor: () => '#DDD6FE', vLineColor: () => '#DDD6FE',
            hLineWidth: () => 0.75, vLineWidth: () => 0.75,
        },
        margin: [0, 6, 0, 0],
    };
}

// ── Document definition builder ─────────────────────────────────────────────

function buildDocDefinition(roadmap: TechnicalRoadmapLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    const content: Content[] = [];

    // Banner
    content.push(banner(roadmap.roadmap_title, 'Technical roadmap with vision, domains, phased plan, enablers, and risks.'));

    // Overall Vision
    content.push(sectionBlock('Overall Vision', colors.sky));
    content.push({ text: sanitizeText(roadmap.overall_vision.goal), fontSize: 10, color: colors.slate600, margin: [0, 2, 0, 4] });
    if (roadmap.overall_vision.success_metrics?.length > 0) {
        content.push({ text: 'Success Metrics', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 4, 0, 4] });
        content.push(pills(roadmap.overall_vision.success_metrics, colors.emerald));
    }

    // Current State Analysis
    content.push(sectionBlock('Current State Analysis', colors.sky));
    content.push({ text: sanitizeText(roadmap.current_state_analysis.summary), fontSize: 10, color: colors.slate600, margin: [0, 2, 0, 4] });
    content.push({
        columns: [
            {
                stack: [
                    { text: 'Key Challenges', fontSize: 10, bold: true, color: colors.rose.text, margin: [0, 0, 0, 4] },
                    bulletList(roadmap.current_state_analysis.key_challenges),
                ],
            },
            {
                stack: [
                    { text: 'Existing Capabilities', fontSize: 10, bold: true, color: colors.emerald.text, margin: [0, 0, 0, 4] },
                    bulletList(roadmap.current_state_analysis.existing_capabilities),
                ],
            },
        ],
        columnGap: 16,
    });

    // Technology Domains
    content.push(sectionBlock('Technology Domains', colors.emerald));
    content.push(...domainsContent(roadmap.technology_domains));

    // Phased Technical Roadmap
    content.push(sectionBlock('Phased Technical Roadmap', colors.fuchsia));
    content.push(phasedCard('Short Term', roadmap.phased_roadmap.short_term));
    content.push(phasedCard('Mid Term', roadmap.phased_roadmap.mid_term));
    content.push(phasedCard('Long Term', roadmap.phased_roadmap.long_term));

    // Key Technology Enablers
    content.push(sectionBlock('Key Technology Enablers', colors.violet));
    const enablerPills = roadmap.key_technology_enablers.map((e) => `${e.enabler}: ${e.impact}`);
    content.push(bulletList(enablerPills));

    // Risks & Mitigation
    content.push(sectionBlock('Risks & Mitigation', colors.rose));
    content.push(risksTable(roadmap.risks_and_mitigations));

    // Innovation Opportunities
    if (roadmap.innovation_opportunities?.length > 0) {
        content.push(sectionBlock('Innovation Opportunities', colors.sky));
        roadmap.innovation_opportunities.forEach((iop) => {
            content.push(card([
                { text: sanitizeText(iop.idea), fontSize: 11, bold: true, color: colors.sky.text, margin: [0, 0, 0, 3] },
                { text: sanitizeText(iop.description), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 3] },
                { text: `Maturity: ${sanitizeText(iop.maturity_level)}`, fontSize: 9, color: colors.violet.text, italics: true },
            ], '#BAE6FD')); // sky-200
        });
    }

    // Tabular Summary
    if (roadmap.tabular_summary?.length > 0) {
        content.push(sectionBlock('Tabular Summary', colors.violet));
        content.push(tabularSummaryTable(roadmap.tabular_summary));
    }

    // LLM Inferred Additions
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
            title: `${roadmap.roadmap_title} - Technical Roadmap`,
            author: 'Knowledge Synthesis Platform',
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
        content,
        defaultStyle: { fontSize: 10, color: colors.slate800 },
    };
}

export function downloadTechnicalRoadmapPdf(roadmap: TechnicalRoadmapLLMOutput, filename?: string) {
    const doc = buildDocDefinition(roadmap);
    const safe = roadmap.roadmap_title?.replace(/[^a-z0-9\-\s]/gi, '').trim() || 'technical-roadmap';
    const name = filename || `${safe}.pdf`;
    pdfMake.createPdf(doc).download(name);
}
