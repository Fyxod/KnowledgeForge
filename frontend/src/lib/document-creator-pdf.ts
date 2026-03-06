// Client-side PDF generation for Document Creator using pdfmake
// Modeled after summary-pdf.ts — avoids server-side fpdf2 issues

type TDocumentDefinitions = any;
type Content = any;

// @ts-ignore - build paths are valid at runtime
import pdfMake from 'pdfmake/build/pdfmake';
// @ts-ignore - side-effect import that registers window.pdfMake.vfs
import 'pdfmake/build/vfs_fonts';

import type { SectionState } from '@/lib/api';

// Initialize virtual file system for fonts (required by pdfmake in browser)
const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

// ── Color palette ────────────────────────────────────────────────────────────
const colors = {
    bannerBg: '#1E293B',       // slate-800
    bannerText: '#FFFFFF',
    subtitleColor: '#94A3B8',  // slate-400
    headingColor: '#1E293B',   // slate-800
    bodyColor: '#334155',      // slate-700
    mutedColor: '#64748B',     // slate-500
    takeawayBg: '#FFF7ED',    // orange-50
    takeawayText: '#C2410C',  // orange-700
    sectionBg: '#EDE9FE',     // violet-100
    sectionText: '#6D28D9',   // violet-700
    tableBorder: '#CBD5E1',   // slate-300
    tableHeaderBg: '#F1F5F9', // slate-100
};

function sanitizeText(s: string | undefined | null): string {
    if (!s) return '';
    return String(s)
        .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/×/g, 'x')
        .replace(/±/g, '+/-').replace(/[–—]/g, '-').replace(/[""]/g, '"')
        .replace(/\u202F/g, ' ').replace(/'/g, "'").replace(/‑/g, '-');
}

// ── PDF building blocks ─────────────────────────────────────────────────────

function titleBanner(title: string): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{
                text: sanitizeText(title),
                fontSize: 24, bold: true, color: colors.bannerText,
                fillColor: colors.bannerBg,
                alignment: 'center',
                margin: [16, 20, 16, 20],
            }]],
        },
        layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
        margin: [0, 0, 0, 6],
    };
}

function subtitleBlock(subtitle: string): Content {
    return {
        text: sanitizeText(subtitle),
        fontSize: 14,
        color: colors.mutedColor,
        alignment: 'center',
        margin: [0, 0, 0, 6],
    };
}

function metadataBlock(meta: string): Content {
    return {
        text: sanitizeText(meta),
        fontSize: 9,
        color: colors.subtitleColor,
        alignment: 'center',
        margin: [0, 0, 0, 20],
    };
}

function sectionHeading(title: string, level: number): Content {
    if (level <= 1) {
        return {
            table: {
                widths: ['*'],
                body: [[{
                    text: sanitizeText(title),
                    fontSize: 14, bold: true, color: colors.sectionText,
                    fillColor: colors.sectionBg,
                    margin: [10, 7, 10, 7],
                }]],
            },
            layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
            margin: [0, 16, 0, 8],
        };
    }
    return {
        text: sanitizeText(title),
        fontSize: level === 2 ? 12 : 11,
        bold: true,
        color: colors.headingColor,
        margin: [0, 12, 0, 6],
    };
}

function keyTakeawayBlock(takeaway: string): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{
                text: [
                    { text: 'Key Takeaway: ', bold: true, italics: true },
                    { text: sanitizeText(takeaway), italics: true },
                ],
                fontSize: 9,
                color: colors.takeawayText,
                fillColor: colors.takeawayBg,
                margin: [8, 5, 8, 5],
            }]],
        },
        layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
        margin: [0, 0, 0, 8],
    };
}

function contentParagraphs(content: string): Content[] {
    const items: Content[] = [];
    for (const para of content.split('\n')) {
        const text = para.trim();
        if (text) {
            items.push({ text: sanitizeText(text), margin: [0, 0, 0, 4] });
        }
    }
    return items;
}

