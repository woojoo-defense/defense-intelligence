import { useEffect, useMemo, useState } from 'react'

function dday(start) {
  const t = new Date()
  t.setHours(0, 0, 0, 0)
  const s = new Date(start + 'T00:00:00')
  return Math.round((s - t) / 86400000)
}

const ymd = (d) => {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/* ---------------- 월 그리드 캘린더 (PC·모바일 동일 구조) ---------------- */
function MonthGrid({ rows }) {
  const now = new Date()
  const [ym, setYm] = useState([now.getFullYear(), now.getMonth()]) // [year, 0-based month]
  const [year, month] = ym

  const move = (d) => {
    const nd = new Date(year, month + d, 1)
    setYm([nd.getFullYear(), nd.getMonth()])
  }

  const cells = useMemo(() => {
    const first = new Date(year, month, 1)
    const start = new Date(first)
    start.setDate(1 - first.getDay())                 // 일요일 시작
    const out = []
    for (let i = 0; i < 42; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      out.push(d)
    }
    // 마지막 줄이 전부 다음 달이면 잘라낸다
    return out[35].getMonth() === month ? out : out.slice(0, 35)
  }, [year, month])

  const todayStr = ymd(new Date())

  const eventsOf = (dateStr) =>
    rows.filter((r) => {
      const end = r.end || r.start
      return r.start <= dateStr && dateStr <= end
    })

  return (
    <div className="cal-wrap">
      <div className="cal-nav">
        <button onClick={() => move(-1)} aria-label="이전 달">‹</button>
        <h3>{year}년 {month + 1}월</h3>
        <button onClick={() => move(1)} aria-label="다음 달">›</button>
      </div>
      <div className="cal-grid">
        {['일', '월', '화', '수', '목', '금', '토'].map((w, i) => (
          <div className={'cal-dow' + (i === 0 ? ' sun' : '')} key={w}>{w}</div>
        ))}
        {cells.map((d) => {
          const ds = ymd(d)
          const evs = eventsOf(ds)
          const out = d.getMonth() !== month
          return (
            <div key={ds}
                 className={'cal-cell' + (out ? ' out' : '') + (ds === todayStr ? ' today' : '')}>
              <div className={'cal-date' + (d.getDay() === 0 ? ' sun' : '')}>{d.getDate()}</div>
              {!out && evs.map((e) => (
                <a key={e.name} href={e.url} target="_blank" rel="noopener noreferrer"
                   className={'cal-ev' + (e.country === '대한민국' ? ' kr' : '')
                              + (e.start === ds ? ' start' : '')}
                   title={`${e.name_ko || e.name} (${e.start}~${(e.end || '').slice(5)})`}>
                  {e.name}
                </a>
              ))}
            </div>
          )
        })}
      </div>
      <div style={{ marginTop: 10, fontSize: 11.5, color: 'var(--muted)',
                    display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        <span><span style={{ display: 'inline-block', width: 10, height: 10,
              background: 'var(--bluebg)', border: '1px solid var(--link)',
              borderRadius: 2, verticalAlign: -1, marginRight: 5 }} />해외 전시회</span>
        <span><span style={{ display: 'inline-block', width: 10, height: 10,
              background: '#ffede3', border: '1px solid var(--orange)',
              borderRadius: 2, verticalAlign: -1, marginRight: 5 }} />국내 전시회</span>
        <span>막대를 누르면 공식 사이트로 이동합니다</span>
      </div>
    </div>
  )
}

/* ---------------- 페이지 ---------------- */
export default function Calendar() {
  const [rows, setRows] = useState([])

  useEffect(() => {
    fetch('/data/exhibitions.json').then((r) => r.json())
      .then((d) => setRows(d.exhibitions || [])).catch(() => {})
  }, [])

  const today = new Date().toISOString().slice(0, 10)
  const upcoming = rows
    .filter((r) => (r.end || r.start) >= today)
    .sort((a, b) => a.start.localeCompare(b.start))

  return (
    <>
      <div className="hero" style={{ padding: '48px 0 38px' }}>
        <div className="wrap">
          <div className="eyebrow">CALENDAR</div>
          <h1 style={{ fontSize: 32 }}>방산전시회 캘린더</h1>
          <p style={{ marginBottom: 0 }}>
            국가관·공동관 신청은 통상 개최 <b>4~6개월 전에 마감</b>됩니다.
            D-180 시점부터 검토가 필요합니다. 일정은 주최측 공식 사이트로 확인했습니다.
          </p>
        </div>
      </div>

      <section style={{ paddingTop: 34 }}>
        <div className="wrap">
          <MonthGrid rows={rows} />

          <div className="kicker">Upcoming</div>
          <h2 className="sec" style={{ fontSize: 24, marginBottom: 18 }}>다가오는 전시회</h2>
          {upcoming.map((r) => {
            const d = r.verified ? dday(r.start) : null
            const cls = d === null ? 'd-tbd' : d <= 30 ? 'd-soon' : d <= 90 ? 'd-mid' : 'd-far'
            return (
              <div className={'exh' + (r.country === '대한민국' ? ' exh-kr' : '')} key={r.name}>
                <div className={`dday ${cls}`}>
                  <b>{d === null ? '미정' : d < 0 ? '진행 중' : `D-${d}`}</b>
                  <span>{r.country}</span>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <h3>
                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                       style={{ color: 'var(--heading)', textDecoration: 'none' }}>
                      {r.name_ko || r.name}
                    </a>
                  </h3>
                  <div className="when">
                    {r.start}{r.end ? ` ~ ${r.end.slice(5)}` : ''} · {r.city} · {r.focus}
                  </div>
                  <div className="why" dangerouslySetInnerHTML={{ __html: r.why || '' }} />
                  {r.note && (
                    <div className="note" dangerouslySetInnerHTML={{ __html: r.note }} />
                  )}
                  <div style={{ marginTop: 8, fontSize: 12 }}>
                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                       className="nl-golink">공식 사이트 ›</a>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </>
  )
}
