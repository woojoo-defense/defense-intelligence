import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

export default function Issue() {
  const { date } = useParams()
  const [issues, setIssues] = useState([])
  const [h, setH] = useState(2400)

  useEffect(() => {
    fetch('/data/issues.json').then((r) => r.json()).then(setIssues).catch(() => {})
  }, [])

  const idx = issues.findIndex((i) => i.date === date)
  const me = idx >= 0 ? issues[idx] : null
  const newer = idx > 0 ? issues[idx - 1] : null
  const older = idx >= 0 && idx < issues.length - 1 ? issues[idx + 1] : null

  return (
    <section style={{ paddingTop: 28 }}>
      <div className="wrap">
        <div style={{ marginBottom: 14, fontSize: 13 }}>
          <Link to="/archive">← 아카이브</Link>
        </div>

        {me && (
          <>
            <div className="kicker">제{me.no}호 · {me.date} 발행 · 대상기간 {me.covers}</div>
            <h2 className="sec" style={{ marginBottom: 6 }}>{me.subject}</h2>
            <p className="sub">{me.summary}</p>
          </>
        )}

        <div className="mailview">
          <div className="mailbar">
            <span>실제 발송된 뉴스레터 원본입니다.
              {me && <> 수집 <b>{me.counts?.collected}건</b> 중 <b>{me.counts?.published}</b> 수록</>}
            </span>
            <a href={`/issues/${date}.html`} target="_blank" rel="noopener noreferrer">
              새 창에서 열기 ↗
            </a>
          </div>
          <iframe
            title={`${date} 뉴스레터`}
            src={`/issues/${date}.html`}
            style={{ height: h }}
            onLoad={(e) => {
              try {
                const d = e.target.contentDocument
                if (d) setH(Math.max(900, d.body.scrollHeight + 40))
              } catch (_) { /* 동일 출처가 아니면 기본 높이 유지 */ }
            }}
          />
        </div>

        <div className="pager">
          {older
            ? <Link to={`/archive/${older.date}`}>← 제{older.no}호 · {older.date}</Link>
            : <span />}
          {newer
            ? <Link to={`/archive/${newer.date}`}>제{newer.no}호 · {newer.date} →</Link>
            : <span />}
        </div>
      </div>
    </section>
  )
}
