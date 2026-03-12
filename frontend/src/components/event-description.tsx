"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface EventDescriptionProps {
  content: string;
}

export function EventDescription({ content }: EventDescriptionProps) {
  return (
    <div className="prose prose-sm max-w-none text-muted-foreground prose-headings:text-foreground prose-strong:text-foreground prose-a:text-primary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          img: ({ src, alt, ...props }) => (
            <img
              src={src}
              alt={alt || ""}
              className="rounded-lg max-w-full h-auto my-3"
              loading="lazy"
              {...props}
            />
          ),
          a: ({ href, children, ...props }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
              {...props}
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
