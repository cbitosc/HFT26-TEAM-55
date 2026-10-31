import React from 'react';

interface SafeMarkdownProps {
  content: string;
}

/**
 * Pure React safe Markdown renderer.
 * Does NOT use dangerouslySetInnerHTML; all text is rendered into React nodes,
 * preventing XSS, script injection, and unintended HTML rendering.
 */
export const SafeMarkdown: React.FC<SafeMarkdownProps> = ({ content }) => {
  if (!content) return null;

  const renderInline = (text: string): React.ReactNode[] => {
    const nodes: React.ReactNode[] = [];
    // Tokenize inline markdown: `code`, **bold**, *italic*
    const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
    const parts = text.split(regex);

    parts.forEach((part, idx) => {
      if (!part) return;
      if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
        nodes.push(
          <code key={idx} className="safe-inline-code">
            {part.slice(1, -1)}
          </code>
        );
      } else if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        nodes.push(
          <strong key={idx} className="safe-bold">
            {part.slice(2, -2)}
          </strong>
        );
      } else if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
        nodes.push(
          <em key={idx} className="safe-italic">
            {part.slice(1, -1)}
          </em>
        );
      } else {
        nodes.push(part);
      }
    });

    return nodes;
  };

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockLines: string[] = [];
  let codeBlockLang = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code fence handling
    if (line.trim().startsWith('```')) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBlockLang = line.trim().slice(3).trim();
        codeBlockLines = [];
      } else {
        inCodeBlock = false;
        elements.push(
          <div key={`codeblock-${i}`} className="safe-code-block-wrap">
            {codeBlockLang && <span className="safe-code-lang">{codeBlockLang}</span>}
            <pre className="safe-pre-code">
              <code>{codeBlockLines.join('\n')}</code>
            </pre>
          </div>
        );
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Headings
    if (line.startsWith('### ')) {
      elements.push(
        <h4 key={`h3-${i}`} className="safe-h3">
          {renderInline(line.slice(4))}
        </h4>
      );
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h3 key={`h2-${i}`} className="safe-h2">
          {renderInline(line.slice(3))}
        </h3>
      );
      continue;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <h2 key={`h1-${i}`} className="safe-h1">
          {renderInline(line.slice(2))}
        </h2>
      );
      continue;
    }

    // Unordered lists
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      elements.push(
        <div key={`li-${i}`} className="safe-list-item">
          <span className="safe-bullet">•</span>
          <span className="safe-list-text">{renderInline(line.trim().slice(2))}</span>
        </div>
      );
      continue;
    }

    // Numbered lists
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      elements.push(
        <div key={`nli-${i}`} className="safe-list-item">
          <span className="safe-num">{numMatch[1]}.</span>
          <span className="safe-list-text">{renderInline(numMatch[2])}</span>
        </div>
      );
      continue;
    }

    // Blank line
    if (!line.trim()) {
      continue;
    }

    // Standard paragraph
    elements.push(
      <p key={`p-${i}`} className="safe-p">
        {renderInline(line)}
      </p>
    );
  }

  // Handle unclosed code block if model output was truncated
  if (inCodeBlock && codeBlockLines.length > 0) {
    elements.push(
      <div key="unclosed-code" className="safe-code-block-wrap">
        <pre className="safe-pre-code">
          <code>{codeBlockLines.join('\n')}</code>
        </pre>
      </div>
    );
  }

  return <div className="safe-markdown-root">{elements}</div>;
};
