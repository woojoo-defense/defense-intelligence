import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Newsletter from '../components/Newsletter.jsx'

const TYPE_KO = { daily: '일일뉴스', weekly: '주간뉴스', monthly: '월간뉴스' }

export default function Issue() {
  const { date: slug } = useParams()
  const [issues, setIssues] = useState([])
  const [doc, setDoc] = useState(null)
  const [state, setState] = useState('loading')   // loading | ok | fallback

  useEffect(() => {
    fetch('/data/issues.json').then((r) => r.json()).then(setIssues).catch(() => {})
  }, [])

  useEffect(() => {
    setState('loading')
    setDoc(null)
    fetch(`/issues/${slug}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => { setDoc(d); setState('ok') })
      .catch(() => setState('fallback'))
  }, [slug])

  const key = (i) => i.slug || i.date
  const me = issues.find((i) => key(i) === slug) || null
  const sameType = issues.filter((i) => (i.type || 'weekly') === (me?.type || 'weekly'))
  const tIdx = sameType.findIndex((i) => key(i) === slug)
  const newer = tIdx > 0 ? sameType[tIdx - 1] : null
  const older = tIdx >= 0 && tIdx < sameType.length - 1 ? sameType[tIdx + 1] : null

  return (
    <section style={{ paddingTop: 24 }}>
      <div className="wrap" style={{ maxWidth: 900 }}>
        <div style={{ marginBottom: 14, fontSize: 13, display: 'flex',
                      justifyContent: 'space-between', alignItems: 'center', gap: 10,
                      flexWrap: 'wrap' }}>
          <Link to="/archive">← 아카이브</Link>
          <a href={`/issues/${slug}.html`} target="_blank" rel="noopener noreferrer"
             style={{ fontSize: 12.5 }}>
            메일 원본 보기 ↗
          </a>
        </div>

        {me && (
          <div style={{ marginBottom: 16 }}>
            <div className="kicker" style={{ marginBottom: 6 }}>
              {TYPE_KO[me.type] || '주간뉴스'} 제{me.no}호 · {me.date} 발행
              {me.covers ? ` · ${me.covers}` : ''}
            </div>
          </div>
        )}

        {state === 'loading' && (
          <div className="card" style={{ textAlign: 'center', color: 'var(--muted)' }}>
            불러오는 중…
          </div>
        )}

        {state === 'ok' && doc && <Newsletter doc={doc} />}

        {state === 'fallback' && (
          <div className="mailview">
            <div className="mailbar">
              <span>이 호는 웹 문서가 없어 발송본을 표시합니다.</span>
            </div>
            <iframe title={`${slug} 뉴스레터`} src={`/issues/${slug}_web.html`}
                    style={{ height: 2200 }} />
          </div>
        )}

        <div className="pager">
          <span>
            {older && (
              <Link to={`/archive/${older.slug || older.date}`}>
                ← 제{older.no}호 ({older.date})
              </Link>
            )}
          </span>
          <span>
            {newer && (
              <Link to={`/archive/${newer.slug || newer.date}`}>
                제{newer.no}호 ({newer.date}) →
              </Link>
            )}
          </span>
        </div>
      </div>
    </section>
  )
}
