import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function Archive() {
  const [issues, setIssues] = useState([])
  const [q, setQ] = useState('')

  useEffect(() => {
    fetch('/data/issues.json').then((r) => r.json()).then(setIssues).catch(() => {})
  }, [])

  const kw = q.trim().toLowerCase()
  const shown = kw
    ? issues.filter((i) =>
        (i.subject + ' ' + (i.summary || '') + ' ' + (i.tags || []).join(' '))
          .toLowerCase().includes(kw))
    : issues

  const byMonth = {}
  shown.forEach((i) => {
    const m = i.date.slice(0, 7)
    ;(byMonth[m] = byMonth[m] || []).push(i)
  })

  return (
    <>
      <div className="hero" style={{ padding: '48px 0 38px' }}>
        <div className="wrap">
          <div className="eyebrow">ARCHIVE</div>
          <h1 style={{ fontSize: 32 }}>주간호 아카이브</h1>
          <p style={{ marginBottom: 14 }}>
            2026년 1월 5일 창간 이후 매주 월요일 아침 발송한 {issues.length}개 호입니다.
            각 호는 실제 그 주에 공고·보도된 내용으로 작성했습니다.
          </p>
          <input
            className="search"
            placeholder="키워드로 찾기 — 예: 캐나다 잠수함, 폴란드, K9, NATO"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </div>

      <section>
        <div className="wrap">
          {shown.length === 0 && (
            <p style={{ color: 'var(--muted)' }}>검색 결과가 없습니다.</p>
          )}
          {Object.keys(byMonth).sort().reverse().map((m) => (
            <div key={m}>
              <div className="year-head">
                {m.slice(0, 4)}년 {Number(m.slice(5, 7))}월
                <span style={{ fontWeight: 400, marginLeft: 8 }}>({byMonth[m].length}개 호)</span>
              </div>
              <div className="grid g2">
                {byMonth[m].map((it) => (
                  <Link className="issue" key={it.date} to={`/archive/${it.date}`}>
                    <div className="no">제{it.no}호 · {it.date} 발행</div>
                    <h3>{it.subject}</h3>
                    <p>{it.summary}</p>
                    <div className="meta">
                      대상기간 {it.covers} · 수집 <b>{it.counts?.collected}건</b> ·
                      조달공고 <b>{it.counts?.tender}건</b>
                    </div>
                    {it.tags?.length > 0 && (
                      <div style={{ marginTop: 9, display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                        {it.tags.map((t) => <span className="tag" key={t}>{t}</span>)}
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
