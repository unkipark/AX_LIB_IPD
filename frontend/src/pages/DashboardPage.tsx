import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { StatusBadge } from '@/components/StatusBadge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { useMeta } from '@/lib/meta'
import type { ThemeColors } from '@/lib/theme'
import { fmtDate } from '@/lib/utils'
import type { CountRow, Dashboard } from '@/types'

const AXIS_FONT = { fontSize: 11, fontFamily: '"IBM Plex Mono", monospace' }

export function DashboardPage({ colors }: { colors: ThemeColors }) {
  const { data, error } = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard })
  const { typeLabel } = useMeta()

  if (error) return <p className="text-sm text-fail">{(error as Error).message}</p>
  if (!data) return <p className="text-sm text-inkMuted">불러오는 중…</p>

  const { kpi } = data
  const tiles: { label: string; value: string; sub?: string }[] = [
    { label: '등록 산출물', value: kpi.artifacts.toLocaleString(), sub: `배포 ${kpi.deployed}건` },
    { label: '등록 참여자', value: kpi.contributors.toLocaleString(), sub: '명' },
    { label: '사용 기록', value: kpi.uses.toLocaleString(), sub: `사용자 ${kpi.users}명` },
    { label: '누적 절감 시간', value: kpi.savedHours.toLocaleString(), sub: '시간' },
    { label: '다운로드', value: kpi.downloads.toLocaleString(), sub: '회' },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {tiles.map((t) => (
          <Card key={t.label}>
            <CardContent className="flex flex-col gap-1">
              <span className="text-xs text-inkMuted">{t.label}</span>
              <span className="font-mono text-2xl font-medium text-ink">{t.value}</span>
              {t.sub && <span className="text-xs text-inkMuted">{t.sub}</span>}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <MonthlyChart title="월별 신규 등록" data={data.monthly} dataKey="created" unit="건" color={colors.series1} colors={colors} />
        <MonthlyChart title="월별 사용 기록" data={data.monthly} dataKey="used" unit="회" color={colors.series2} colors={colors} />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <BarList title="상태별" rows={data.byStatus} filterKey="status" />
        <BarList title="유형별" rows={data.byType} filterKey="type" />
        <BarList title="AI 도구별" rows={data.byTool} filterKey="tool" />
        <BarList title="부서별" rows={data.byDepartment} filterKey="department" />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>많이 쓰인 산출물</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-1">
            {data.topUsed.length === 0 && <Empty />}
            {data.topUsed.map((a, i) => (
              <Link key={a.id} to={`/artifacts/${a.id}`} className="flex items-center gap-2 rounded-panel px-1.5 py-1 text-xs hover:bg-panelRaised">
                <span className="w-4 font-mono text-inkMuted">{i + 1}</span>
                <span className="truncate text-ink">{a.title}</span>
                <span className="ml-auto shrink-0 font-mono text-inkMuted">{a.uses}회 · {a.savedHours}h</span>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>등록 기여자</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-1">
            {data.topContributors.length === 0 && <Empty />}
            {data.topContributors.map((u, i) => (
              <div key={u.id} className="flex items-center gap-2 px-1.5 py-1 text-xs">
                <span className="w-4 font-mono text-inkMuted">{i + 1}</span>
                <span className="text-ink">{u.name}</span>
                {u.department && <span className="truncate text-inkMuted">{u.department}</span>}
                <span className="ml-auto shrink-0 font-mono text-inkMuted">{u.count}건</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>최근 등록</CardTitle>
            <Link to="/artifacts" className="text-xs text-inkMuted hover:text-ink">전체 보기 →</Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {data.recent.length === 0 && <Empty />}
            {data.recent.map((a) => (
              <Link key={a.id} to={`/artifacts/${a.id}`} className="flex items-center gap-2 rounded-panel px-1.5 py-1 text-xs hover:bg-panelRaised">
                <StatusBadge status={a.status} />
                <span className="truncate text-ink">{a.title}</span>
                <span className="ml-auto shrink-0 text-inkMuted">{typeLabel(a.type)} · {fmtDate(a.createdAt)}</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Empty() {
  return <p className="py-4 text-center text-xs text-inkMuted">아직 데이터가 없습니다.</p>
}

function MonthlyChart({
  title,
  data,
  dataKey,
  unit,
  color,
  colors,
}: {
  title: string
  data: Dashboard['monthly']
  dataKey: 'created' | 'used'
  unit: string
  color: string
  colors: ThemeColors
}) {
  const axis = { ...AXIS_FONT, fill: colors.inkMuted }
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <span className="text-xs text-inkMuted">최근 12개월</span>
      </CardHeader>
      <div className="h-56 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid stroke={colors.grid} strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="month" tick={axis} tickFormatter={(m: string) => `${Number(m.slice(5))}월`}
              tickLine={false} axisLine={{ stroke: colors.grid }} />
            <YAxis allowDecimals={false} tick={axis} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: colors.grid, fillOpacity: 0.4 }}
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <div className="rounded-panel border border-line bg-panelRaised px-2.5 py-1.5 text-xs shadow-lg">
                    <p className="text-inkMuted">{label}</p>
                    <p className="font-mono text-ink">{payload[0].value}{unit}</p>
                  </div>
                ) : null
              }
            />
            <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

/** 분포는 가로 막대 목록으로 보여줍니다. 라벨·값이 텍스트라 색에 의존하지 않고,
 *  행을 누르면 그 조건으로 필터된 산출물 목록으로 이동합니다. */
function BarList({ title, rows, filterKey }: { title: string; rows: CountRow[]; filterKey: string }) {
  const max = Math.max(1, ...rows.map((r) => r.count))
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-0.5">
        {rows.length === 0 && <Empty />}
        {rows.map((r) => (
          <Link
            key={r.key}
            to={`/artifacts?${filterKey}=${encodeURIComponent(r.key)}`}
            className="group grid grid-cols-[6.5rem_1fr_2rem] items-center gap-2 rounded-panel px-1 py-1 text-xs hover:bg-panelRaised"
          >
            <span className="truncate text-inkMuted group-hover:text-ink" title={r.label}>{r.label}</span>
            <span className="h-2 overflow-hidden rounded-full bg-panelRaised group-hover:bg-canvas">
              <span className="block h-full rounded-full bg-series1" style={{ width: `${(r.count / max) * 100}%` }} />
            </span>
            <span className="text-right font-mono text-ink">{r.count}</span>
          </Link>
        ))}
      </CardContent>
    </Card>
  )
}
