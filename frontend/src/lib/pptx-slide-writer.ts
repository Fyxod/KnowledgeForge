/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';

/**
 * PDF-matching page constants.
 * Letter 8.5" × 11" portrait with [40,60,40,60] pt margins.
 */
export const PAGE_W = 8.5;
export const PAGE_H = 11;
export const ML = 0.56;   // left margin  (40pt)
export const MT = 0.83;   // top margin   (60pt)
export const MB = 0.83;   // bottom margin(60pt)
export const CW = PAGE_W - ML - ML; // content width ≈ 7.38"
export const MAX_Y = PAGE_H - MB - 0.3; // leave room for footer

export const FONT = {
    title: 20,
    subtitle: 10,
    sectionTitle: 13,
    phaseTitle: 11,
    subheading: 11,
    pillTitle: 11,
    swotTitle: 11,
    body: 10,
    code: 9,
    footer: 8,
};

/** Sanitize text for pptxgenjs — strip non-latin1 glyphs */
export function s(text: string | undefined | null): string {
    if (!text) return '';
    return String(text)
        .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/×/g, 'x')
        .replace(/±/g, '+/-').replace(/[–—]/g, '-').replace(/[""]/g, '"')
        .replace(/\u202F/g, ' ').replace(/'/g, "'").replace(/‑/g, '-');
}

/** Estimate how tall a block of text will be given its font size and width */
export function estimateTextHeight(text: string, fontSize: number, width: number): number {
    if (!text) return 0.2;
    // Approximate chars-per-inch at given font size (rough heuristic)
    const charsPerInch = (72 / fontSize) * 1.45;
    const charsPerLine = Math.floor(width * charsPerInch);
    const lineCount = Math.max(1, Math.ceil(text.length / Math.max(charsPerLine, 1)));
    const lineHeight = (fontSize / 72) * 1.35; // pt→in with leading
    return lineCount * lineHeight + 0.04; // small padding
}

/** Estimate height needed for a bullet list */
export function estimateBulletsHeight(items: string[], fontSize: number, width: number): number {
    if (!items || items.length === 0) return 0;
    let total = 0;
    for (const item of items) {
        total += estimateTextHeight(item, fontSize, width - 0.3); // indent
    }
    return total + 0.04;
}

/** Estimate height for a table */
export function estimateTableHeight(rowCount: number, fontSize: number): number {
    const rowH = (fontSize / 72) * 1.6 + 0.08;
    return rowCount * rowH + 0.1;
}

/** Build pptxgenjs bullet options array */
export function makeBullets(items: string[], opts?: { fontSize?: number; color?: string }): any[] {
    return items.map((t) => ({
        text: s(t),
        options: {
            bullet: { type: 'bullet' as const },
            fontSize: opts?.fontSize ?? FONT.body,
            color: opts?.color ?? '1F2937',
            breakLine: true,
            paraSpaceAfter: 3,
        },
    }));
}

/**
 * SlideWriter — dynamic cursor-based slide builder.
 *
 * Tracks the current Y position on the current slide.
 * Automatically creates a new slide when content would overflow.
 * Adds a footer to every completed slide.
 */
export class SlideWriter {
    private pptx: PptxGenJS;
    private slide: any;
    private y: number;
    private page: number;
    private footerColor: string;

    constructor(pptx: PptxGenJS, opts?: { footerColor?: string }) {
        this.pptx = pptx;
        this.page = 0;
        this.y = MAX_Y + 1; // force new slide on first use
        this.slide = null;
        this.footerColor = opts?.footerColor ?? '64748B';
    }

    /** Current Y cursor position */
    get cursor(): number { return this.y; }

    /** Remaining vertical space on current slide */
    get remaining(): number { return Math.max(0, MAX_Y - this.y); }

    /** Current page number */
    get pageNum(): number { return this.page; }

    /** Current slide reference */
    get currentSlide(): any { return this.slide; }

    /** Ensure there is at least `needed` inches of vertical space; if not, start a new slide. */
    ensureSpace(needed: number): void {
        if (this.slide && this.y + needed <= MAX_Y) return;
        this.newSlide();
    }

    /** Force a new slide, finishing the current one with a footer. */
    newSlide(): any {
        if (this.slide) this.addFooter();
        this.slide = this.pptx.addSlide();
        this.page++;
        this.y = MT;
        return this.slide;
    }

    /** Advance the cursor by `amount` inches. */
    advance(amount: number): void {
        this.y += amount;
    }

    /** Add vertical spacing */
    gap(inches: number = 0.15): void {
        this.y += inches;
    }

    // ── High-level content methods ──────────────────────────────────────────

    /** Add a centered title (large heading) */
    addTitle(text: string, opts?: { color?: string; align?: string }): void {
        const h = estimateTextHeight(text, FONT.title, CW);
        this.ensureSpace(h);
        this.slide.addText(s(text), {
            x: ML, y: this.y, w: CW, h,
            fontSize: FONT.title, bold: true,
            color: opts?.color ?? '1F2937',
            align: opts?.align ?? 'center',
            valign: 'top',
        } as any);
        this.y += h + 0.06;
    }

