/**
 * MarkdownRenderer Component - 渲染Markdown内容
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import './MarkdownRenderer.css';

export const MarkdownRenderer = ({ content }) => {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // 自定义链接渲染，在新窗口打开
          a: ({ node, ...props }) => {
            // 检查是否是下载链接
            const isDownloadLink = props.href?.includes('/files/');

            return (
              <a
                {...props}
                target={isDownloadLink ? '_blank' : undefined}
                rel={isDownloadLink ? 'noopener noreferrer' : undefined}
                className={isDownloadLink ? 'download-link' : undefined}
              />
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
