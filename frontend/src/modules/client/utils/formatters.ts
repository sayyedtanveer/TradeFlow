const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
})

const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
})

export function formatCurrency(value: number | null | undefined, fallback = "--") {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return fallback
  }

  return currencyFormatter.format(value)
}

export function formatDate(value: string | null | undefined, fallback = "--") {
  if (!value) {
    return fallback
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return dateFormatter.format(date)
}

export function formatDateTime(value: string | null | undefined, fallback = "--") {
  if (!value) {
    return fallback
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return dateTimeFormatter.format(date)
}

export function formatStatusLabel(value: string | null | undefined, fallback = "--") {
  if (!value) {
    return fallback
  }

  return value
    .toLowerCase()
    .split("_")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ")
}

export function clampPercent(value: number | null | undefined) {
  return Math.max(0, Math.min(100, value ?? 0))
}

export function formatAddress(address: {
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  postal_code?: string | null
  country?: string | null
}) {
  const locality = [address.city, address.state].filter(Boolean).join(", ")
  const postal = [address.postal_code, address.country].filter(Boolean).join(" ")

  return [address.address_line1, address.address_line2, locality, postal].filter(Boolean).join(", ")
}
