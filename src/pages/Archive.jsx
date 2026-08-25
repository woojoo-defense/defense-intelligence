import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const TYPES = [
  { key: 'all', label: '전체' },
  { key: 'daily', label: '일일뉴스' },
  { key: 'weekly', label: '주간뉴스' },
  { key: 'monthly', label: '월간뉴스' },
]
const TYPE_META = {
  daily: { badge: '일간', color: 'var(--sky)', bg: '#e8f3fe' },
  weekly: { badge: '주간', color: 'var(--orange)', bg: '#ffede3' },
  monthly: { badge: '월간', color: '#7c3aed', bg: '#f1eafe' },
}

export default function Archive() {
  const [issues, setIssues] = useState([])
  const [q, setQ] = useState('')
  const [type, setType] = useState('all')

  useEffect(() => {
    fetch('/data/issues.json').then((r) => r.json()).then(setIssues).catch(() => {})
  }, [])

  const kw = q.trim().toLowerCase()
  const shown = issues.filter((i) => {
    if (type !== 'all' && (i.type || 'weekly') !== type) return false
    if (!kw) return true
    return (i.subject + ' ' + (i.summary || '') + ' ' + (i.tags || []).join(' '))
      .toLowerCase().includes(kw)
  })

  const byMonth = {}
  shown.forEach((i) => {
    const m = i.date.slice(0, 7)
    ;(byMonth[m] = byMonth[m] || []).push(i)
  })

  const counts = { all: issues.length }
  issues.forEach((i) => {
    const t = i.type || 'weekly'
    counts[t] = (counts[t] || 0) + 1
  })

  return (
    <>
      <div className="hero" style={{ padding: '48px 0 38px' }}>
        <div className="wrap">
          <div className="eyebrow">ARCHIVE</div>
          <h1 style={{ fontSize: 32 }}>뉴스레터 아카이브</h1>
          <p style={{ marginBottom: 16 }}>
            일일(매일)·주간(매주 월요일)·월간(매월 1일) 세 종의 뉴스레터를 발행합니다.
            모든 호는 실제 해당 기간에 공고·보도된 내용으로 작성했습니다.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
            {TYPES.map((t) => (
              <button key={t.key} onClick={() => setType(t.key)}
                style={{
                  padding: '9px 18px', borderRadius: 5, cursor: 'pointer',
                  fontFamily: 'var(--font)', fontSize: 13.5, fontWeight: 800,
                  border: '1px solid rgba(157,184,255,.4)',
                  background: type === t.key ? 'var(--orange)' : 'rgba(10,18,44,.6)',
                  color: type === t.key ? '#fff' : '#cdd9ff',
                }}>
                {t.label} <span style={{ opacity: 0.75, fontWeight: 600 }}>
                  {counts[t.key] || 0}</span>
              </button>
            ))}
          </div>
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
                {byMonth[m].map((it) => {
                  const meta = TYPE_META[it.type || 'weekly']
                  return (
                    <Link className="issue" key={it.slug || it.date}
                          to={`/archive/${it.slug || it.date}`}>
                      <div className="no">
                        <span style={{
                          background: meta.bg, color: meta.color, borderRadius: 3,
                          padding: '2px 7px', marginRight: 7, fontSize: 10.5,
                        }}>{meta.badge}</span>
                        제{it.no}호 · {it.date} 발행
                      </div>
                      <h3>{it.subject}</h3>
                      <p>{it.summary}</p>
                      <div className="meta">
                        수집 <b>{it.counts?.collected}건</b> · 조달공고 <b>{it.counts?.tender}건</b>
                        {it.covers ? <> · {it.covers}</> : null}
                      </div>
                      {(it.tags || []).length > 0 && (
                        <div style={{ marginTop: 9, display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                          {it.tags.map((t) => <span className="tag" key={t}>{t}</span>)}
                        </div>
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
