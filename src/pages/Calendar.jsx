import { useEffect, useState } from 'react'

function dday(start) {
  const t = new Date()
  t.setHours(0, 0, 0, 0)
  const s = new Date(start + 'T00:00:00')
  return Math.round((s - t) / 86400000)
}

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
          <h1 style={{ fontSize: 32 }}>해외 방산전시회 캘린더</h1>
          <p style={{ marginBottom: 0 }}>
            국가관·공동관 신청은 통상 개최 <b>4~6개월 전에 마감</b>됩니다.
            D-180 시점부터 검토가 필요합니다. 일정은 주최측 공식 사이트로 확인했습니다.
          </p>
        </div>
      </div>

      <section>
        <div className="wrap">
          {upcoming.map((r) => {
            const d = r.verified ? dday(r.start) : null
            const cls = d === null ? 'd-tbd' : d <= 30 ? 'd-soon' : d <= 90 ? 'd-mid' : 'd-far'
            return (
              <div className={"exh" + (r.country === "대한민국" ? " exh-kr" : "")} key={r.name}>
                <div className={`dday ${cls}`}>
                  <b>{d === null ? '미정' : `D-${d}`}</b>
                  <span>{r.country}</span>
                </div>
                <div style={{ flex: 1 }}>
                  <h3>
                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                       style={{ color: 'var(--navy)', textDecoration: 'none' }}>
                      {r.name_ko}
                    </a>
                  </h3>
                  <div className="when">
                    {r.start}{r.end ? ` ~ ${r.end.slice(5)}` : ''} · {r.city} · {r.focus}
                  </div>
                  <div className="why" dangerouslySetInnerHTML={{ __html: r.why }} />
                  {r.note && <div className="note" dangerouslySetInnerHTML={{ __html: r.note }} />}
                  <div style={{ marginTop: 9, fontSize: 12 }}>
                    <a href={r.url} target="_blank" rel="noopener noreferrer">공식 사이트 ↗</a>
                  </div>
                </div>
              </div>
            )
          })}
          {upcoming.length === 0 && <p style={{ color: 'var(--muted)' }}>등록된 일정이 없습니다.</p>}
        </div>
      </section>
    </>
  )
}
