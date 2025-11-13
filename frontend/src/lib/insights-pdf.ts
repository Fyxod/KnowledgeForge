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

const colors = {
    primary: '#6d56f1',
    slate600: '#475569',
    slate800: '#1F2937',
    slate500: '#64748B',
    accent1: '#F59E0B',
    accent2: '#5341c8',
    success: '#10B981',
    danger: '#EF4444',
    border: '#c4bcf0',
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

function bulletList(items: string[] = []): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        ul: items.map((i) => ({ text: sanitizeText(i), margin: [0, 2, 0, 2] })),
        margin: [0, 4, 0, 0],
    } as Content;
}

function sectionHeader(title: string, color: string = colors.primary): Content {
    return {
        text: sanitizeText(title),
        style: 'sectionTitle',
        color,
        margin: [0, 12, 0, 6],
    } as Content;
}

function keyDiscussionPoints(points: InsightsLLMOutput['key_discussion_points']): Content {
    if (!points || points.length === 0) return { text: '' };
    return {
        stack: points.map((p) => ({
            stack: [
                { text: sanitizeText(p.topic), style: 'subheading' },
                { text: sanitizeText(p.details), margin: [0, 2, 0, 6] },
            ],
            margin: [0, 2, 0, 2],
        })),
    };
}

function strengthsContent(items: InsightsLLMOutput['strengths']): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        stack: items.map((s) => ({
            stack: [
                { text: sanitizeText(s.aspect), style: 'subheading' },
                { text: sanitizeText(s.evidence_or_example), margin: [0, 2, 0, 6] },
            ],
            margin: [0, 2, 0, 2],
        })),
    };
}

function gapsContent(items: InsightsLLMOutput['improvement_or_missing_areas']): Content {
    if (!items || items.length === 0) return { text: '' };
    const body: any[] = [
        [{ text: 'Gap', bold: true }, { text: 'Suggested Improvement', bold: true }],
    ];
    items.forEach((g) => {
        body.push([
            { text: sanitizeText(g.gap), margin: [0, 3, 0, 3] },
            { text: sanitizeText(g.suggested_improvement), margin: [0, 3, 0, 3] },
        ]);
    });
    return {
        table: {
            widths: ['*', '*'],
            body,
        },
        layout: {
            fillColor: (rowIndex: number) => (rowIndex === 0 ? '#e3defc' : undefined),
            hLineColor: () => colors.border,
            vLineColor: () => colors.border,
        },
        margin: [0, 6, 0, 0],
    };
}

function innovationsContent(items: InsightsLLMOutput['innovation_aspects']): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        stack: items.map((i) => ({
            stack: [
                { text: sanitizeText(i.innovation_title), style: 'subheading' },
                { text: sanitizeText(i.description), margin: [0, 2, 0, 2] },
                { text: `Potential Impact: ${sanitizeText(i.potential_impact)}`, color: colors.slate600 },
            ],
            margin: [0, 2, 0, 6],
        })),
    };
}

function futureContent(items: InsightsLLMOutput['future_considerations']): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        stack: items.map((f) => ({
            stack: [
                { text: sanitizeText(f.focus_area), style: 'subheading' },
                { text: sanitizeText(f.recommendation), margin: [0, 2, 0, 6] },
            ],
            margin: [0, 2, 0, 2],
        })),
    };
}

function pseudocodeContent(items: InsightsLLMOutput['pseudocode_or_technical_outline']): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        stack: items.map((p) => ({
            stack: [
                ...(p.section ? [{ text: sanitizeText(p.section), style: 'subheading' }] : []),
                ...(p.pseudocode ? [{ text: sanitizeText(p.pseudocode), style: 'code' }] : []),
            ],
            margin: [0, 2, 0, 6],
        })),
    };
}

function additionsContent(items: InsightsLLMOutput['llm_inferred_additions']): Content {
    if (!items || items.length === 0) return { text: '' };
    return {
        stack: items.map((a) => ({
            stack: [
                { text: sanitizeText(a.section_title), style: 'subheading' },
                { text: sanitizeText(a.content), margin: [0, 2, 0, 6] },
            ],
            margin: [0, 2, 0, 2],
        })),
    };
}

function buildDocDefinition(insights: InsightsLLMOutput): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();
    const title = insights?.document_summary?.title || 'Insights';
    const purpose = insights?.document_summary?.purpose || '';

    const content: Content[] = [];

    // Title & summary
    content.push(
        { text: sanitizeText(title), style: 'title', alignment: 'center' },
        { text: sanitizeText(purpose), style: 'subtitle', alignment: 'center', margin: [0, 0, 0, 6] },
        bulletList(insights.document_summary?.key_themes || []),
    );

    // Conditional sections (only add header when there's content)
    if (insights.key_discussion_points && insights.key_discussion_points.length > 0) {
        content.push(sectionHeader('Key Discussion Points', colors.primary));
        content.push(keyDiscussionPoints(insights.key_discussion_points));
    }

    if (insights.strengths && insights.strengths.length > 0) {
        content.push(sectionHeader('Strengths', colors.success));
        content.push(strengthsContent(insights.strengths));
    }

    if (insights.improvement_or_missing_areas && insights.improvement_or_missing_areas.length > 0) {
        content.push(sectionHeader('Gaps & Improvements', colors.danger));
        content.push(gapsContent(insights.improvement_or_missing_areas));
    }

    if (insights.innovation_aspects && insights.innovation_aspects.length > 0) {
        content.push(sectionHeader('Innovation Aspects', colors.accent1));
        content.push(innovationsContent(insights.innovation_aspects));
    }

    if (insights.future_considerations && insights.future_considerations.length > 0) {
        content.push(sectionHeader('Future Considerations', colors.accent2));
        content.push(futureContent(insights.future_considerations));
    }

    if (insights.pseudocode_or_technical_outline && insights.pseudocode_or_technical_outline.length > 0) {
        content.push(sectionHeader('Pseudocode / Technical Outline', colors.primary));
        content.push(pseudocodeContent(insights.pseudocode_or_technical_outline));
    }

    if (insights.llm_inferred_additions && insights.llm_inferred_additions.length > 0) {
        content.push(sectionHeader('Additional Insights', colors.slate600));
        content.push(additionsContent(insights.llm_inferred_additions));
    }

    return {
        info: {
            title: `${title} - Insights`,
            author: 'NotebookLM',
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
        styles: {
            title: { fontSize: 20, bold: true, color: colors.slate800, margin: [0, 0, 0, 4] },
            subtitle: { fontSize: 10, color: colors.slate600 },
            sectionTitle: { fontSize: 13, bold: true },
            subheading: { fontSize: 11, bold: true, margin: [0, 6, 0, 2] },
            code: { fontSize: 9, color: colors.slate800 },
        },
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
