import React, { useState } from 'react';
import researchApi from '../../services/researchApi';

export function ResearchExportModal({
  isOpen,
  onClose,
  sessionId,
  sessionScenario,
}) {
  const [format, setFormat] = useState('csv');
  const [isExporting, setIsExporting] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  if (!isOpen) return null;

  const handleDownload = async () => {
    setIsExporting(true);
    setDownloadError(null);
    try {
      const blob = await researchApi.downloadSessionExport(sessionId, format);
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', `${sessionId}_research_export.${format}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);

      setTimeout(() => {
        setIsExporting(false);
        onClose();
      }, 500);
    } catch (err) {
      setDownloadError(err.message || 'Export download failed. Please verify authentication.');
      setIsExporting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container research-export-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="research-badge-accent">DATA EXPORT</span>
            <h3>Export Research Session Data</h3>
          </div>
          <button className="btn-icon close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          <div className="export-session-summary">
            <div>
              <span className="lbl">Session Identifier:</span>
              <strong>{sessionId}</strong>
            </div>
            <div>
              <span className="lbl">Scenario Condition:</span>
              <strong>{sessionScenario}</strong>
            </div>
            <div>
              <span className="lbl">Data Source:</span>
              <strong>SYNTHETIC (Isolated)</strong>
            </div>
            <div>
              <span className="lbl">Nominal Records:</span>
              <strong>3,600 observations (1 Hz)</strong>
            </div>
          </div>

          <div className="export-format-selector">
            <label className="format-label">Select Export Format:</label>
            <div className="format-options">
              <label className={`format-card ${format === 'csv' ? 'active' : ''}`}>
                <input
                  type="radio"
                  name="format"
                  value="csv"
                  checked={format === 'csv'}
                  onChange={() => setFormat('csv')}
                />
                <div className="format-info">
                  <strong>Tabular CSV (.csv)</strong>
                  <span>Comma-separated observations with timestamp, HR, RR, G-load, and evaluated state.</span>
                </div>
              </label>

              <label className={`format-card ${format === 'json' ? 'active' : ''}`}>
                <input
                  type="radio"
                  name="format"
                  value="json"
                  checked={format === 'json'}
                  onChange={() => setFormat('json')}
                />
                <div className="format-info">
                  <strong>Structured JSON (.json)</strong>
                  <span>Full structured object array with schema provenance and per-window evaluations.</span>
                </div>
              </label>
            </div>
          </div>

          {downloadError && (
            <div className="research-error-banner" style={{ margin: '8px 0', padding: '8px 12px', fontSize: '12px' }}>
              <span>⚠️ {downloadError}</span>
            </div>
          )}

          <div className="export-isolation-warning">
            <span>🛡️ <strong>Operational Isolation Notice:</strong> Exported records originate solely from research dataset v1. They contain no actual human patient or live flight data.</span>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={isExporting}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleDownload} disabled={isExporting}>
            {isExporting ? 'Preparing Download...' : `Download ${format.toUpperCase()}`}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ResearchExportModal;
