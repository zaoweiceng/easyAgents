/**
 * FormComponent - 动态表单组件
 * 根据 form_config 渲染不同类型的表单字段
 */
import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import './FormComponent.css';

export const FormComponent = ({ formConfig, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({});
  const [errors, setErrors] = useState({});

  const handleChange = (fieldName, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }));
    // 清除该字段的错误
    if (errors[fieldName]) {
      setErrors(prev => ({
        ...prev,
        [fieldName]: null
      }));
    }
  };

  const handleTableChange = (fieldName, rowIndex, columnField, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: prev[fieldName].map((row, idx) =>
        idx === rowIndex ? { ...row, [columnField]: value } : row
      )
    }));
  };

  const addTableRow = (fieldName) => {
    const field = formConfig.fields.find(f => f.field_name === fieldName);
    if (!field) return;

    const maxRows = field.max_rows || 10;
    const currentRows = formData[fieldName] || [];

    if (currentRows.length < maxRows) {
      const newRow = {};
      field.columns.forEach(col => {
        newRow[col.field] = '';
      });
      setFormData(prev => ({
        ...prev,
        [fieldName]: [...currentRows, newRow]
      }));
    }
  };

  const removeTableRow = (fieldName, rowIndex) => {
    const field = formConfig.fields.find(f => f.field_name === fieldName);
    if (!field) return;

    const minRows = field.min_rows || 1;
    const currentRows = formData[fieldName] || [];

    if (currentRows.length > minRows) {
      setFormData(prev => ({
        ...prev,
        [fieldName]: currentRows.filter((_, idx) => idx !== rowIndex)
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    formConfig.fields.forEach(field => {
      if (field.required) {
        const value = formData[field.field_name];

        if (field.field_type === 'table') {
          if (!value || value.length === 0) {
            newErrors[field.field_name] = `${field.label} 不能为空`;
          }
        } else if (!value || (typeof value === 'string' && value.trim() === '')) {
          newErrors[field.field_name] = `${field.label} 不能为空`;
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (validateForm()) {
      onSubmit(formData);
    }
  };

  const renderField = (field) => {
    const value = formData[field.field_name] || '';

    switch (field.field_type) {
      case 'radio':
        return (
          <div key={field.field_name} className="form-field">
            <label className="field-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            <div className="radio-group">
              {field.options.map((option, idx) => (
                <label key={idx} className="radio-option">
                  <input
                    type="radio"
                    name={field.field_name}
                    value={option}
                    checked={value === option}
                    onChange={(e) => handleChange(field.field_name, e.target.value)}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
            {errors[field.field_name] && (
              <span className="error-message">{errors[field.field_name]}</span>
            )}
          </div>
        );

      case 'checkbox':
        return (
          <div key={field.field_name} className="form-field">
            <label className="field-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            <div className="checkbox-group">
              {field.options.map((option, idx) => (
                <label key={idx} className="checkbox-option">
                  <input
                    type="checkbox"
                    checked={(value || []).includes(option)}
                    onChange={(e) => {
                      const currentValues = formData[field.field_name] || [];
                      if (e.target.checked) {
                        handleChange(field.field_name, [...currentValues, option]);
                      } else {
                        handleChange(field.field_name, currentValues.filter(v => v !== option));
                      }
                    }}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
            {errors[field.field_name] && (
              <span className="error-message">{errors[field.field_name]}</span>
            )}
          </div>
        );

      case 'textarea':
        return (
          <div key={field.field_name} className="form-field">
            <label className="field-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            <textarea
              className="textarea-input"
              value={value}
              onChange={(e) => handleChange(field.field_name, e.target.value)}
              placeholder={field.placeholder || ''}
              rows={4}
            />
            {errors[field.field_name] && (
              <span className="error-message">{errors[field.field_name]}</span>
            )}
          </div>
        );

      case 'number':
        return (
          <div key={field.field_name} className="form-field">
            <label className="field-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            <input
              type="number"
              className="text-input"
              value={value}
              onChange={(e) => handleChange(field.field_name, e.target.value)}
              placeholder={field.placeholder || ''}
            />
            {errors[field.field_name] && (
              <span className="error-message">{errors[field.field_name]}</span>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={field.field_name} className="form-field">
            <label className="field-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            <select
              className="select-input"
              value={value}
              onChange={(e) => handleChange(field.field_name, e.target.value)}
            >
              <option value="">请选择...</option>
              {field.options.map((option, idx) => (
                <option key={idx} value={option}>{option}</option>
              ))}
            </select>
            {errors[field.field_name] && (
              <span className="error-message">{errors[field.field_name]}</span>
            )}
          </div>
        );

      case 'table':
        const tableData = formData[field.field_name] || [];
        return (
          <div key={field.field_name} className="form-field">
            <label className="field-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    {field.columns.map((col, idx) => (
                      <th key={idx}>{col.header}</th>
                    ))}
                    <th className="action-column">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {tableData.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {field.columns.map((col, colIdx) => (
                        <td key={colIdx}>
                          {col.type === 'number' ? (
                            <input
                              type="number"
                              value={row[col.field] || ''}
                              onChange={(e) => handleTableChange(
                                field.field_name,
                                rowIndex,
                                col.field,
                                e.target.value
                              )}
                              className="table-cell-input"
                            />
                          ) : (
                            <input
                              type="text"
                              value={row[col.field] || ''}
                              onChange={(e) => handleTableChange(
                                field.field_name,
                                rowIndex,
                                col.field,
                                e.target.value
                              )}
                              className="table-cell-input"
                            />
                          )}
                        </td>
                      ))}
                      <td className="action-column">
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => removeTableRow(field.field_name, rowIndex)}
                          disabled={tableData.length <= (field.min_rows || 1)}
                          title="删除此行"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button
                type="button"
                className="add-row-button"
                onClick={() => addTableRow(field.field_name)}
                disabled={tableData.length >= (field.max_rows || 10)}
              >
                <Plus size={16} />
                添加行
              </button>
            </div>
            {errors[field.field_name] && (
              <span className="error-message">{errors[field.field_name]}</span>
            )}
          </div>
        );

      default: // text
        return (
          <div key={field.field_name} className="form-field">
            <label className="field-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            <input
              type="text"
              className="text-input"
              value={value}
              onChange={(e) => handleChange(field.field_name, e.target.value)}
              placeholder={field.placeholder || ''}
            />
            {errors[field.field_name] && (
              <span className="error-message">{errors[field.field_name]}</span>
            )}
          </div>
        );
    }
  };

  return (
    <div className="form-component">
      {formConfig.form_title && (
        <h3 className="form-title">{formConfig.form_title}</h3>
      )}
      {formConfig.form_description && (
        <p className="form-description">{formConfig.form_description}</p>
      )}
      <form onSubmit={handleSubmit} className="dynamic-form">
        {formConfig.fields.map(field => renderField(field))}
        <div className="form-actions">
          <button type="submit" className="submit-button">
            提交
          </button>
          {onCancel && (
            <button type="button" className="cancel-button" onClick={onCancel}>
              取消
            </button>
          )}
        </div>
      </form>
    </div>
  );
};
