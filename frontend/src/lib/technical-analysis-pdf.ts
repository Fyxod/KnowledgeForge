/* eslint-disable @typescript-eslint/no-explicit-any */
type TDocumentDefinitions = any;
type Content = any;

import pdfMake from 'pdfmake/build/pdfmake';
import 'pdfmake/build/vfs_fonts';
import type { TechnicalAnalysisLLMOutput } from './api';

const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

// ── Color palette ──────────────────────────────────────────────────────────
const colors = {
    bannerBg: '#6366F1',      // indigo-500
    indigo:  { bg: '#E0E7FF', text: '#4338CA' },
    violet:  { bg: '#EDE9FE', text: '#6D28D9' },
    emerald: { bg: '#D1FAE5', text: '#047857' },
    amber:   { bg: '#FEF3C7', text: '#B45309' },
    sky:     { bg: '#E0F2FE', text: '#0369A1' },
    rose:    { bg: '#FFE4E6', text: '#BE123C' },
    muted:   { bg: '#F1F5F9', text: '#475569' },
    slate600: '#475569',
    slate800: '#1F2937',
    slate500: '#64748B',
    border:   '#E2E8F0',
};

function sanitizeText(s: string | undefined | null): string {
    if (!s) return '';
    return String(s)
        .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/×/g, 'x')
        .replace(/±/g, '+/-').replace(/[–—]/g, '-').replace(/[""]/g, '"')
        .replace(/\u202F/g, ' ').replace(/'/g, "'").replace(/‑/g, '-');
}

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
                text: sanitizeText(title), fontSize: 13, bold: true, color: tone.text,
                fillColor: tone.bg, margin: [10, 6, 10, 6],
            }]],
        },
        layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
        margin: [0, 14, 0, 8],
    };
}

function card(content: Content[], borderColor: string = colors.border): Content {
    return {
        table: { widths: ['*'], body: [[{ stack: content, margin: [8, 8, 8, 8] }]] },
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
            text: sanitizeText(item), fontSize: 8, bold: true,
            color: tone.text, background: tone.bg, margin: [4, 3, 4, 3],
        })),
        columnGap: 6, margin: [0, 4, 0, 6],
    };
}

function partHeader(title: string, tone: { bg: string; text: string }): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{
                text: sanitizeText(title), fontSize: 12, bold: true, color: tone.text,
                fillColor: tone.bg, margin: [10, 8, 10, 8],
            }]],
        },
        layout: { hLineWidth: () => 1, vLineWidth: () => 1, hLineColor: () => tone.text, vLineColor: () => tone.text, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
        margin: [0, 16, 0, 8],
    };
}

