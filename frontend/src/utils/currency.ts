export function formatCurrency(value: number | string, symbol?: string | null): string {
  // Protect against null/undefined or empty symbol, fallback to INR
  const safeSymbol = symbol ? symbol.trim() : "₹";
  
  // Protect against null numeric values
  if (value === null || value === undefined) {
    return `${safeSymbol} 0.00`;
  }
  
  const numValue = Number(value);
  if (isNaN(numValue)) {
    return `${safeSymbol} 0.00`;
  }
  
  return `${safeSymbol} ${numValue.toFixed(2)}`;
}
