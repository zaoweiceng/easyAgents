/**
 * FileDownload - 文件下载组件
 * 显示文件列表并提供下载功能
 */

import { useState, useEffect } from 'react';
import { downloadFile, getFiles } from '../services/api';
import { Download, File, Trash2, RefreshCw } from 'lucide-react';

const FileDownload = ({ sessionId, onFileDelete }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState({});

  // 加载文件列表
  const loadFiles = async () => {
    setLoading(true);
    try {
      const result = sessionId
        ? await getFiles(sessionId)
        : await getFiles();

      setFiles(result.files || []);
    } catch (error) {
      console.error('加载文件列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [sessionId]);

  // 下载文件
  const handleDownload = async (file) => {
    setDownloading((prev) => ({ ...prev, [file.file_id]: true }));

    try {
      const blob = await downloadFile(file.file_id);

      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.original_filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('下载失败:', error);
      alert(`下载失败: ${error.message}`);
    } finally {
      setDownloading((prev) => ({ ...prev, [file.file_id]: false }));
    }
  };

  // 删除文件
  const handleDelete = async (fileId) => {
    if (!confirm('确定要删除这个文件吗？')) {
      return;
    }

    try {
      await deleteFile(fileId);
      setFiles((prev) => prev.filter((f) => f.file_id !== fileId));

      if (onFileDelete) {
        onFileDelete(fileId);
      }
    } catch (error) {
      console.error('删除失败:', error);
      alert(`删除失败: ${error.message}`);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getFileIcon = (contentType) => {
    // 根据文件类型返回不同的图标
    if (contentType?.includes('image')) return '🖼️';
    if (contentType?.includes('pdf')) return '📕';
    if (contentType?.includes('word') || contentType?.includes('document')) return '📘';
    if (contentType?.includes('excel') || contentType?.includes('spreadsheet') || contentType?.includes('csv')) return '📗';
    if (contentType?.includes('zip') || contentType?.includes('rar') || contentType?.includes('compressed')) return '📦';
    return '📄';
  };

  return (
    <div className="file-download">
      <div className="header">
        <h3>文件列表</h3>
        <button
          className="refresh-btn"
          onClick={loadFiles}
          disabled={loading}
          title="刷新"
        >
          <RefreshCw size={18} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      {loading ? (
        <div className="loading">加载中...</div>
      ) : files.length === 0 ? (
        <div className="empty">暂无文件</div>
      ) : (
        <div className="file-list">
          {files.map((file) => (
            <div key={file.file_id} className="file-item">
              <div className="file-icon">{getFileIcon(file.content_type)}</div>

              <div className="file-info">
                <div className="file-name" title={file.original_filename}>
                  {file.original_filename}
                </div>
                <div className="file-meta">
                  <span className="file-size">{formatFileSize(file.file_size)}</span>
                  <span className="file-date">
                    {new Date(file.created_at).toLocaleString('zh-CN')}
                  </span>
                </div>
              </div>

              <div className="file-actions">
                <button
                  className="action-btn download-btn"
                  onClick={() => handleDownload(file)}
                  disabled={downloading[file.file_id]}
                  title="下载"
                >
                  <Download size={18} />
                  {downloading[file.file_id] ? '下载中...' : '下载'}
                </button>

                <button
                  className="action-btn delete-btn"
                  onClick={() => handleDelete(file.file_id)}
                  title="删除"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .file-download {
          width: 100%;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .header h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }

        .refresh-btn {
          padding: 6px;
          background: none;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          cursor: pointer;
          color: #666;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .refresh-btn:hover:not(:disabled) {
          background: #f5f5f5;
          border-color: #2196F3;
          color: #2196F3;
        }

        .refresh-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .refresh-btn svg.spinning {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .loading,
        .empty {
          text-align: center;
          padding: 32px;
          color: #999;
          font-size: 14px;
        }

        .file-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .file-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 6px;
          transition: all 0.2s;
        }

        .file-item:hover {
          border-color: #2196F3;
          box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);
        }

        .file-icon {
          font-size: 32px;
          flex-shrink: 0;
        }

        .file-info {
          flex: 1;
          min-width: 0;
        }

        .file-name {
          font-size: 14px;
          font-weight: 500;
          color: #333;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          margin-bottom: 4px;
        }

        .file-meta {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: #999;
        }

        .file-actions {
          display: flex;
          gap: 8px;
          flex-shrink: 0;
        }

        .action-btn {
          padding: 6px 12px;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          background: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          transition: all 0.2s;
        }

        .download-btn:hover:not(:disabled) {
          background: #2196F3;
          color: white;
          border-color: #2196F3;
        }

        .download-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .delete-btn:hover {
          background: #f44336;
          color: white;
          border-color: #f44336;
        }
      `}</style>
    </div>
  );
};

export default FileDownload;
