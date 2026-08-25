import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const TYPES = [
  { key: 'all', label: '전체' },
  { key: 'daily', label: '일일뉴스' },
  { key: 'weekly', label: '주간뉴스' },
  { key: 'monthly', label: '월간뉴스' },
]
const TYPE_KO = { daily: '일간', weekly: '주간', monthly: '월간' }

function ago(dateStr) {
  const d = new Date(dateStr + 'T06:00:00')
  const diff = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (diff <= 0) return '오늘'
  if (diff === 1) return '어제'
  if (diff < 30) return `${diff}일전`
  if (diff < 365) return `${Math.floor(diff / 30)}개월전`
  return `${Math.floor(diff / 365)}년전`
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
      <div className="hero">
        <div className="wrap">
          <div className="eyebrow">K-DEFENSE GLOBAL MARKET INTELLIGENCE</div>
          <h1 style={{ fontSize: 32 }}>방산MICE 글로벌 마켓 인텔리전스</h1>
          <p style={{ marginBottom: 22 }}>
            뉴스에서 수출기회까지. 일일 · 주간(월요일) · 월간(1일) 세 종의 뉴스레터를
            공개 조달공고와 보도를 확인해 직접 작성합니다.
          </p>
          <div className="chipbar">
            {TYPES.map((t) => (
              <button key={t.key} onClick={() => setType(t.key)}
                      className={'chip' + (type === t.key ? ' on' : '')}>
                {t.label} <span className="cnt">{counts[t.key] || 0}</span>
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

      <section style={{ paddingTop: 6 }}>
        <div className="wrap">
          {shown.length === 0 && (
            <p style={{ color: 'var(--muted)', textAlign: 'center' }}>검색 결과가 없습니다.</p>
          )}
          {Object.keys(byMonth).sort().reverse().map((m) => (
            <div key={m}>
              <div className="year-head">
                {m.slice(0, 4)}년 {Number(m.slice(5, 7))}월
                <span style={{ fontWeight: 400 }}>· {byMonth[m].length}개 호</span>
              </div>
              <div className="feed">
                {byMonth[m].map((it) => (
                  <Link className="issue" key={it.slug || it.date}
                        to={`/archive/${it.slug || it.date}`}>
                    <div className="no">
                      {TYPE_KO[it.type || 'weekly']} 제{it.no}호
                      {' · '}{Number(it.date.slice(5, 7))}/{Number(it.date.slice(8, 10))}
                      ({'일월화수목금토'[new Date(it.date + 'T00:00:00').getDay()]}) 발행
                      {it.covers ? ` · ${it.covers}` : ''}
                    </div>
                    <h3>{it.subject}</h3>
                    <p>{it.summary}</p>
                    <div className="meta">
                      수집 {it.counts?.collected}건 · 조달공고 {it.counts?.tender}건
                      {' · '}{ago(it.date)} · <b>by 방산MICE</b>
                    </div>
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
