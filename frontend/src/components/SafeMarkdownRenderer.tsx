import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";

type Props = {
  content: string;
  enableMarkdown?: boolean;
};

export default function SafeMarkdownRenderer({ content, enableMarkdown = true }: Props) {
  if (!enableMarkdown || !content) {
    return <div className="whitespace-pre-wrap leading-relaxed">{content}</div>;
  }

  return (
  <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed dark:text-zinc-100 text-zinc-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight as any]}
        components={{
          h1: ({ node, ...props }) => (
            <h1 className="text-xl font-bold mb-2" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-lg font-bold mb-2" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-base font-bold mb-1" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-sm font-bold mb-1" {...props} />
          ),
          h5: ({ node, ...props }) => (
            <h5 className="text-sm font-semibold mb-1" {...props} />
          ),
          h6: ({ node, ...props }) => (
            <h6 className="text-xs font-semibold mb-1" {...props} />
          ),
          p: ({ node, ...props }) => <p className="mb-2" {...props} />,
          ul: ({ node, ...props }) => (
            <ul className="list-disc pl-5 mb-2 space-y-1" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal pl-5 mb-2 space-y-1" {...props} />
          ),
          li: ({ node, ...props }) => <li className="mb-1" {...props} />,
          blockquote: ({ node, ...props }) => (
            <blockquote
              className="border-l-4 border-gray-300 dark:border-gray-700 pl-4 italic text-gray-600 dark:text-gray-300 my-2"
              {...props}
            />
          ),
          code: ({ node, inline, className, children, ...props }) => {
            return !inline ? (
              <pre className="bg-zinc-100 dark:bg-zinc-900 text-zinc-800 dark:text-zinc-100 p-3 rounded-lg overflow-x-auto my-3 text-sm border border-zinc-300 dark:border-zinc-700 shadow-sm">
                <code className={className} {...props}>
                  {children}
                </code>
              </pre>
            ) : (
              <code className="bg-zinc-200 dark:bg-zinc-900 text-red-600 dark:text-red-300 px-1.5 py-0.5 rounded-md text-sm font-mono border border-zinc-300 dark:border-zinc-700">
                {children}
              </code>
            );
          },
          table: ({ node, ...props }) => (
            <table className="table-auto border-collapse border border-gray-400 dark:border-gray-700 my-4" {...props} />
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-gray-100 dark:bg-gray-800" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="border border-gray-400 dark:border-gray-700 px-3 py-1 text-left font-semibold" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="border border-gray-400 dark:border-gray-700 px-3 py-1" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
