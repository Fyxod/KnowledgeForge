/* eslint-disable @typescript-eslint/no-explicit-any */
// Loose types to avoid TS issues with pdfmake ambient types in Vite builds
type TDocumentDefinitions = any;
type Content = any;

// Import pdfmake (browser build) and its default font VFS shim
import pdfMake from 'pdfmake/build/pdfmake';
import 'pdfmake/build/vfs_fonts';
import type { InsightsLLMOutput } from './api';

// Initialize virtual file system for fonts (required by pdfmake in browser)
const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

// ── Color palette (matches UI Tailwind colors) ──────────────────────────────
const colors = {
    // Banner
    bannerBg: '#F97316',      // orange-500
    // Section tones: [lightBg, darkText]
    amber:   { bg: '#FEF3C7', text: '#B45309' },
    violet:  { bg: '#EDE9FE', text: '#6D28D9' },
    emerald: { bg: '#D1FAE5', text: '#047857' },
    rose:    { bg: '#FFE4E6', text: '#BE123C' },
    pink:    { bg: '#FCE7F3', text: '#BE185D' },
    sky:     { bg: '#E0F2FE', text: '#0369A1' },
    muted:   { bg: '#F1F5F9', text: '#475569' },
    // General
    slate600: '#475569',
    slate800: '#1F2937',
    slate500: '#64748B',
    border:   '#E2E8F0',
    codeBg:   '#F1F5F9',
};

