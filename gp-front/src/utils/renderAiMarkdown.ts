/**
 * AI 助手回复：Markdown → HTML，并用 DOMPurify 净化（防 XSS）。
 */
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const defaultLinkOpen =
  md.renderer.rules.link_open ||
  function (tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }

md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  const t = tokens[idx]
  if (t) {
    t.attrSet('target', '_blank')
    t.attrSet('rel', 'noopener noreferrer')
  }
  return defaultLinkOpen(tokens, idx, options, env, self)
}

export function renderAiMarkdown(text: string): string {
  const raw = md.render(text || '')
  return DOMPurify.sanitize(raw)
}