function bulletList(bullets: string[]): Content {
    return {
        ul: bullets.map((b) => ({
            text: sanitizeText(b),
            margin: [0, 2, 0, 2],
        })),
        margin: [0, 4, 0, 8],
    };
}

function dataTable(tableData: { headers: string[]; rows: string[][] }): Content {
    const { headers, rows } = tableData;
    if (!headers || headers.length === 0) return { text: '' };

    const headerRow = headers.map((h) => ({
        text: sanitizeText(h),
        bold: true,
        fontSize: 9,
        fillColor: colors.tableHeaderBg,
        color: colors.headingColor,
        margin: [4, 4, 4, 4],
    }));

    const dataRows = (rows || []).map((row) =>
        headers.map((_, colIdx) => ({
            text: sanitizeText(row[colIdx] ?? ''),
            fontSize: 9,
            color: colors.bodyColor,
            margin: [4, 3, 4, 3],
        })),
    );

    return {
        table: {
            headerRows: 1,
            widths: headers.map(() => '*'),
            body: [headerRow, ...dataRows],
        },
        layout: {
            hLineColor: () => colors.tableBorder,
            vLineColor: () => colors.tableBorder,
            hLineWidth: () => 0.5,
            vLineWidth: () => 0.5,
        },
        margin: [0, 4, 0, 8],
    };
}

// ── Main builder ────────────────────────────────────────────────────────────

function buildDocCreatorDefinition(
    title: string,
    subtitle: string | undefined,
    sections: SectionState[],
    config?: { document_type?: string; audience?: string },
): TDocumentDefinitions {
    const today = new Date();
    const date = today.toLocaleDateString();

    const content: Content[] = [];

    // Title banner
    content.push(titleBanner(title));

    // Subtitle
    if (subtitle) {
        content.push(subtitleBlock(subtitle));
    }

    // Metadata line
    if (config?.document_type || config?.audience) {
        const parts: string[] = [];
        if (config.document_type) parts.push(`Type: ${config.document_type.replace(/_/g, ' ')}`);
        if (config.audience) parts.push(`Audience: ${config.audience}`);
        content.push(metadataBlock(parts.join(' | ')));
    }

    // Page break after title page
    content.push({ text: '', pageBreak: 'after' });

    // Sections
    for (const section of sections) {
        if (!section.versions || section.versions.length === 0) continue;
        const version = section.versions[section.selected_version_index] || section.versions[0];

        // Section heading
        const level = Math.min(section.spec.heading_level || 1, 3);
        content.push(sectionHeading(section.spec.title, level));

        // Key takeaway
        if (version.key_takeaway) {
            content.push(keyTakeawayBlock(version.key_takeaway));
        }

        // Main content
        if (version.content) {
            content.push(...contentParagraphs(version.content));
        }

        // Bullet points
        if (version.bullet_points && version.bullet_points.length > 0) {
            content.push(bulletList(version.bullet_points));
        }

        // Table
        if (version.table_data && version.table_data.headers) {
            content.push(dataTable(version.table_data));
        }

        // Spacing
        content.push({ text: ' ', margin: [0, 4, 0, 0] });
    }

    return {
        info: {
            title: sanitizeText(title),
            author: 'Knowledge Synthesis Platform',
            subject: 'Document Creator Export',
        },
        pageMargins: [40, 60, 40, 60],
        footer: (currentPage: number, pageCount: number) => ({
            columns: [
                { text: date, color: colors.mutedColor },
                { text: `${currentPage} / ${pageCount}`, alignment: 'right', color: colors.mutedColor },
            ],
            margin: [40, 10, 40, 0],
        }),
        content,
        defaultStyle: {
            fontSize: 10,
            color: colors.bodyColor,
        },
    };
}

export function downloadDocumentCreatorPdf(
    title: string,
    subtitle: string | undefined,
    sections: SectionState[],
    config?: { document_type?: string; audience?: string },
) {
    const doc = buildDocCreatorDefinition(title, subtitle, sections, config);
    const safeName = (title || 'document').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'document';
    pdfMake.createPdf(doc).download(`${safeName}.pdf`);
}