// ── Document definition builder ─────────────────────────────────────────────
function buildDocDefinition(analysis: TechnicalAnalysisLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    const title = analysis?.analysis_title || 'Technical Analysis';

    const content: Content[] = [];

    // Banner
    content.push(banner(title, 'Technical content extraction and analytical assessment.'));

    // Executive Overview
    content.push(sectionBlock('Executive Overview', colors.indigo));
    content.push({ text: sanitizeText(analysis.executive_overview), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });

    // ── PART 1 ──
    content.push(partHeader('Part 1 — Document Content Extraction', colors.indigo));

    // Technical Scope
    content.push(sectionBlock('Technical Scope', colors.violet));
    if (analysis.technical_scope.domains_covered?.length > 0) {
        content.push({ text: 'Domains Covered', fontSize: 10, bold: true, margin: [0, 0, 0, 4] });
        content.push(pills(analysis.technical_scope.domains_covered, colors.violet));
    }
    if (analysis.technical_scope.technology_stack?.length > 0) {
        content.push({ text: 'Technology Stack', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.technical_scope.technology_stack, colors.indigo));
    }
    content.push({ text: 'Architecture Overview', fontSize: 10, bold: true, margin: [0, 4, 0, 3] });
    content.push({ text: sanitizeText(analysis.technical_scope.architecture_overview), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });

    // Technical Decisions
    if (analysis.technical_decisions?.length > 0) {
        content.push(sectionBlock('Technical Decisions', colors.amber));
        analysis.technical_decisions.forEach(d => {
            content.push(card([
                { text: sanitizeText(d.decision), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
                { text: sanitizeText(d.rationale), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 3] },
                { text: `Implications: ${sanitizeText(d.implications)}`, fontSize: 9, color: colors.amber.text, italics: true },
            ]));
        });
    }

    // Strengths & Concerns
    if (analysis.technical_strengths?.length > 0) {
        content.push(sectionBlock('Technical Strengths', colors.emerald));
        analysis.technical_strengths.forEach(s => {
            content.push(card([
                { text: sanitizeText(s.aspect), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
                { text: sanitizeText(s.evidence), fontSize: 10, color: colors.slate600 },
            ], '#A7F3D0'));
        });
    }
    if (analysis.technical_concerns?.length > 0) {
        content.push(sectionBlock('Technical Concerns', colors.rose));
        const cBody: any[] = [
            [
                { text: 'Concern', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
                { text: 'Impact', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
                { text: 'Evidence', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
            ],
        ];
        analysis.technical_concerns.forEach(c => {
            cBody.push([
                { text: sanitizeText(c.concern), margin: [4, 4, 4, 4] },
                { text: sanitizeText(c.impact), margin: [4, 4, 4, 4] },
                { text: sanitizeText(c.evidence), margin: [4, 4, 4, 4] },
            ]);
        });
        content.push({
            table: { widths: ['*', '*', '*'], body: cBody },
            layout: { hLineColor: () => '#FECDD3', vLineColor: () => '#FECDD3', hLineWidth: () => 0.75, vLineWidth: () => 0.75 },
            margin: [0, 6, 0, 0],
        });
    }

    // Innovation Elements
    if (analysis.innovation_elements?.length > 0) {
        content.push(sectionBlock('Innovation Elements', colors.violet));
        analysis.innovation_elements.forEach(i => {
            content.push(card([
                { text: `${sanitizeText(i.element)} [${sanitizeText(i.maturity)}]`, fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
                { text: sanitizeText(i.description), fontSize: 10, color: colors.slate600 },
            ], '#DDD6FE'));
        });
    }

    // Technical Aspirations
    content.push(sectionBlock('Technical Aspirations', colors.sky));
    if (analysis.technical_aspirations.stated_goals?.length > 0) {
        content.push({ text: 'Stated Goals', fontSize: 10, bold: true, margin: [0, 0, 0, 4] });
        content.push(pills(analysis.technical_aspirations.stated_goals, colors.sky));
    }
    content.push({ text: 'Implied Direction', fontSize: 10, bold: true, margin: [0, 4, 0, 3] });
    content.push({ text: sanitizeText(analysis.technical_aspirations.implied_direction), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 4] });
    content.push({ text: 'Alignment Assessment', fontSize: 10, bold: true, margin: [0, 4, 0, 3] });
    content.push({ text: sanitizeText(analysis.technical_aspirations.alignment_assessment), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });

    // Implementation Readiness
    content.push(sectionBlock('Implementation Readiness', colors.indigo));
    if (analysis.implementation_readiness.ready_components?.length > 0) {
        content.push({ text: 'Ready Components', fontSize: 10, bold: true, margin: [0, 0, 0, 4] });
        content.push(pills(analysis.implementation_readiness.ready_components, colors.emerald));
    }
    if (analysis.implementation_readiness.gaps_to_address?.length > 0) {
        content.push({ text: 'Gaps to Address', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.implementation_readiness.gaps_to_address, colors.amber));
    }
    if (analysis.implementation_readiness.dependencies?.length > 0) {
        content.push({ text: 'Dependencies', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.implementation_readiness.dependencies, colors.sky));
    }

    // ── PART 2 ──
    content.push(partHeader('Part 2 — Analytical Assessment', colors.violet));

    content.push(sectionBlock('Forward-Looking Assessment', colors.emerald));
    content.push({ text: 'Scalability Outlook', fontSize: 10, bold: true, margin: [0, 0, 0, 3] });
    content.push({ text: sanitizeText(analysis.forward_looking_assessment.scalability_outlook), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });
    content.push({ text: 'Technology Evolution', fontSize: 10, bold: true, margin: [0, 4, 0, 3] });
    content.push({ text: sanitizeText(analysis.forward_looking_assessment.technology_evolution), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });
    if (analysis.forward_looking_assessment.recommended_focus_areas?.length > 0) {
        content.push({ text: 'Recommended Focus Areas', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.forward_looking_assessment.recommended_focus_areas, colors.emerald));
    }
    content.push({ text: 'Overall Assessment', fontSize: 10, bold: true, margin: [0, 8, 0, 4] });
    content.push({ text: sanitizeText(analysis.forward_looking_assessment.overall_assessment), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });

    // Additional Insights
    if (analysis.llm_inferred_additions && analysis.llm_inferred_additions.length > 0) {
        content.push(sectionBlock('Additional Insights', colors.muted));
        analysis.llm_inferred_additions.forEach(a => {
            content.push(card([
                { text: sanitizeText(a.section_title), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
                { text: sanitizeText(a.content), fontSize: 10, color: colors.slate600 },
            ]));
        });
    }

    return {
        info: {
            title: `${title} - Technical Analysis`,
            author: 'Knowledge Synthesis Platform',
            subject: 'Technical Analysis',
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

export function downloadTechnicalAnalysisPdf(analysis: TechnicalAnalysisLLMOutput, filename?: string) {
    const doc = buildDocDefinition(analysis);
    const safe = (analysis?.analysis_title || 'technical-analysis').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'technical-analysis';
    const name = filename || `${safe} - Technical Analysis.pdf`;
    pdfMake.createPdf(doc).download(name);
}
