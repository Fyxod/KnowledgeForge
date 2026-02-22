/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';

/**
 * Slide layout constants.
 * 16:9 widescreen landscape — standard presentation format.
 */
export const PAGE_W = 13.333;
export const PAGE_H = 7.5;
export const ML = 0.6;    // left margin
export const MR = 0.6;    // right margin
export const MT = 0.4;    // top margin
export const MB = 0.4;    // bottom margin
export const CW = PAGE_W - ML - MR; // content width ≈ 12.133"
export const MAX_Y = PAGE_H - MB - 0.25; // leave room for footer ≈ 6.85"

export const FONT = {
    title: 28,
    subtitle: 14,
    sectionTitle: 18,
    phaseTitle: 14,
    subheading: 12,
    pillTitle: 12,
    swotTitle: 12,
    body: 11,
    code: 9,
    pill: 9,
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
    const charsPerInch = (72 / fontSize) * 1.45;
    const charsPerLine = Math.floor(width * charsPerInch);
    const lineCount = Math.max(1, Math.ceil(text.length / Math.max(charsPerLine, 1)));
    const lineHeight = (fontSize / 72) * 1.35;
    return lineCount * lineHeight + 0.04;
}

/** Estimate height needed for a bullet list */
export function estimateBulletsHeight(items: string[], fontSize: number, width: number): number {
    if (!items || items.length === 0) return 0;
    let total = 0;
    for (const item of items) {
        total += estimateTextHeight(item, fontSize, width - 0.3);
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
 * SlideWriter — slide-oriented builder for landscape presentations.
 *
 * Each major section gets its own slide. Content fills the slide body.
 * Auto-paginates to continuation slides only if content overflows.
 */
export class SlideWriter {
    private pptx: PptxGenJS;
    private slide: any;
    private y: number;
    private page: number;
    private footerColor: string;
    private _noFooterSlide: boolean;

    constructor(pptx: PptxGenJS, opts?: { footerColor?: string }) {
        this.pptx = pptx;
        this.page = 0;
        this.y = MAX_Y + 1; // force new slide on first use
        this.slide = null;
        this.footerColor = opts?.footerColor ?? '64748B';
        this._noFooterSlide = false;
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
        if (this.slide && !this._noFooterSlide) this.addFooter();
        this._noFooterSlide = false;
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

    // ── Slide-oriented content methods ──────────────────────────────────────

    /**
     * Add a full-page colored title slide with centered title + subtitle.
     * Forces next content to start on a new slide.
     */
    addBanner(title: string, subtitle: string, bgColor: string): void {
        this.newSlide();

        // Full-page background
        this.slide.addShape('rect' as any, {
            x: 0, y: 0, w: PAGE_W, h: PAGE_H,
            fill: { color: bgColor },
        } as any);

        // Title — vertically centered, slightly above middle
        const titleH = 0.7;
        const subH = subtitle ? 0.4 : 0;
        const totalH = titleH + subH;
        const topY = (PAGE_H - totalH) / 2 - 0.2;

        this.slide.addText(s(title), {
            x: ML, y: topY, w: CW, h: titleH,
            fontSize: FONT.title, bold: true, color: 'FFFFFF',
            align: 'center', valign: 'middle',
        } as any);

        if (subtitle) {
            this.slide.addText(s(subtitle), {
                x: ML + 1, y: topY + titleH + 0.05, w: CW - 2, h: subH,
                fontSize: FONT.subtitle, color: 'FFFFFFCC',
                align: 'center', valign: 'top',
            } as any);
        }

        // Title slide: skip footer, force next content to a new slide
        this._noFooterSlide = true;
        this.y = MAX_Y + 1;
    }

    /**
     * Add a section header that starts a new slide with a tinted background strip at top.
     * Pass `startSlide: false` to render inline (useful for summary markdown headings).
     */
    addSectionBlock(title: string, bgColor: string, textColor: string, opts?: { startSlide?: boolean }): void {
        if (opts?.startSlide !== false) {
            this.newSlide();
        } else {
            this.ensureSpace(0.65);
        }

        const h = 0.45;

        // Tinted background strip
        this.slide.addShape('rect' as any, {
            x: ML, y: this.y, w: CW, h,
            fill: { color: bgColor },
            rectRadius: 0.06,
        } as any);

        // Bold section title text
        this.slide.addText(s(title), {
            x: ML + 0.2, y: this.y, w: CW - 0.4, h,
            fontSize: FONT.sectionTitle, bold: true, color: textColor,
            valign: 'middle',
        } as any);

        this.y += h + 0.15;
    }

    /**
     * Add content wrapped in a card (bordered rectangle).
     * Full-width card — use for tables, phase cards, single items.
     */
    addCard(
        contentFn: (x: number, y: number, w: number) => number,
        opts?: { borderColor?: string; bgColor?: string; indent?: number },
    ): void {
        const indent = opts?.indent ?? 0;
        const cardX = ML + indent;
        const cardW = CW - indent;
        const padX = 0.12;
        const padY = 0.1;
        const innerW = cardW - padX * 2;

        // Estimate content height
        const startY = this.y + padY;
        const endY = contentFn(cardX + padX, startY, innerW);
        const contentH = endY - startY;
        const cardH = contentH + padY * 2;

        this.ensureSpace(cardH);

        const actualStartY = this.y;

        // Draw card background/border
        this.slide.addShape('rect' as any, {
            x: cardX, y: actualStartY, w: cardW, h: cardH,
            fill: opts?.bgColor ? { color: opts.bgColor } : undefined,
            line: { color: opts?.borderColor ?? 'E2E8F0', width: 0.75 },
            rectRadius: 0.06,
        } as any);

        // Re-run content at actual position
        contentFn(cardX + padX, actualStartY + padY, innerW);

        this.y = actualStartY + cardH + 0.08;
    }

    /**
     * Render two cards side by side (2-column layout for landscape slides).
     * Each card gets ~half of CW. Borders are drawn after content (no fill = transparent).
     */
    addCardPair(
        leftFn: (x: number, y: number, w: number) => number,
        rightFn: (x: number, y: number, w: number) => number,
        opts?: { borderColor?: string },
    ): void {
        const gap = 0.2;
        const colW = (CW - gap) / 2;
        const padX = 0.1;
        const padY = 0.08;
        const borderColor = opts?.borderColor ?? 'E2E8F0';

        this.ensureSpace(0.6);
        const startY = this.y;

        // Left card content
        const leftEndY = leftFn(ML + padX, startY + padY, colW - padX * 2);
        const leftH = Math.max(0.5, leftEndY - startY + padY);

        // Left card border
        this.slide.addShape('rect' as any, {
            x: ML, y: startY, w: colW, h: leftH,
            line: { color: borderColor, width: 0.75 },
            rectRadius: 0.06,
        } as any);

        // Right card content
        const rightX = ML + colW + gap;
        const rightEndY = rightFn(rightX + padX, startY + padY, colW - padX * 2);
        const rightH = Math.max(0.5, rightEndY - startY + padY);

        // Right card border
        this.slide.addShape('rect' as any, {
            x: rightX, y: startY, w: colW, h: rightH,
            line: { color: borderColor, width: 0.75 },
            rectRadius: 0.06,
        } as any);

        this.y = startY + Math.max(leftH, rightH) + 0.08;
    }

    /** Add pill badges (small colored rounded-rect tags) */
    addPills(items: string[], bgColor: string, textColor: string): void {
        if (!items || items.length === 0) return;
        const pillH = 0.24;
        const pillGap = 0.1;
        const pillPadX = 0.14;
        const fontSize = FONT.pill;

        const charsPerInch = (72 / fontSize) * 1.45;
        let cx = ML;
        let rowY = this.y;
        const rowHeight = pillH + 0.06;

        this.ensureSpace(rowHeight);

        for (const item of items) {
            const textW = Math.max(0.6, item.length / charsPerInch + pillPadX * 2);
            if (cx + textW > ML + CW) {
                cx = ML;
                rowY += rowHeight;
                if (rowY + pillH > MAX_Y) {
                    this.newSlide();
                    rowY = this.y;
                }
            }

            // Pill background
            this.slide.addShape('rect' as any, {
                x: cx, y: rowY, w: textW, h: pillH,
                fill: { color: bgColor },
                rectRadius: 0.1,
            } as any);

            // Pill text
            this.slide.addText(s(item), {
                x: cx, y: rowY, w: textW, h: pillH,
                fontSize, color: textColor, bold: true,
                align: 'center', valign: 'middle',
            } as any);

            cx += textW + pillGap;
        }

        this.y = rowY + pillH + 0.1;
    }

    /** Add a code block with gray background */
    addCodeBlock(text: string): void {
        const fs = FONT.code;
        const h = estimateTextHeight(text, fs, CW - 0.3);
        const blockH = h + 0.15;
        this.ensureSpace(blockH);

        this.slide.addShape('rect' as any, {
            x: ML, y: this.y, w: CW, h: blockH,
            fill: { color: 'F1F5F9' },
            rectRadius: 0.06,
        } as any);

        this.slide.addText(s(text), {
            x: ML + 0.15, y: this.y + 0.08, w: CW - 0.3, h,
            fontSize: fs, color: '1F2937',
            valign: 'top',
        } as any);

        this.y += blockH + 0.06;
    }

    // ── Standard content methods ────────────────────────────────────────────

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

    /** Add a section header (bold, centered) — legacy plain style */
    addSectionHeader(text: string, color: string = '0EA5E9'): void {
        const h = 0.3;
        this.ensureSpace(h + 0.3);
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
        this.ensureSpace(Math.min(h, 1.5));
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
            x: ML, y: PAGE_H - MB + 0.05, w: CW / 2, h: 0.25,
            fontSize: FONT.footer, color: this.footerColor,
        } as any);
        this.slide.addText(`${this.page}`, {
            x: ML + CW / 2, y: PAGE_H - MB + 0.05, w: CW / 2, h: 0.25,
            fontSize: FONT.footer, color: this.footerColor, align: 'right',
        } as any);
    }

    /** Call when done building slides to finalize the last footer */
    finalize(): void {
        if (this.slide && !this._noFooterSlide) this.addFooter();
    }
}
