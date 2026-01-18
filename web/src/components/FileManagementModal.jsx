/**
 * File Management Modal - 文件管理窗口
 */
import { useState, useEffect } from 'react';
import { Folder, Download, Trash2, Copy, RefreshCw, File, Search, Check, X } from 'lucide-react';
import { ConfirmDialog } from './ConfirmDialog';
import { getFiles, deleteFile, downloadFile } from '../services/api';
import './FileManagementModal.css';

export const FileManagementModal = ({ isOpen, onClose }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, fileId: null, fileName: null });
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchFiles();
    }
  }, [isOpen]);

  const fetchFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFiles(null, 1000); // 获取所有文件，不限制会话
      setFiles(data.files || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (fileId, fileName) => {
    setDeleteConfirm({ show: true, fileId, fileName });
  };

  const confirmDelete = async () => {
    const { fileId, fileName } = deleteConfirm;
    setDeleteConfirm({ show: false, fileId: null, fileName: null });

    try {
      await deleteFile(fileId);
      setSuccessMessage(`文件 "${fileName}" 已删除`);
      setFiles(prev => prev.filter(f => f.file_id !== fileId));
      setSelectedFiles(prev => {
        const newSet = new Set(prev);
        newSet.delete(fileId);
        return newSet;
      });

      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(`删除失败: ${err.message}`);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedFiles.size === 0) return;
    setBatchDeleteConfirm(true);
  };

  const confirmBatchDelete = async () => {
    setBatchDeleteConfirm(false);
    setLoading(true);
    setError(null);

    try {
      const promises = Array.from(selectedFiles).map(fileId => deleteFile(fileId));
      await Promise.all(promises);

      setSuccessMessage(`已删除 ${selectedFiles.size} 个文件`);
      setFiles(prev => prev.filter(f => !selectedFiles.has(f.file_id)));
      setSelectedFiles(new Set());

      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(`批量删除失败: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (fileId, fileName) => {
    try {
      const blob = await downloadFile(fileId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(`下载失败: ${err.message}`);
    }
  };

  const handleCopyId = (fileId) => {
    navigator.clipboard.writeText(fileId).then(() => {
      setSuccessMessage(`文件ID已复制: ${fileId}`);
      setTimeout(() => setSuccessMessage(null), 3000);
    }).catch(err => {
      setError('复制失败');
    });
  };

  const handleSelectFile = (fileId) => {
    setSelectedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fileId)) {
        newSet.delete(fileId);
      } else {
        newSet.add(fileId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    const filteredFiles = getFilteredFiles();
    if (selectedFiles.size === filteredFiles.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(filteredFiles.map(f => f.file_id)));
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
  };

  const getFilteredFiles = () => {
    if (!searchTerm) return files;
    return files.filter(f =>
      f.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.file_id.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const getFileIcon = (contentType) => {
    return <File size={20} />;
  };

  if (!isOpen) return null;

  const filteredFiles = getFilteredFiles();

  return (
    <div className="file-overlay" onClick={onClose}>
      <div className="file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="file-header">
          <div className="file-header-left">
            <Folder size={24} />
            <h2>文件管理</h2>
          </div>
          <div className="file-header-right">
            <button
              className={`file-refresh-btn ${loading ? 'loading' : ''}`}
              onClick={fetchFiles}
              disabled={loading}
              title="刷新文件列表"
            >
              <RefreshCw size={16} className={loading ? 'spinning' : ''} />
            </button>
            <button className="file-close" onClick={onClose} title="关闭">×</button>
          </div>
        </div>

        {/* 成功提示 */}
        {successMessage && (
          <div className="file-success-message">
            <Check size={16} />
            {successMessage}
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="file-error">
            <X size={16} />
            {error}
            <button onClick={() => setError(null)} className="error-close">×</button>
          </div>
        )}

        {/* 工具栏 */}
        <div className="file-toolbar">
          <div className="file-search">
            <Search size={18} />
            <input
              type="text"
              placeholder="搜索文件名或ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="file-actions">
            {selectedFiles.size > 0 && (
              <button
                className="file-batch-delete-btn"
                onClick={handleBatchDelete}
                disabled={loading}
              >
                <Trash2 size={16} />
                删除选中 ({selectedFiles.size})
              </button>
            )}
            <div className="file-count">
              共 {files.length} 个文件
              {filteredFiles.length !== files.length && ` (筛选: ${filteredFiles.length})`}
            </div>
          </div>
        </div>

        {/* 文件列表 */}
        <div className="file-content">
          {loading && files.length === 0 ? (
            <div className="file-loading">
              <RefreshCw size={32} className="spinning" />
              <p>加载中...</p>
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="file-empty">
              <Folder size={48} />
              <p>{searchTerm ? '没有找到匹配的文件' : '暂无文件'}</p>
            </div>
          ) : (
            <div className="file-list">
              <div className="file-list-header">
                <label className="file-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedFiles.size === filteredFiles.length && filteredFiles.length > 0}
                    onChange={handleSelectAll}
                  />
                </label>
                <div className="file-info-header">文件信息</div>
                <div className="file-size-header">大小</div>
                <div className="file-date-header">创建时间</div>
                <div className="file-actions-header">操作</div>
              </div>
              {filteredFiles.map((file) => (
                <div
                  key={file.file_id}
                  className={`file-item ${selectedFiles.has(file.file_id) ? 'selected' : ''}`}
                >
                  <label className="file-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(file.file_id)}
                      onChange={() => handleSelectFile(file.file_id)}
                    />
                  </label>
                  <div className="file-info">
                    <div className="file-icon">{getFileIcon(file.content_type)}</div>
                    <div className="file-details">
                      <div className="file-name" title={file.original_filename}>
                        {file.original_filename}
                      </div>
                      <div className="file-id" title={file.file_id}>
                        ID: {file.file_id}
                      </div>
                      {file.session_id && (
                        <div className="file-session" title={file.session_id}>
                          会话: {file.session_id.substring(0, 8)}...
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="file-size">
                    {formatFileSize(file.file_size)}
                  </div>
                  <div className="file-date">
                    {formatDate(file.created_at)}
                  </div>
                  <div className="file-actions">
                    <button
                      className="file-action-btn"
                      onClick={() => handleCopyId(file.file_id)}
                      title="复制ID"
                    >
                      <Copy size={16} />
                    </button>
                    <button
                      className="file-action-btn"
                      onClick={() => handleDownload(file.file_id, file.original_filename)}
                      title="下载"
                    >
                      <Download size={16} />
                    </button>
                    <button
                      className="file-action-btn file-delete-btn"
                      onClick={() => handleDelete(file.file_id, file.original_filename)}
                      title="删除"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        isOpen={deleteConfirm.show}
        title="删除文件"
        message={`确定要删除文件 "${deleteConfirm.fileName}" 吗？此操作不可恢复。`}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteConfirm({ show: false, fileId: null, fileName: null })}
      />

      {/* 批量删除确认对话框 */}
      <ConfirmDialog
        isOpen={batchDeleteConfirm}
        title="批量删除文件"
        message={`确定要删除选中的 ${selectedFiles.size} 个文件吗？此操作不可恢复。`}
        onConfirm={confirmBatchDelete}
        onCancel={() => setBatchDeleteConfirm(false)}
      />
    </div>
  );
};
