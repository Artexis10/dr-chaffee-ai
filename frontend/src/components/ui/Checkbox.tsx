/**
 * Checkbox Component
 * 
 * Part of the Dr Chaffee AI design system.
 * A themed checkbox that matches the tuning dashboard styling.
 * 
 * Features:
 * - Dark mode support
 * - Optional label and description
 * - Accessible (proper label association, keyboard focus, visible focus ring)
 * - Supports both controlled and uncontrolled usage
 * 
 * Usage:
 * ```tsx
 * <Checkbox
 *   id="my-checkbox"
 *   checked={value}
 *   onChange={(e) => setValue(e.target.checked)}
 *   label="Enable feature"
 *   description="This will turn on the feature"
 * />
 * ```
 */

import React, { forwardRef } from 'react';

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Label content displayed next to the checkbox (can be string or JSX) */
  label?: React.ReactNode;
  /** Optional description text below the label */
  description?: string;
  /** Additional class name for the wrapper */
  wrapperClassName?: string;
}

/**
 * Themed checkbox component for the design system.
 * Reuse this component for all checkbox/toggle inputs in the tuning dashboard.
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, wrapperClassName, className, id, ...props }, ref) => {
    // Generate a unique ID if not provided
    const checkboxId = id || `checkbox-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className={`checkbox-wrapper ${wrapperClassName || ''}`}>
        <label htmlFor={checkboxId} className="checkbox-label">
          <input
            ref={ref}
            type="checkbox"
            id={checkboxId}
            className={`checkbox-input ${className || ''}`}
            {...props}
          />
          {label && (
            <span className="checkbox-label-text">
              {label}
            </span>
          )}
        </label>
        {description && (
          <span className="checkbox-description">{description}</span>
        )}

        <style jsx>{`
          .checkbox-wrapper {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
          }

          .checkbox-label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
            user-select: none;
          }

          .checkbox-input {
            appearance: none;
            -webkit-appearance: none;
            width: 1.125rem;
            height: 1.125rem;
            border: 1.5px solid var(--border-subtle, #d1d5db);
            border-radius: 0.25rem;
            background: var(--bg-card, #ffffff);
            cursor: pointer;
            position: relative;
            flex-shrink: 0;
            transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
          }

          .checkbox-input:checked {
            background: var(--accent, #000000);
            border-color: var(--accent, #000000);
          }

          .checkbox-input:checked::after {
            content: '';
            position: absolute;
            left: 5px;
            top: 2px;
            width: 4px;
            height: 8px;
            border: solid white;
            border-width: 0 2px 2px 0;
            transform: rotate(45deg);
          }

          .checkbox-input:focus {
            outline: none;
            box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1);
          }

          .checkbox-input:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }

          .checkbox-label-text {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-primary, #111111);
          }

          .checkbox-description {
            font-size: 0.75rem;
            color: var(--text-muted, #6b7280);
            margin-left: 1.625rem; /* Align with label text (checkbox width + gap) */
          }

          /* Dark mode styles */
          :global(.dark-mode) .checkbox-input {
            background: #1a1a1a;
            border-color: #3a3a3a;
          }

          :global(.dark-mode) .checkbox-input:checked {
            background: var(--accent, #ffffff);
            border-color: var(--accent, #ffffff);
          }

          :global(.dark-mode) .checkbox-input:checked::after {
            border-color: #000000;
          }

          :global(.dark-mode) .checkbox-input:focus {
            box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
          }

          :global(.dark-mode) .checkbox-label-text {
            color: #e5e5e5;
          }

          :global(.dark-mode) .checkbox-description {
            color: #a0a0a0;
          }
        `}</style>
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

export default Checkbox;
