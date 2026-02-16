/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';

// ── Theme ──────────────────────────────────────────────────────────────────────
const colors = {
    primary: '6d56f1',
    accent: '5341c8',
    slate800: '1F2937',
    slate600: '475569',
    white: 'FFFFFF',
    lightBg: 'F1F0FB',
    border: 'c4bcf0',
};

const SLIDE_MARGIN = 0.5; // inches

function sanitize(s: string | undefined | null): string {
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

// ── Minimal markdown → slide converter ─────────────────────────────────────────
interface Section {
    heading: string;
    bullets: string[];
}

function markdownToSections(md: string): { title: string; sections: Section[] } {
    const lines = (md || '').split(/\r?\n/);
    let title = 'Summary';
    const sections: Section[] = [];
    let current: Section | null = null;

    for (const raw of lines) {
        const line = raw.trimEnd();

        // top-level heading → presentation title
        const h1 = line.match(/^#\s+(.+)$/);
        if (h1) {
            title = sanitize(h1[1]);
            continue;
        }

        // section heading
        const h2 = line.match(/^#{2,3}\s+(.+)$/);
        const boldHeading = line.match(/^\*\*(.+?)\*\*:?$/);
        if (h2 || boldHeading) {
            if (current) sections.push(current);
            current = { heading: sanitize((h2 ? h2[1] : boldHeading![1])), bullets: [] };
            continue;
        }

        // bullet
        const bullet = line.match(/^[-*]\s+(.+)$/);
        if (bullet) {
            if (!current) current = { heading: '', bullets: [] };
            current.bullets.push(sanitize(bullet[1]));
            continue;
        }

        // numbered list
        const ol = line.match(/^\d+\.\s+(.+)$/);
        if (ol) {
            if (!current) current = { heading: '', bullets: [] };
            current.bullets.push(sanitize(ol[1]));
            continue;
        }

        // plain text paragraph (non-empty, non-code-fence)
        if (line.trim() && !line.startsWith('```')) {
            if (!current) current = { heading: '', bullets: [] };
            // strip inline markdown
            const clean = sanitize(line.replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1').replace(/`(.+?)`/g, '$1'));
            if (clean) current.bullets.push(clean);
        }
    }
    if (current) sections.push(current);
    return { title, sections };
}

// ── Slide helpers ──────────────────────────────────────────────────────────────
function addTitleSlide(pptx: PptxGenJS, title: string) {
    const slide = pptx.addSlide();
    slide.background = { color: colors.primary };
    slide.addText(title, {
        x: SLIDE_MARGIN,
        y: '35%',
        w: `${10 - SLIDE_MARGIN * 2}`,
        h: 1.2,
        fontSize: 32,
        bold: true,
        color: colors.white,
        align: 'center',
    } as any);
    slide.addText('Document Summary', {
        x: SLIDE_MARGIN,
        y: '55%',
        w: `${10 - SLIDE_MARGIN * 2}`,
        fontSize: 16,
        color: colors.border,
        align: 'center',
    } as any);
}

function addContentSlide(pptx: PptxGenJS, heading: string, bullets: string[]) {
    const slide = pptx.addSlide();

    // heading bar
    slide.addShape(pptx.ShapeType.rect, {
        x: 0,
        y: 0,
        w: 10,
        h: 0.9,
        fill: { color: colors.primary },
    });
    slide.addText(heading || 'Details', {
        x: SLIDE_MARGIN,
        y: 0.15,
        w: `${10 - SLIDE_MARGIN * 2}`,
        h: 0.6,
        fontSize: 22,
        bold: true,
        color: colors.white,
    });

    // content
    if (bullets.length > 0) {
        // Split into chunks of ~8 bullets per slide area
        const MAX_PER_SLIDE = 8;
        const chunk = bullets.slice(0, MAX_PER_SLIDE);
        const body = chunk.map((b) => ({
            text: b,
            options: { bullet: { type: 'bullet' as const }, fontSize: 14, color: colors.slate800, breakLine: true },
        }));
        slide.addText(body as any, {
            x: SLIDE_MARGIN,
            y: 1.2,
            w: `${10 - SLIDE_MARGIN * 2}`,
            h: 4.5,
            valign: 'top',
            lineSpacingMultiple: 1.3,
        } as any);

        // overflow → extra slides
        if (bullets.length > MAX_PER_SLIDE) {
            addContentSlide(pptx, `${heading} (cont.)`, bullets.slice(MAX_PER_SLIDE));
        }
    }
}

// ── Public API ─────────────────────────────────────────────────────────────────
export function downloadSummaryPptx(markdown: string, filename?: string, opts?: { title?: string }) {
    const { title: parsedTitle, sections } = markdownToSections(markdown);
    const title = opts?.title || parsedTitle;

    const pptx = new PptxGenJS();
    pptx.author = 'NotebookLM';
    pptx.subject = 'Summary';
    pptx.title = title;
    pptx.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5 → we use 10 x 7.5

    addTitleSlide(pptx, title);

    for (const section of sections) {
        addContentSlide(pptx, section.heading, section.bullets);
    }

    // If no sections were parsed, add a single slide with the raw text
    if (sections.length === 0) {
        const slide = pptx.addSlide();
        slide.addText(sanitize(markdown).slice(0, 2000), {
            x: SLIDE_MARGIN,
            y: SLIDE_MARGIN,
            w: `${10 - SLIDE_MARGIN * 2}`,
            h: 6,
            fontSize: 12,
            color: colors.slate800,
            valign: 'top',
        } as any);
    }

    const safe = (title || 'summary').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'summary';
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
