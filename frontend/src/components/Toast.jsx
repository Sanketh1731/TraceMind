import React, { useEffect } from 'react';
import { CheckCircleIcon, AlertTriangleIcon, InfoIcon, XIcon } from './Icons';

export function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="tm-toast-container" aria-live="polite">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={() => onDismiss(toast.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }) {
  const { type = 'info', title, message, duration = 4000 } = toast;

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onDismiss, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onDismiss]);

  const icons = {
    success: <CheckCircleIcon size={16} className="toast-icon success" />,
    error: <AlertTriangleIcon size={16} className="toast-icon error" />,
    info: <InfoIcon size={16} className="toast-icon info" />,
  };

  return (
    <div className={`tm-toast-card tm-toast-${type}`}>
      <div className="toast-icon-wrap">{icons[type] || icons.info}</div>
      <div className="toast-content">
        {title && <div className="toast-title">{title}</div>}
        {message && <div className="toast-message">{message}</div>}
      </div>
      <button className="toast-close-btn" onClick={onDismiss} aria-label="Close notification">
        <XIcon size={14} />
      </button>
    </div>
  );
}

export function ConfirmModal({ isOpen, title, message, confirmLabel = "Confirm", cancelLabel = "Cancel", onConfirm, onCancel }) {
  if (!isOpen) return null;

  return (
    <div className="tm-modal-backdrop" onClick={onCancel}>
      <div className="tm-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-row">
            <AlertTriangleIcon size={18} className="modal-warn-icon" />
            <h3>{title}</h3>
          </div>
          <button className="modal-close-btn" onClick={onCancel} aria-label="Close modal">
            <XIcon size={16} />
          </button>
        </div>
        <div className="modal-body">
          <p>{message}</p>
        </div>
        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="button" className="btn-danger" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
