/**
 * Number formatting utilities for Servex Holdings
 * Provides consistent formatting for weight, dimensions, and currency display
 */

/**
 * Format weight in kilograms
 * @param {number} weight - Weight value
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted weight with unit
 */
export function formatWeight(weight, decimals = 1) {
  if (weight === null || weight === undefined) return '-';
  const num = parseFloat(weight);
  if (isNaN(num)) return '-';
  return `${num.toFixed(decimals)} kg`;
}

/**
 * Format dimension in centimeters
 * @param {number} dimension - Dimension value in cm
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted dimension with unit
 */
export function formatDimension(dimension, decimals = 0) {
  if (dimension === null || dimension === undefined) return '-';
  const num = parseFloat(dimension);
  if (isNaN(num)) return '-';
  return `${num.toFixed(decimals)} cm`;
}

/**
 * Format dimensions (L x W x H) in centimeters
 * @param {number} length - Length in cm
 * @param {number} width - Width in cm
 * @param {number} height - Height in cm
 * @returns {string} Formatted dimensions
 */
export function formatDimensions(length, width, height) {
  if (!length && !width && !height) return '-';
  const l = parseFloat(length) || 0;
  const w = parseFloat(width) || 0;
  const h = parseFloat(height) || 0;
  return `${l} × ${w} × ${h} cm`;
}

/**
 * Format currency amount
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code (default: 'ZAR')
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted currency amount
 */
export function formatCurrency(amount, currency = 'ZAR', decimals = 2) {
  if (amount === null || amount === undefined) return '-';
  const num = parseFloat(amount);
  if (isNaN(num)) return '-';
  
  const currencySymbols = {
    ZAR: 'R',
    KES: 'KES',
    USD: '$',
    EUR: '€',
    GBP: '£'
  };
  
  const symbol = currencySymbols[currency] || currency;
  const formatted = num.toLocaleString('en-ZA', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
  
  return `${symbol} ${formatted}`;
}

/**
 * Format CBM (cubic meters)
 * @param {number} cbm - CBM value
 * @param {number} decimals - Number of decimal places (default: 3)
 * @returns {string} Formatted CBM with unit
 */
export function formatCBM(cbm, decimals = 3) {
  if (cbm === null || cbm === undefined) return '-';
  const num = parseFloat(cbm);
  if (isNaN(num)) return '-';
  return `${num.toFixed(decimals)} m³`;
}

/**
 * Format percentage
 * @param {number} value - Percentage value
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted percentage
 */
export function formatPercentage(value, decimals = 1) {
  if (value === null || value === undefined) return '-';
  const num = parseFloat(value);
  if (isNaN(num)) return '-';
  return `${num.toFixed(decimals)}%`;
}

/**
 * Format parcel sequence display (e.g., "1 of 10")
 * @param {number} sequence - Current sequence number
 * @param {number} total - Total in sequence
 * @returns {string} Formatted sequence display or empty string if not applicable
 */
export function formatParcelSequence(sequence, total) {
  if (!sequence || !total || total <= 1) return '';
  return `${sequence} of ${total}`;
}
