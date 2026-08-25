import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

export default function Issue() {
  const { date: slug } = useParams()
  const [issues, setIssues] = useState([])
  const [h, setH] = useState(1800)

  const frame = useRef(null)

  useEffect(() => {
    fetch('/data/issues.json').then((r) => r.json()).then(setIssues).catch(() => {})
  }, [])

  // 웹버전은 탭을 바꾸면 내용 높이가 달라진다. 같은 출처이므로 주기적으로 맞춘다.
  useEffect(() => {
    const fit = () => {
      try {
        const d = frame.current?.contentDocument
        if (d?.body) {
          const next = Math.max(700, d.documentElement.scrollHeight + 24)
          setH((prev) => (Math.abs(prev - next) > 8 ? next : prev))
        }
      } catch (_) { /* 접근 불가 시 현재 높이 유지 */ }
    }
    const id = setInterval(fit, 400)
    return () => clearInterval(id)
  }, [slug])

  const key = (i) => i.slug || i.date
  const idx = issues.findIndex((i) => key(i) === slug)
  const me = idx >= 0 ? issues[idx] : null
  // 이전/다음은 같은 종(일간/주간/월간) 안에서만 이동한다
  const sameType = issues.filter((i) => (i.type || 'weekly') === (me?.type || 'weekly'))
  const tIdx = sameType.findIndex((i) => key(i) === slug)
  const newer = tIdx > 0 ? sameType[tIdx - 1] : null
  const older = tIdx >= 0 && tIdx < sameType.length - 1 ? sameType[tIdx + 1] : null
  const TYPE_KO = { daily: '일일뉴스', weekly: '주간뉴스', monthly: '월간뉴스' }

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
            <span>
              발송된 뉴스레터 본문입니다. 상단 탭으로 섹션을 전환할 수 있습니다.
              {me && <> 수집 <b>{me.counts?.collected}건</b> 중 <b>{me.counts?.published}</b> 수록</>}
            </span>
            <span style={{ display: 'flex', gap: 12 }}>
              <a href={`/issues/${slug}_web.html`} target="_blank" rel="noopener noreferrer">
                새 창에서 열기 ↗
              </a>
              <a href={`/issues/${slug}.html`} target="_blank" rel="noopener noreferrer">
                메일 원본(전체 펼침) ↗
              </a>
            </span>
          </div>
          <iframe
            ref={frame}
            title={`${slug} 뉴스레터`}
            src={`/issues/${slug}_web.html`}
            style={{ height: h }}
          />
        </div>

        <div className="pager">
          {older
            ? <Link to={`/archive/${older.slug || older.date}`}>← 제{older.no}호 · {older.date}</Link>
            : <span />}
          {newer
            ? <Link to={`/archive/${newer.slug || newer.date}`}>제{newer.no}호 · {newer.date} →</Link>
            : <span />}
        </div>
      </div>
    </section>
  )
}
