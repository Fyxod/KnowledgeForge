/* eslint-disable @typescript-eslint/no-explicit-any */
type TDocumentDefinitions = any;
type Content = any;

import pdfMake from 'pdfmake/build/pdfmake';
import 'pdfmake/build/vfs_fonts';
import type { SensingReportData } from './api';

const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

// ── Color palette ──────────────────────────────────────────────────────────
const colors = {
    bannerBg: '#1e3a5f',
    primary: '#1e3a5f',
    accent: '#f59e0b',
    // Section tones
    executive: { bg: '#EFF6FF', text: '#1E40AF' },
    trends: { bg: '#FEF3C7', text: '#B45309' },
    radar: { bg: '#ECFDF5', text: '#047857' },
    market: { bg: '#EDE9FE', text: '#6D28D9' },
    sections: { bg: '#F0F9FF', text: '#0369A1' },
    recommendations: { bg: '#FFF7ED', text: '#C2410C' },
    articles: { bg: '#F1F5F9', text: '#475569' },
    // General
    slate600: '#475569',
    slate800: '#1F2937',
    slate500: '#64748B',
    border: '#E2E8F0',
    // Impact
    impactHigh: { bg: '#FEE2E2', text: '#991B1B' },
    impactMed: { bg: '#FEF3C7', text: '#92400E' },
    impactLow: { bg: '#D1FAE5', text: '#065F46' },
    // Ring
    adopt: '#059669',
    trial: '#2563EB',
    assess: '#D97706',
    hold: '#DC2626',
};

function sanitize(s: string | undefined | null): string {
    if (!s) return '';
    return String(s)
        .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/×/g, 'x')
        .replace(/±/g, '+/-').replace(/[–—]/g, '-').replace(/[""]/g, '"')
        .replace(/\u202F/g, ' ').replace(/'/g, "'").replace(/‑/g, '-');
}

// ── Helpers ────────────────────────────────────────────────────────────────

function banner(title: string, subtitle: string): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{
                stack: [
                    { text: sanitize(title), fontSize: 20, bold: true, color: '#FFFFFF', alignment: 'center', margin: [0, 0, 0, 4] },
                    ...(subtitle ? [{ text: sanitize(subtitle), fontSize: 10, color: '#E0E7FF', alignment: 'center' }] : []),
                ],
                fillColor: colors.bannerBg,
                margin: [12, 16, 12, 16],
            }]],
        },
        layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 0, paddingRight: () => 0, paddingTop: () => 0, paddingBottom: () => 0 },
        margin: [0, 0, 0, 12],
    };
}

