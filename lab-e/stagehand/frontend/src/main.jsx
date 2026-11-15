import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import { configure } from './api.js';
import './styles.css';

// Runtime settings (API base path, feature switches) are fetched, not built in.
fetch('/app-config.json')
  .then((response) => response.json())
  .catch(() => ({}))
  .then((config) => {
    configure(config);
    // Page-only state: readable by script running in the page, not by a request.
    window.__stagehand = { build: ['SH', 'E02', '4d0f6a27'].join('-'), site: config.siteName || 'Stagehand' };
    createRoot(document.getElementById('root')).render(<App />);
  });
