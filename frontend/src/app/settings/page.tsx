'use client';

import React from 'react';

/**
 * Settings page - user preferences and configuration
 */
export default function SettingsPage() {
  return (
    <div className="space-y-lg">
      <div className="space-y-md">
        <h1 className="text-display-md font-bold text-text-primary">
          Settings
        </h1>
        <p className="text-body-lg text-text-secondary">
          Configure preferences and application settings
        </p>
      </div>

      <div className="rounded-lg border border-border-light bg-surface p-xl">
        <p className="text-center text-body-md text-text-tertiary py-2xl">
          Settings panel coming soon. Manage preferences, connected wallet, and display options.
        </p>
      </div>
    </div>
  );
}