function sectionHeader(title: string, tone: { bg: string; text: string }): Content {
    return {
        table: {
            widths: ['*'],
            body: [[{
                text: sanitize(title),
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

function pill(text: string, tone: { bg: string; text: string }): Content {
    return { text: sanitize(text), fontSize: 8, bold: true, color: tone.text, background: tone.bg, margin: [4, 2, 4, 2] };
}

function impactTone(level: string) {
    if (level === 'High') return colors.impactHigh;
    if (level === 'Medium') return colors.impactMed;
    return colors.impactLow;
}

function ringColor(ring: string): string {
    if (ring === 'Adopt') return colors.adopt;
    if (ring === 'Trial') return colors.trial;
    if (ring === 'Assess') return colors.assess;
    return colors.hold;
}

// ── Build Document ─────────────────────────────────────────────────────────

function buildSensingPdf(data: SensingReportData): TDocumentDefinitions {
    const { report, meta } = data;
    const today = new Date().toLocaleDateString();
    const content: Content[] = [];

    // Title banner
    content.push(banner(
        report.report_title || 'Tech Sensing Report',
        `${report.domain} | ${report.date_range} | ${report.total_articles_analyzed} articles analyzed`,
    ));

    // Meta pills
    content.push({
        columns: [
            pill(`Domain: ${report.domain}`, colors.executive),
            pill(`Period: ${report.date_range}`, colors.executive),
            pill(`Articles: ${report.total_articles_analyzed}`, colors.executive),
            pill(`Generated in ${meta.execution_time_seconds}s`, colors.executive),
        ],
        columnGap: 6,
        margin: [0, 0, 0, 10],
    });

    // Executive Summary
    content.push(sectionHeader('Executive Summary', colors.executive));
    content.push(card([
        { text: sanitize(report.executive_summary), fontSize: 10, color: colors.slate800, lineHeight: 1.4 },
    ], '#BFDBFE'));

    // Key Trends
    if (report.key_trends?.length > 0) {
        content.push(sectionHeader(`Key Trends (${report.key_trends.length})`, colors.trends));
        for (const trend of report.key_trends) {
            content.push(card([
                {
                    columns: [
                        { text: sanitize(trend.trend_name), fontSize: 11, bold: true, width: '*' },
                        pill(trend.impact_level, impactTone(trend.impact_level)),
                        pill(trend.time_horizon, colors.trends),
                    ],
                    columnGap: 6,
                    margin: [0, 0, 0, 4],
                },
                { text: sanitize(trend.description), fontSize: 9, color: colors.slate600, margin: [0, 0, 0, 4] },
                ...(trend.evidence?.length > 0 ? [{
                    ul: trend.evidence.map(e => ({ text: sanitize(e), fontSize: 8, color: colors.slate500 })),
                    margin: [0, 2, 0, 0] as any,
                }] : []),
            ]));
        }
    }

    // Market Signals
    if (report.market_signals?.length > 0) {
        content.push(sectionHeader(`Market Signals (${report.market_signals.length})`, colors.market));
        content.push({
            text: 'What prominent players are doing and where the industry is heading.',
            fontSize: 9, italics: true, color: colors.slate500, margin: [0, 0, 0, 8],
        });
        for (const signal of report.market_signals) {
            content.push(card([
                { text: sanitize(signal.company_or_player), fontSize: 11, bold: true, color: colors.market.text, margin: [0, 0, 0, 3] },
                { text: sanitize(signal.signal), fontSize: 9, color: colors.slate800, margin: [0, 0, 0, 3] },
                {
                    columns: [
                        { stack: [
                            { text: 'Strategic Intent', fontSize: 8, bold: true, color: colors.slate600 },
                            { text: sanitize(signal.strategic_intent), fontSize: 8, color: colors.slate600 },
                        ], width: '*' },
                        { stack: [
                            { text: 'Industry Impact', fontSize: 8, bold: true, color: colors.slate600 },
                            { text: sanitize(signal.industry_impact), fontSize: 8, color: colors.slate600 },
                        ], width: '*' },
                    ],
                    columnGap: 10,
                    margin: [0, 2, 0, 0],
                },
            ], '#DDD6FE'));
        }
    }

    // Technology Radar Details
    if (report.radar_item_details?.length > 0) {
        content.push(sectionHeader(`Technology Deep Dives (${report.radar_item_details.length})`, colors.radar));
        for (const item of report.radar_item_details) {
            // Find matching radar item for ring/quadrant
            const radarItem = report.radar_items?.find(r => r.name === item.technology_name);
            content.push(card([
                {
                    columns: [
                        { text: sanitize(item.technology_name), fontSize: 11, bold: true, width: '*' },
                        ...(radarItem ? [
                            pill(radarItem.ring, { bg: '#F0FDF4', text: ringColor(radarItem.ring) }),
                            pill(radarItem.quadrant, colors.radar),
                        ] : []),
                    ],
                    columnGap: 6,
                    margin: [0, 0, 0, 4],
                },
                { text: 'What It Is', fontSize: 9, bold: true, color: colors.slate800, margin: [0, 2, 0, 1] },
                { text: sanitize(item.what_it_is), fontSize: 9, color: colors.slate600, margin: [0, 0, 0, 4] },
                { text: 'Why It Matters', fontSize: 9, bold: true, color: colors.slate800, margin: [0, 2, 0, 1] },
                { text: sanitize(item.why_it_matters), fontSize: 9, color: colors.slate600, margin: [0, 0, 0, 4] },
                { text: 'Current State', fontSize: 9, bold: true, color: colors.slate800, margin: [0, 2, 0, 1] },
                { text: sanitize(item.current_state), fontSize: 9, color: colors.slate600, margin: [0, 0, 0, 4] },
                ...(item.key_players?.length > 0 ? [
                    { text: 'Key Players', fontSize: 9, bold: true, color: colors.slate800, margin: [0, 2, 0, 1] as any },
                    { text: item.key_players.map(sanitize).join(', '), fontSize: 9, color: colors.slate600, margin: [0, 0, 0, 4] as any },
                ] : []),
                ...(item.practical_applications?.length > 0 ? [
                    { text: 'Practical Applications', fontSize: 9, bold: true, color: colors.slate800, margin: [0, 2, 0, 1] as any },
                    { ul: item.practical_applications.map((a: string) => ({ text: sanitize(a), fontSize: 8, color: colors.slate600 })), margin: [0, 0, 0, 0] as any },
                ] : []),
            ], '#A7F3D0'));
        }
    }

    // Report Sections
    if (report.report_sections?.length > 0) {
        content.push(sectionHeader('Detailed Analysis', colors.sections));
        for (const section of report.report_sections) {
            content.push(card([
                { text: sanitize(section.section_title), fontSize: 11, bold: true, margin: [0, 0, 0, 4] },
                { text: sanitize(section.content), fontSize: 9, color: colors.slate600, lineHeight: 1.3 },
            ]));
        }
    }

    // Recommendations
    if (report.recommendations?.length > 0) {
        content.push(sectionHeader(`Recommendations (${report.recommendations.length})`, colors.recommendations));
        for (const rec of report.recommendations) {
            content.push(card([
                {
                    columns: [
                        pill(rec.priority, impactTone(rec.priority === 'Critical' ? 'High' : rec.priority)),
                        { text: sanitize(rec.title), fontSize: 10, bold: true, width: '*', margin: [0, 1, 0, 0] },
                    ],
                    columnGap: 6,
                    margin: [0, 0, 0, 3],
                },
                { text: sanitize(rec.description), fontSize: 9, color: colors.slate600, margin: [0, 0, 0, 3] },
                ...(rec.related_trends?.length > 0 ? [{
                    columns: rec.related_trends.slice(0, 4).map(t => pill(t, colors.trends)),
                    columnGap: 4,
                }] : []),
            ]));
        }
    }

    // Notable Articles
    if (report.notable_articles?.length > 0) {
        content.push(sectionHeader(`Notable Articles (${report.notable_articles.length})`, colors.articles));
        const tableBody: any[] = [
            [
                { text: 'Title', bold: true, fillColor: colors.articles.bg, color: colors.articles.text, margin: [4, 4, 4, 4] },
                { text: 'Source', bold: true, fillColor: colors.articles.bg, color: colors.articles.text, margin: [4, 4, 4, 4] },
                { text: 'Quadrant', bold: true, fillColor: colors.articles.bg, color: colors.articles.text, margin: [4, 4, 4, 4] },
                { text: 'Ring', bold: true, fillColor: colors.articles.bg, color: colors.articles.text, margin: [4, 4, 4, 4] },
            ],
        ];
        for (const article of report.notable_articles) {
            tableBody.push([
                { text: sanitize(article.title), margin: [4, 3, 4, 3], fontSize: 8 },
                { text: sanitize(article.source), margin: [4, 3, 4, 3], fontSize: 8 },
                { text: sanitize(article.quadrant), margin: [4, 3, 4, 3], fontSize: 8 },
                { text: sanitize(article.ring), margin: [4, 3, 4, 3], fontSize: 8, color: ringColor(article.ring) },
            ]);
        }
        content.push({
            table: { headerRows: 1, widths: ['*', 'auto', 'auto', 'auto'], body: tableBody },
            layout: {
                hLineColor: () => colors.border, vLineColor: () => colors.border,
                hLineWidth: () => 0.5, vLineWidth: () => 0.5,
            },
        });
    }

    return {
        info: {
            title: report.report_title || 'Tech Sensing Report',
            author: 'Knowledge Synthesis Platform',
            subject: `Tech Sensing - ${report.domain}`,
            keywords: 'tech sensing, technology radar, trends',
        },
        pageMargins: [36, 50, 36, 50],
        footer: (currentPage: number, pageCount: number) => ({
            columns: [
                { text: `Tech Sensing Report | ${report.domain} | ${today}`, color: colors.slate500, fontSize: 8 },
                { text: `${currentPage} / ${pageCount}`, alignment: 'right', color: colors.slate500, fontSize: 8 },
            ],
            margin: [36, 10, 36, 0],
        }),
        content,
        defaultStyle: { fontSize: 10, color: colors.slate800 },
    };
}

export function downloadSensingReportPdf(data: SensingReportData, filename?: string) {
    const doc = buildSensingPdf(data);
    const safe = (data.report.report_title || 'Tech Sensing Report')
        .replace(/[^a-z0-9\-\s]/gi, '').trim() || 'Tech Sensing Report';
    const name = filename || `${safe}.pdf`;
    pdfMake.createPdf(doc).download(name);
}
