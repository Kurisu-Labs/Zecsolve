import { formatZat, formatZec } from './money'
import { caseStateLabel, chainView, findingView, receiptView, formatWhen } from './status'

const limitations: Record<string, string> = {
  SELECTED_FIELDS_ONLY: 'Only the sections selected for this access are included.',
  UNSELECTED_OR_UNCONSENTED_MATERIAL_OMITTED:
    'Information outside this scope or without sharing consent is omitted.',
  HISTORICAL_OBSERVATIONS_ARE_NOT_FRESH_CONFIRMATION:
    'Historical chain observations do not establish current confirmation.',
  PROJECTED_HISTORY_IS_NOT_A_COMPLETE_AUDIT_CHAIN:
    'This shared history is a limited view of the complete audit trail.',
}

export function limitationLabel(code: string): string {
  return limitations[code] ?? code.replaceAll('_', ' ').toLowerCase()
}

export function reportValue(value: unknown, field = ''): string {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number' && field.endsWith('_zat') && Number.isSafeInteger(value) && value >= 0)
    return `${formatZat(value)} zat (${formatZec(value)} ZEC)`
  if (typeof value !== 'string') return String(value)
  if (field.endsWith('_at') && !Number.isNaN(Date.parse(value))) return formatWhen(value)
  if (field === 'findings') return findingView[value as keyof typeof findingView]?.label ?? value
  if (field === 'receipt_state') return receiptView[value as keyof typeof receiptView]?.label ?? value
  if (field === 'state')
    return (
      caseStateLabel[value as keyof typeof caseStateLabel] ??
      chainView[value as keyof typeof chainView]?.label ??
      value
    )
  if (field === 'source_kind' && value === 'SIMULATED') return 'Simulated source (test only)'
  return value
}
