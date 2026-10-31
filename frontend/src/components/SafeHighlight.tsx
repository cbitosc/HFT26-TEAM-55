import React from 'react';

interface SafeHighlightProps {
  text: string;
}

/**
 * Tokenizes text containing SQLite FTS5 `<mark>` and `</mark>` tags.
 * Renders matched tokens inside `<mark>` React elements and all other
 * text as safe, automatically-escaped React string text nodes.
 * Completely eliminates XSS / raw HTML injection vulnerabilities.
 */
export const SafeHighlight: React.FC<SafeHighlightProps> = ({ text }) => {
  if (!text) return null;

  // Split text by <mark>...</mark> captures while retaining the matched tokens
  const markRegex = /(<mark>[\s\S]*?<\/mark>)/g;
  const tokens = text.split(markRegex);

  return (
    <>
      {tokens.map((token, index) => {
        if (!token) return null;
        if (token.startsWith('<mark>') && token.endsWith('</mark>') && token.length >= 13) {
          const innerText = token.slice(6, -7);
          return (
            <mark key={index} className="fts5-mark">
              {innerText}
            </mark>
          );
        }
        // Render as standard React text node (escapes any raw HTML entities like <script>, <img>, etc.)
        return <React.Fragment key={index}>{token}</React.Fragment>;
      })}
    </>
  );
};
