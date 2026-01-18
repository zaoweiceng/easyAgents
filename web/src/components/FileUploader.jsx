/**
 * FileUploader - 文件上传组件
 * 支持拖拽上传和点击上传
 */

import { useState, useRef } from 'react';
import { uploadFile } from '../services/api';
import { Upload, File, X } from 'lucide-react';

const FileUploader = ({ onUploadSuccess, sessionId, multiple = false }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const fileInputRef = useRef(null);

  // 支持的文件类型
  const acceptedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv',
    'image/jpeg',
    'image/png',
    'image/gif',
    'text/plain',
    'application/json',
    'application/zip',
  ];

  // 最大文件大小 (100MB)
  const MAX_SIZE = 100 * 1024 * 1024;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
  };

  const validateFile = (file) => {
    // 检查文件大小
    if (file.size > MAX_SIZE) {
      alert(`文件 "${file.name}" 超过大小限制 (最大 100MB)`);
      return false;
    }

    // 检查文件类型（通过扩展名）
    const ext = file.name.split('.').pop().toLowerCase();
    const allowedExts = [
      'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv',
      'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
      'txt', 'md', 'json', 'xml', 'yaml', 'yml',
      'zip', 'rar', '7z', 'tar', 'gz',
      'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'c', 'cpp', 'h'
    ];

    if (!allowedExts.includes(ext)) {
      alert(`不支持的文件类型: .${ext}`);
      return false;
    }

    return true;
  };

  const handleFiles = async (files) => {
    if (!multiple && files.length > 1) {
      alert('只能上传一个文件');
      return;
    }

    // 验证文件
    const validFiles = files.filter(validateFile);
    if (validFiles.length === 0) {
      return;
    }

    setUploading(true);

    try {
      for (const file of validFiles) {
        const result = await uploadFile(file, sessionId);

        const fileInfo = {
          ...result.file,
          localName: file.name,
        };

        setUploadedFiles((prev) => [...prev, fileInfo]);

        // 通知父组件
        if (onUploadSuccess) {
          onUploadSuccess(fileInfo);
        }
      }
    } catch (error) {
      console.error('上传失败:', error);
      alert(`上传失败: ${error.message}`);
    } finally {
      setUploading(false);
      // 重置input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const removeFile = (fileId) => {
    setUploadedFiles((prev) => prev.filter((f) => f.file_id !== fileId));
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="file-uploader">
      {/* 上传区域 */}
      <div
        className={`upload-area ${isDragging ? 'dragging' : ''} ${uploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={acceptedTypes.join(',')}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          disabled={uploading}
        />

        <div className="upload-icon">
          {uploading ? (
            <div className="spinner"></div>
          ) : (
            <Upload size={48} />
          )}
        </div>

        <p className="upload-text">
          {uploading ? '上传中...' : '拖拽文件到此处或点击上传'}
        </p>

        <p className="upload-hint">
          支持PDF、Word、Excel、图片等格式，最大100MB
        </p>
      </div>

      {/* 已上传文件列表 */}
      {uploadedFiles.length > 0 && (
        <div className="uploaded-files">
          <h4>已上传文件</h4>
          {uploadedFiles.map((file) => (
            <div key={file.file_id} className="file-item">
              <File size={20} />
              <div className="file-info">
                <span className="file-name">{file.original_filename}</span>
                <span className="file-size">{formatFileSize(file.file_size)}</span>
              </div>
              <button
                className="remove-btn"
                onClick={() => removeFile(file.file_id)}
                title="移除"
              >
                <X size={18} />
              </button>
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .file-uploader {
          width: 100%;
        }

        .upload-area {
          border: 2px dashed #ccc;
          border-radius: 8px;
          padding: 32px;
          text-align: center;
          cursor: pointer;
          transition: all 0.3s;
          background: #fafafa;
        }

        .upload-area:hover {
          border-color: #666;
          background: #f5f5f5;
        }

        .upload-area.dragging {
          border-color: #2196F3;
          background: #e3f2fd;
        }

        .upload-area.uploading {
          cursor: not-allowed;
          opacity: 0.7;
        }

        .upload-icon {
          display: flex;
          justify-content: center;
          align-items: center;
          margin-bottom: 16px;
          color: #666;
        }

        .upload-text {
          margin: 0 0 8px 0;
          font-size: 16px;
          font-weight: 500;
          color: #333;
        }

        .upload-hint {
          margin: 0;
          font-size: 13px;
          color: #999;
        }

        .uploaded-files {
          margin-top: 16px;
        }

        .uploaded-files h4 {
          margin: 0 0 12px 0;
          font-size: 14px;
          font-weight: 600;
          color: #333;
        }

        .file-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 6px;
          margin-bottom: 8px;
        }

        .file-item svg {
          flex-shrink: 0;
          color: #666;
        }

        .file-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 4px;
          min-width: 0;
        }

        .file-name {
          font-size: 14px;
          font-weight: 500;
          color: #333;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .file-size {
          font-size: 12px;
          color: #999;
        }

        .remove-btn {
          flex-shrink: 0;
          padding: 4px;
          background: none;
          border: none;
          cursor: pointer;
          color: #999;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .remove-btn:hover {
          background: #f5f5f5;
          color: #f44336;
        }

        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #f3f3f3;
          border-top: 3px solid #2196F3;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default FileUploader;