    /** Add subtitle text */
    addSubtitle(text: string, opts?: { color?: string }): void {
        const h = estimateTextHeight(text, FONT.subtitle, CW);
        this.ensureSpace(h);
        this.slide.addText(s(text), {
            x: ML, y: this.y, w: CW, h,
            fontSize: FONT.subtitle,
            color: opts?.color ?? '475569',
            align: 'center',
            valign: 'top',
        } as any);
        this.y += h + 0.04;
    }

    /** Add a section header (bold, centered) */
    addSectionHeader(text: string, color: string = '0EA5E9'): void {
        const h = 0.3;
        this.ensureSpace(h + 0.3); // header + at least some content after it
        this.slide.addText(s(text), {
            x: ML, y: this.y, w: CW, h,
            fontSize: FONT.sectionTitle, bold: true, color,
            align: 'center',
        } as any);
        this.y += h + 0.08;
    }

    /** Add a subheading (bold, left-aligned) */
    addSubheading(text: string, opts?: { color?: string; indent?: number }): void {
        const indent = opts?.indent ?? 0;
        const h = estimateTextHeight(text, FONT.subheading, CW - indent);
        this.ensureSpace(h);
        this.slide.addText(s(text), {
            x: ML + indent, y: this.y, w: CW - indent, h,
            fontSize: FONT.subheading, bold: true,
            color: opts?.color ?? '1F2937',
            valign: 'top',
        } as any);
        this.y += h + 0.04;
    }

    /** Add body text paragraph */
    addText(text: string, opts?: { fontSize?: number; color?: string; indent?: number; bold?: boolean }): void {
        const fs = opts?.fontSize ?? FONT.body;
        const indent = opts?.indent ?? 0;
        const h = estimateTextHeight(text, fs, CW - indent);
        this.ensureSpace(h);
        this.slide.addText(s(text), {
            x: ML + indent, y: this.y, w: CW - indent, h,
            fontSize: fs,
            color: opts?.color ?? '1F2937',
            bold: opts?.bold ?? false,
            valign: 'top',
        } as any);
        this.y += h + 0.04;
    }

    /** Add a bullet list */
    addBullets(items: string[], opts?: { fontSize?: number; color?: string; indent?: number }): void {
        if (!items || items.length === 0) return;
        const fs = opts?.fontSize ?? FONT.body;
        const indent = opts?.indent ?? 0;
        const h = estimateBulletsHeight(items, fs, CW - indent);
        this.ensureSpace(Math.min(h, 1.5)); // at least first chunk must fit
        this.slide.addText(makeBullets(items, { fontSize: fs, color: opts?.color }) as any, {
            x: ML + indent, y: this.y, w: CW - indent, h,
            valign: 'top', lineSpacingMultiple: 1.15,
        } as any);
        this.y += h + 0.06;
    }

    /** Add a table */
    addTable(rows: any[][], opts?: {
        fontSize?: number;
        colWidths?: number[];
        borderColor?: string;
    }): void {
        const fs = opts?.fontSize ?? FONT.body;
        const h = estimateTableHeight(rows.length, fs);
        this.ensureSpace(Math.min(h, 2.5));
        this.slide.addTable(rows, {
            x: ML, y: this.y, w: CW,
            fontSize: fs,
            border: { pt: 0.5, color: opts?.borderColor ?? 'c4bcf0' },
            colW: opts?.colWidths ?? undefined,
            autoPage: true,
            autoPageRepeatHeader: true,
        } as any);
        this.y += h + 0.1;
    }

    /** Add two-column content using callbacks */
    addTwoColumns(
        leftFn: (x: number, y: number, w: number) => number,
        rightFn: (x: number, y: number, w: number) => number,
        opts?: { gap?: number },
    ): void {
        const gap = opts?.gap ?? 0.22;
        const colW = (CW - gap) / 2;
        const startY = this.y;
        const leftEnd = leftFn(ML, startY, colW);
        const rightEnd = rightFn(ML + colW + gap, startY, colW);
        this.y = Math.max(leftEnd, rightEnd) + 0.06;
    }

    /** Add a horizontal line */
    addLine(opts?: { indent?: number; color?: string }): void {
        const indent = opts?.indent ?? 0;
        this.slide.addShape('line' as any, {
            x: ML + indent, y: this.y, w: CW - indent * 2, h: 0,
            line: { color: opts?.color ?? 'c4bcf0', width: 0.5 },
        } as any);
        this.y += 0.06;
    }

    /** Add raw pptxgenjs text object at current cursor (low-level) */
    addRawText(textObj: any, opts: any): void {
        const h = opts.h ?? 0.3;
        this.ensureSpace(h);
        this.slide.addText(textObj, { ...opts, x: opts.x ?? ML, y: this.y, w: opts.w ?? CW });
        this.y += h + 0.04;
    }

    // ── Footer ─────────────────────────────────────────────────────────────

    private addFooter(): void {
        const date = new Date().toLocaleDateString();
        this.slide.addText(date, {
            x: ML, y: PAGE_H - MB + 0.1, w: CW / 2, h: 0.25,
            fontSize: FONT.footer, color: this.footerColor,
        } as any);
        this.slide.addText(`${this.page}`, {
            x: ML + CW / 2, y: PAGE_H - MB + 0.1, w: CW / 2, h: 0.25,
            fontSize: FONT.footer, color: this.footerColor, align: 'right',
        } as any);
    }

    /** Call when done building slides to finalize the last footer */
    finalize(): void {
        if (this.slide) this.addFooter();
    }
}