function sanitizeText(s: string | undefined | null): string {
    if (!s) return '';
    return String(s)
        .replace(/≥/g, '>=')
        .replace(/≤/g, '<=')
        .replace(/×/g, 'x')
        .replace(/±/g, '+/-')
        .replace(/[–—]/g, '-')
        .replace(/[""]/g, '"')
        .replace(/\u202F/g, ' ')
        .replace(/'/g, "'")
        .replace(/‑/g, '-');
}

// ── PDF helpers matching UI visual style ────────────────────────────────────

/** Colored banner block (single-cell table with fill) */
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

/** Pill badges — inline text with colored backgrounds */
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

function keyDiscussionPoints(points: InsightsLLMOutput['key_discussion_points']): Content[] {
    if (!points || points.length === 0) return [];
    return points.map((p) =>
        card([
            { text: sanitizeText(p.topic), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
            { text: sanitizeText(p.details), fontSize: 10, color: colors.slate600 },
        ]),
    );
}

function strengthsContent(items: InsightsLLMOutput['strengths']): Content[] {
    if (!items || items.length === 0) return [];
    return items.map((st) =>
        card([
            { text: sanitizeText(st.aspect), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
            { text: sanitizeText(st.evidence_or_example), fontSize: 10, color: colors.slate600 },
        ], '#A7F3D0'), // emerald-200
    );
}

function gapsContent(items: InsightsLLMOutput['improvement_or_missing_areas']): Content {
    if (!items || items.length === 0) return { text: '' };
    const body: any[] = [
        [
            { text: 'Gap', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
            { text: 'Suggested Improvement', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
        ],
    ];
    items.forEach((gi) => {
        body.push([
            { text: sanitizeText(gi.gap), margin: [4, 4, 4, 4] },
            { text: sanitizeText(gi.suggested_improvement), margin: [4, 4, 4, 4] },
        ]);
    });
    return {
        table: { widths: ['*', '*'], body },
        layout: {
            hLineColor: () => '#FECDD3', // rose-200
            vLineColor: () => '#FECDD3',
            hLineWidth: () => 0.75,
            vLineWidth: () => 0.75,
        },
        margin: [0, 6, 0, 0],
    };
}

function innovationsContent(items: InsightsLLMOutput['innovation_aspects']): Content[] {
    if (!items || items.length === 0) return [];
    return items.map((i) =>
        card([
            { text: sanitizeText(i.innovation_title), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
            { text: sanitizeText(i.description), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 3] },
            { text: `Potential Impact: ${sanitizeText(i.potential_impact)}`, fontSize: 9, color: colors.pink.text, italics: true },
        ], '#FBCFE8'), // pink-200
    );
}

function futureContent(items: InsightsLLMOutput['future_considerations']): Content[] {
    if (!items || items.length === 0) return [];
    return items.map((f) =>
        card([
            { text: sanitizeText(f.focus_area), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
            { text: sanitizeText(f.recommendation), fontSize: 10, color: colors.slate600 },
        ], '#BAE6FD'), // sky-200
    );
}

function pseudocodeContent(items: InsightsLLMOutput['pseudocode_or_technical_outline']): Content[] {
    if (!items || items.length === 0) return [];
    return items.map((p) => ({
        stack: [
            ...(p.section ? [{ text: sanitizeText(p.section), fontSize: 11, bold: true, margin: [0, 0, 0, 4] as any }] : []),
            ...(p.pseudocode ? [{
                table: {
                    widths: ['*'],
                    body: [[{
                        text: sanitizeText(p.pseudocode),
                        fontSize: 9, color: colors.slate800,
                        fillColor: colors.codeBg,
                        margin: [8, 6, 8, 6],
                    }]],
                },
                layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
            }] : []),
        ],
        margin: [0, 2, 0, 6],
    }));
}

function additionsContent(items: InsightsLLMOutput['llm_inferred_additions']): Content[] {
    if (!items || items.length === 0) return [];
    return items.map((a) =>
        card([
            { text: sanitizeText(a.section_title), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
            { text: sanitizeText(a.content), fontSize: 10, color: colors.slate600 },
        ]),
    );
}

// ── Document definition builder ─────────────────────────────────────────────

function buildDocDefinition(insights: InsightsLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    const title = insights?.document_summary?.title || 'Insights';
    const purpose = insights?.document_summary?.purpose || '';

    const content: Content[] = [];

    // Banner
    content.push(banner(title, 'Synthesis of discussion points, strengths, gaps, innovations, and next steps.'));

    // Document Summary
    if (purpose || (insights.document_summary?.key_themes?.length > 0)) {
        content.push(sectionBlock('Document Summary', colors.amber));
        if (purpose) {
            content.push({ text: sanitizeText(purpose), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });
        }
        if (insights.document_summary?.key_themes?.length > 0) {
            content.push({ text: 'Key Themes', fontSize: 10, bold: true, color: colors.slate800, margin: [0, 4, 0, 4] });
            content.push(pills(insights.document_summary.key_themes, colors.amber));
        }
    }

    // Key Discussion Points
    if (insights.key_discussion_points && insights.key_discussion_points.length > 0) {
        content.push(sectionBlock('Key Discussion Points', colors.violet));
        content.push(...keyDiscussionPoints(insights.key_discussion_points));
    }

    // Strengths
    if (insights.strengths && insights.strengths.length > 0) {
        content.push(sectionBlock('Strengths', colors.emerald));
        content.push(...strengthsContent(insights.strengths));
    }

    // Gaps & Improvements
    if (insights.improvement_or_missing_areas && insights.improvement_or_missing_areas.length > 0) {
        content.push(sectionBlock('Gaps & Improvements', colors.rose));
        content.push(gapsContent(insights.improvement_or_missing_areas));
    }

    // Innovation Aspects
    if (insights.innovation_aspects && insights.innovation_aspects.length > 0) {
        content.push(sectionBlock('Innovation Aspects', colors.pink));
        content.push(...innovationsContent(insights.innovation_aspects));
    }

    // Future Considerations
    if (insights.future_considerations && insights.future_considerations.length > 0) {
        content.push(sectionBlock('Future Considerations', colors.sky));
        content.push(...futureContent(insights.future_considerations));
    }

    // Pseudocode / Technical Outline
    if (insights.pseudocode_or_technical_outline && insights.pseudocode_or_technical_outline.length > 0) {
        content.push(sectionBlock('Pseudocode / Technical Outline', colors.violet));
        content.push(...pseudocodeContent(insights.pseudocode_or_technical_outline));
    }

    // Additional Insights
    if (insights.llm_inferred_additions && insights.llm_inferred_additions.length > 0) {
        content.push(sectionBlock('Additional Insights', colors.muted));
        content.push(...additionsContent(insights.llm_inferred_additions));
    }

    return {
        info: {
            title: `${title} - Insights`,
            author: 'Knowledge Synthesis Platform',
            subject: 'Insights',
            keywords: 'insights, analysis, summary',
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

export function downloadInsightsPdf(insights: InsightsLLMOutput, filename?: string) {
    const doc = buildDocDefinition(insights);
    const safe = (insights?.document_summary?.title || 'insights').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'insights';
    const name = filename || `${safe} - Insights.pdf`;
    pdfMake.createPdf(doc).download(name);
}
