/* eslint-disable @typescript-eslint/no-explicit-any */
type TDocumentDefinitions = any;
type Content = any;

import pdfMake from 'pdfmake/build/pdfmake';
import 'pdfmake/build/vfs_fonts';
import type { StrategicAnalysisLLMOutput } from './api';

const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

// ── Color palette ──────────────────────────────────────────────────────────
const colors = {
    bannerBg: '#0D9488',      // teal-600
    teal:    { bg: '#CCFBF1', text: '#0F766E' },
    cyan:    { bg: '#CFFAFE', text: '#0E7490' },
    emerald: { bg: '#D1FAE5', text: '#047857' },
    amber:   { bg: '#FEF3C7', text: '#B45309' },
    violet:  { bg: '#EDE9FE', text: '#6D28D9' },
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
function buildDocDefinition(analysis: StrategicAnalysisLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    const title = analysis?.analysis_title || 'Strategic Analysis';

    const content: Content[] = [];

    // Banner
    content.push(banner(title, 'Strategic content extraction and analytical assessment.'));

    // Executive Overview
    content.push(sectionBlock('Executive Overview', colors.teal));
    content.push({ text: sanitizeText(analysis.executive_overview), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });

    // ── PART 1 ──
    content.push(partHeader('Part 1 — Document Content Extraction', colors.teal));

    // Strategic Intent
    content.push(sectionBlock('Strategic Intent', colors.emerald));
    content.push({ text: 'Vision Statement', fontSize: 10, bold: true, margin: [0, 0, 0, 3] });
    content.push({ text: sanitizeText(analysis.strategic_intent.vision_statement), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 6] });
    if (analysis.strategic_intent.stated_objectives?.length > 0) {
        content.push({ text: 'Stated Objectives', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.strategic_intent.stated_objectives, colors.emerald));
    }
    if (analysis.strategic_intent.implicit_aspirations?.length > 0) {
        content.push({ text: 'Implicit Aspirations', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.strategic_intent.implicit_aspirations, colors.teal));
    }

    // Strategic Positioning
    content.push(sectionBlock('Strategic Positioning', colors.cyan));
    const posFields = [
        { label: 'Current Position', value: analysis.strategic_positioning.current_position },
        { label: 'Target Position', value: analysis.strategic_positioning.target_position },
        { label: 'Competitive Landscape', value: analysis.strategic_positioning.competitive_landscape },
    ];
    posFields.forEach(f => {
        content.push(card([
            { text: sanitizeText(f.label), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
            { text: sanitizeText(f.value), fontSize: 10, color: colors.slate600 },
        ]));
    });

    // Key Strategic Themes
    if (analysis.key_strategic_themes?.length > 0) {
        content.push(sectionBlock('Key Strategic Themes', colors.amber));
        analysis.key_strategic_themes.forEach(t => {
            content.push(card([
                { text: sanitizeText(t.theme), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
                { text: sanitizeText(t.description), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 3] },
                { text: `Evidence: ${sanitizeText(t.evidence_from_document)}`, fontSize: 9, color: colors.amber.text, italics: true },
            ]));
        });
    }

    // Stakeholder Insights
    if (analysis.stakeholder_insights?.length > 0) {
        content.push(sectionBlock('Stakeholder Insights', colors.violet));
        const body: any[] = [
            [
                { text: 'Stakeholder', bold: true, fillColor: colors.violet.bg, color: colors.violet.text, margin: [4, 4, 4, 4] },
                { text: 'Role / Interest', bold: true, fillColor: colors.violet.bg, color: colors.violet.text, margin: [4, 4, 4, 4] },
                { text: 'Influence', bold: true, fillColor: colors.violet.bg, color: colors.violet.text, margin: [4, 4, 4, 4] },
            ],
        ];
        analysis.stakeholder_insights.forEach(s => {
            body.push([
                { text: sanitizeText(s.stakeholder), margin: [4, 4, 4, 4] },
                { text: sanitizeText(s.role_or_interest), margin: [4, 4, 4, 4] },
                { text: sanitizeText(s.influence_level), margin: [4, 4, 4, 4] },
            ]);
        });
        content.push({
            table: { widths: ['*', '*', 'auto'], body },
            layout: { hLineColor: () => '#DDD6FE', vLineColor: () => '#DDD6FE', hLineWidth: () => 0.75, vLineWidth: () => 0.75 },
            margin: [0, 6, 0, 0],
        });
    }

    // Resources & Capabilities
    if (analysis.resources_and_capabilities?.length > 0) {
        content.push(sectionBlock('Resources & Capabilities', colors.sky));
        analysis.resources_and_capabilities.forEach(r => {
            content.push(card([
                { text: sanitizeText(r.resource), fontSize: 11, bold: true, margin: [0, 0, 0, 3] },
                { text: sanitizeText(r.current_state), fontSize: 10, color: colors.slate600, margin: [0, 0, 0, 3] },
                { text: `Strategic Relevance: ${sanitizeText(r.strategic_relevance)}`, fontSize: 9, color: colors.sky.text, italics: true },
            ], '#BAE6FD'));
        });
    }

    // Identified Risks
    if (analysis.identified_risks?.length > 0) {
        content.push(sectionBlock('Identified Risks', colors.rose));
        const rBody: any[] = [
            [
                { text: 'Risk', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
                { text: 'Severity', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
                { text: 'Context', bold: true, fillColor: colors.rose.bg, color: colors.rose.text, margin: [4, 4, 4, 4] },
            ],
        ];
        analysis.identified_risks.forEach(r => {
            rBody.push([
                { text: sanitizeText(r.risk), margin: [4, 4, 4, 4] },
                { text: sanitizeText(r.severity), margin: [4, 4, 4, 4] },
                { text: sanitizeText(r.context), margin: [4, 4, 4, 4] },
            ]);
        });
        content.push({
            table: { widths: ['*', 'auto', '*'], body: rBody },
            layout: { hLineColor: () => '#FECDD3', vLineColor: () => '#FECDD3', hLineWidth: () => 0.75, vLineWidth: () => 0.75 },
            margin: [0, 6, 0, 0],
        });
    }

    // ── PART 2 ──
    content.push(partHeader('Part 2 — Analytical Assessment', colors.cyan));

    // Strategic Gaps
    if (analysis.strategic_gaps_and_observations?.length > 0) {
        content.push(sectionBlock('Strategic Gaps & Observations', colors.amber));
        content.push(pills(analysis.strategic_gaps_and_observations, colors.amber));
    }

    // Forward-Looking Assessment
    content.push(sectionBlock('Forward-Looking Assessment', colors.emerald));
    if (analysis.forward_looking_assessment.opportunities?.length > 0) {
        content.push({ text: 'Opportunities', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.forward_looking_assessment.opportunities, colors.emerald));
    }
    if (analysis.forward_looking_assessment.recommended_next_steps?.length > 0) {
        content.push({ text: 'Recommended Next Steps', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.forward_looking_assessment.recommended_next_steps, colors.sky));
    }
    if (analysis.forward_looking_assessment.potential_challenges?.length > 0) {
        content.push({ text: 'Potential Challenges', fontSize: 10, bold: true, margin: [0, 4, 0, 4] });
        content.push(pills(analysis.forward_looking_assessment.potential_challenges, colors.rose));
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
            title: `${title} - Strategic Analysis`,
            author: 'Knowledge Synthesis Platform',
            subject: 'Strategic Analysis',
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

export function downloadStrategicAnalysisPdf(analysis: StrategicAnalysisLLMOutput, filename?: string) {
    const doc = buildDocDefinition(analysis);
    const safe = (analysis?.analysis_title || 'strategic-analysis').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'strategic-analysis';
    const name = filename || `${safe} - Strategic Analysis.pdf`;
    pdfMake.createPdf(doc).download(name);
}
