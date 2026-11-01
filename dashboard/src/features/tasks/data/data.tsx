import {TriangleAlert, CircleCheckBig, Clock} from 'lucide-react'

export const labels = [
  {
    value: 'bug',
    label: 'Bug',
  },
  {
    value: 'feature',
    label: 'Feature',
  },
  {
    value: 'documentation',
    label: 'Documentation',
  },
]

// Severity tiers drive badge color. Every status maps to exactly one tier:
//   critical -> red (destructive)   e.g. expired, denied, failed
//   warning  -> amber (warning)     e.g. expiring soon, needs review
//   good     -> green (success)     e.g. valid, approved, done
//   neutral  -> gray (secondary)    e.g. pending, queued, n/a
export type Severity = 'critical' | 'warning' | 'good' | 'neutral'

export const severityToBadgeVariant: Record<Severity, 'destructive' | 'warning' | 'success' | 'secondary'> = {
  critical: 'destructive',
  warning: 'warning',
  good: 'success',
  neutral: 'secondary',
}

// PRODUCT_CUSTOMIZE: replace this list with the real statuses this product
// produces (must match exactly what the backend poller writes to
// records.status). Every status must declare a severity tier above. Default
// values below are generic placeholders only — do not ship as-is.
// __STATUSES_BLOCK_START__
export const statuses: {
  label: string
  value: string
  icon: typeof TriangleAlert
  severity: Severity
}[] = [
  { label: 'Missing', value: 'missing:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Expired', value: 'expired:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Valid', value: 'valid:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Flagged', value: 'flagged:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Needs Review', value: 'needs_review:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Unmapped Employee', value: 'unmapped_employee:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Placeholder Employee', value: 'placeholder_employee:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Duplicate Pool', value: 'duplicate_pool:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Missing Rule Version', value: 'missing_rule_version:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Missing Approval', value: 'missing_approval:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Missing Signature', value: 'missing_signature:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Rule Conflict', value: 'rule_conflict:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Manager In Pool', value: 'manager_in_pool:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Service Charge Misclassified', value: 'service_charge_misclassified:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Catering Unpooled', value: 'catering_unpooled:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Employee Fee Detected', value: 'employee_fee_detected:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Pay Card Required', value: 'pay_card_required:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Vendor Wallet Risk', value: 'vendor_wallet_risk:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Pos Integration Required', value: 'pos_integration_required:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Overtime Impact', value: 'overtime_impact:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Fica Tip Credit Unsupported', value: 'fica_tip_credit_unsupported:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Quickbooks Desktop Mapping Missing', value: 'quickbooks_desktop_mapping_missing:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Approval Pending', value: 'approval_pending:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Signed', value: 'signed:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Locked', value: 'locked:good', icon: CircleCheckBig, severity: 'good' as Severity },
]
// __STATUSES_BLOCK_END__
