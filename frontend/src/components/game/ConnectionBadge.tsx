import { Wifi, WifiOff, Loader2, AlertTriangle } from 'lucide-react'
import { Badge } from '../ui/Badge'
import type { WsStatus } from '../../stores/gameStore'

const config: Record<
  WsStatus,
  { label: string; tone: 'success' | 'warning' | 'error' | 'neutral'; icon: typeof Wifi }
> = {
  idle: { label: '未连接', tone: 'neutral', icon: WifiOff },
  connecting: { label: '连接中', tone: 'warning', icon: Loader2 },
  connected: { label: '已连接', tone: 'success', icon: Wifi },
  disconnected: { label: '重连中', tone: 'warning', icon: Loader2 },
  error: { label: '异常', tone: 'error', icon: AlertTriangle },
}

export function ConnectionBadge({
  status,
  detail,
  mini = false,
}: {
  status: WsStatus
  detail?: string | null
  mini?: boolean
}) {
  const c = config[status]
  const Icon = c.icon
  const shortDetail =
    status === 'error' || status === 'disconnected' ? detail ?? c.label : c.label
  const title = detail && detail !== shortDetail ? detail : shortDetail

  if (mini) {
    return (
      <Badge tone={c.tone} className="hud-chip hud-chip--icon" title={title}>
        <Icon className={cnIcon(status)} aria-hidden />
      </Badge>
    )
  }

  return (
    <Badge tone={c.tone} className="max-w-full gap-1 hud-chip" title={title}>
      <Icon className={cnIcon(status)} aria-hidden />
      <span className="truncate">{shortDetail}</span>
    </Badge>
  )
}

function cnIcon(status: WsStatus) {
  return status === 'connecting' || status === 'disconnected'
    ? 'h-3 w-3 shrink-0 animate-spin'
    : 'h-3 w-3 shrink-0'
}
