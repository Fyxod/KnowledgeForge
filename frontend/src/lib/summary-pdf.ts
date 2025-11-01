// Loose types to avoid TS issues with pdfmake ambient types in Vite builds
type TDocumentDefinitions = any;
type Content = any;

// Import pdfmake (browser build) and its default font VFS shim
// @ts-ignore - build paths are valid at runtime
import pdfMake from 'pdfmake/build/pdfmake';
// @ts-ignore - side-effect import that registers window.pdfMake.vfs
import 'pdfmake/build/vfs_fonts';

// Initialize virtual file system for fonts (required by pdfmake in browser)
const g: any = (typeof window !== 'undefined' ? window : globalThis) as any;
if (g?.pdfMake?.vfs) {
    (pdfMake as any).vfs = g.pdfMake.vfs;
}

const colors = {
    slate600: '#475569',
    slate800: '#1F2937',
    slate500: '#64748B',
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
        .replace(/ /g, ' ')
        .replace(/’/g, "'")
        .replace(/‑/g, '-');
}

// Normalize some common inline markdown patterns into more parseable lines
function preprocessMarkdown(src: string): string {
    let s = src || '';
    // Turn patterns like ":- " or ".- " or ")- " into real new line bullets
    s = s.replace(/([:\.\)])\s*-\s+/g, '$1\n- ');
    // Collapse accidental double spaces before dashes
    s = s.replace(/\s{2,}-\s+/g, '\n- ');
    return s;
}

// Parse inline emphasis/code: **bold**, *italic*, `code`
function parseInlineChunks(text: string): any[] {
    const chunks: any[] = [];
    if (!text) return chunks;
    const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
    let lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
        const idx = m.index;
        if (idx > lastIndex) {
            const plain = text.slice(lastIndex, idx);
            if (plain) chunks.push({ text: sanitizeText(plain) });
        }
        const token = m[0];
        if (token.startsWith('**')) {
            chunks.push({ text: sanitizeText(token.slice(2, -2)), bold: true });
        } else if (token.startsWith('*')) {
            chunks.push({ text: sanitizeText(token.slice(1, -1)), italics: true });
        } else if (token.startsWith('`')) {
            chunks.push({ text: sanitizeText(token.slice(1, -1)), style: 'codeInline' });
        }
        lastIndex = re.lastIndex;
    }
    if (lastIndex < text.length) {
        const rest = text.slice(lastIndex);
        if (rest) chunks.push({ text: sanitizeText(rest) });
    }
    return chunks;
}

// Very small markdown-to-pdfmake converter, supporting headings, lists, inline emphasis
function markdownToPdfContent(markdown: string): Content[] {
    const lines = preprocessMarkdown(markdown).split(/\r?\n/);
    const content: Content[] = [];
    let inCode = false;
    let ul: string[] = [];
    let ol: string[] = [];

    const flushLists = () => {
        if (ul.length) {
            content.push({ ul: ul.map((t) => ({ text: parseInlineChunks(t), margin: [0, 2, 0, 2] })) });
            ul = [];
        }
        if (ol.length) {
            content.push({ ol: ol.map((t) => ({ text: parseInlineChunks(t), margin: [0, 2, 0, 2] })) });
            ol = [];
        }
    };

    for (let raw of lines) {
        const line = raw.trimEnd();

        // Fenced code blocks
        if (/^```/.test(line)) {
            inCode = !inCode;
            continue;
        }

        if (inCode) {
            flushLists();
            content.push({ text: sanitizeText(raw), style: 'code' });
            continue;
        }

        if (!line.trim()) {
            // blank line -> break paragraph / lists
            flushLists();
            content.push({ text: ' ', margin: [0, 4, 0, 0] });
            continue;
        }

        // Headings
        const h1 = line.match(/^#\s+(.+)$/);
        if (h1) {
            flushLists();
            content.push({ text: sanitizeText(h1[1]), style: 'title', margin: [0, 8, 0, 4] });
            continue;
        }
        const h2 = line.match(/^##\s+(.+)$/);
        if (h2) {
            flushLists();
            content.push({ text: sanitizeText(h2[1]), style: 'sectionTitle', margin: [0, 10, 0, 4] });
            continue;
        }
        const h3 = line.match(/^###\s+(.+)$/);
        if (h3) {
            flushLists();
            content.push({ text: sanitizeText(h3[1]), style: 'subheading', margin: [0, 8, 0, 2] });
            continue;
        }

        // Bold-only line used as pseudo-heading e.g. **Experience**:
        const boldOnly = line.match(/^\*\*(.+?)\*\*:?$/);
        if (boldOnly) {
            flushLists();
            content.push({ text: sanitizeText(boldOnly[1]), style: 'sectionTitle', margin: [0, 10, 0, 4] });
            continue;
        }

        // Unordered list
        const ulMatch = line.match(/^[-*]\s+(.+)$/);
        if (ulMatch) {
            if (ol.length) {
                flushLists();
            }
            ul.push(ulMatch[1]);
            continue;
        }

        // Ordered list
        const olMatch = line.match(/^\d+\.\s+(.+)$/);
        if (olMatch) {
            if (ul.length) {
                flushLists();
            }
            ol.push(olMatch[1]);
            continue;
        }

        // Paragraph text
        flushLists();
        content.push({ text: parseInlineChunks(line) });
    }

    flushLists();
    return content;
}

function buildDocDefinition(markdown: string, explicitTitle?: string): TDocumentDefinitions {
    const firstHeading = /^(?:#\s+|##\s+|###\s+)(.+)$/m.exec(markdown || '');
    const title = sanitizeText(explicitTitle || (firstHeading ? firstHeading[1] : 'Document Summary'));
    const today = new Date();
    const date = today.toLocaleDateString();

    return {
        info: {
            title: `${title} - Summary`,
            author: 'NotebookLM',
            subject: 'Summary',
            keywords: 'summary, document',
        },
        pageMargins: [40, 60, 40, 60],
        footer: (currentPage: number, pageCount: number) => ({
            columns: [
                { text: date, color: colors.slate500 },
                { text: `${currentPage} / ${pageCount}`, alignment: 'right', color: colors.slate500 },
            ],
            margin: [40, 10, 40, 0],
        }),
        content: [
            { text: title, style: 'title', alignment: 'center', margin: [0, 0, 0, 8] },
            ...markdownToPdfContent(markdown || ''),
        ],
        styles: {
            title: { fontSize: 20, bold: true, color: colors.slate800, margin: [0, 0, 0, 4] },
            sectionTitle: { fontSize: 13, bold: true },
            subheading: { fontSize: 11, bold: true, margin: [0, 6, 0, 2] },
            code: { fontSize: 9, color: colors.slate800 },
            codeInline: { fontSize: 9, color: colors.slate800 },
        },
        defaultStyle: {
            fontSize: 10,
            color: colors.slate800,
        },
    };
}

export function downloadSummaryPdf(markdown: string, filename?: string, opts?: { title?: string }) {
    const doc = buildDocDefinition(markdown, opts?.title);
    const safeTitle = (opts?.title || 'summary').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'summary';
    const name = filename || `${safeTitle}.pdf`;
    pdfMake.createPdf(doc).download(name);
}
