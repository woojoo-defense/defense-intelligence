import { useState } from 'react'

/* 뉴스레터 본문 네이티브 렌더러 — /issues/{slug}.json 문서를 React로 그린다.
   밝은 배경, 모바일에서 표는 카드로 전환(styles.css의 .nl-* 클래스). */

const GRADE_CLASS = { A: 'nl-g-a', B: 'nl-g-b', C: 'nl-g-c', D: 'nl-g-d' }

function Html({ text, className, tag: Tag = 'div' }) {
  // 편집자가 작성한 <b>/<br> 강조만 포함된 신뢰 소스(자체 생성 JSON)다.
  return <Tag className={className} dangerouslySetInnerHTML={{ __html: text || '' }} />
}

function Ext({ url, children, className }) {
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className={className}>
      {children}
    </a>
  )
}

/* Windows는 국기 이모지를 글자(US, KR…)로 표시하므로 Twemoji SVG 이미지로 그린다 */
function flagSrc(emoji) {
  const cps = [...emoji].map((c) => c.codePointAt(0).toString(16)).join('-')
  return `https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/svg/${cps}.svg`
}

function FlagImg({ emoji, size = 15 }) {
  return (
    <img src={flagSrc(emoji)} alt="" width={size} height={size}
         style={{ verticalAlign: -2, marginRight: 5, borderRadius: 2 }}
         loading="lazy" />
  )
}

/* 문자열 맨 앞의 국기 이모지(RI 페어)를 이미지로 바꿔 렌더 */
const RI_RE = /^([\u{1F1E6}-\u{1F1FF}]{2})\s*/u

function WithFlag({ text, className }) {
  if (!text) return null
  const m = text.match(RI_RE)
  if (!m) return <div className={className}>{text}</div>
  return (
    <div className={className}>
      <FlagImg emoji={m[1]} size={14} />
      {text.slice(m[0].length)}
    </div>
  )
}

function Feature({ it }) {
  return (
    <article className="nl-feature">
      <h3 className="nl-feature-title"><Ext url={it.url}>{it.title}</Ext></h3>
      {(it.facts || []).length > 0 && (
        <dl className="nl-facts">
          {it.facts.map(([k, v], i) => (
            <div key={i}><dt>{k}</dt><Html tag="dd" text={v} /></div>
          ))}
        </dl>
      )}
      {it.why && (
        <div className="nl-why">
          <div className="nl-why-label">한국 기업에 주는 의미</div>
          <Html text={it.why} />
        </div>
      )}
      {(it.targets || []).length > 0 && (
        <div className="nl-list nl-list-green">
          <div className="nl-list-label">유망 국내 기업·품목</div>
          <ul>{it.targets.map((v, i) => <Html tag="li" key={i} text={v} />)}</ul>
        </div>
      )}
      {(it.action || []).length > 0 && (
        <div className="nl-list nl-list-red">
          <div className="nl-list-label">지금 해야 할 일</div>
          <ul>{it.action.map((v, i) => <Html tag="li" key={i} text={v} />)}</ul>
        </div>
      )}
      <div className="nl-src">
        출처: {it.source} · <Ext url={it.url}>원문 확인 ›</Ext>
      </div>
    </article>
  )
}

function TenderTable({ items }) {
  return (
    <div className="nl-tenders">
      {/* 데스크톱: 표 */}
      <table className="nl-table">
        <thead>
          <tr><th>국가</th><th>사업 / 품목</th><th>단계</th><th>마감</th><th>원문</th></tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i}>
              <td className="nl-country">{it.country}</td>
              <td>
                <Ext url={it.url} className="nl-tender-title">{it.title}</Ext>
                {it.note && <Html className="nl-note" text={it.note} />}
              </td>
              <td className="nl-stage">{it.stage}</td>
              <td className={it.urgent ? 'nl-dl nl-urgent' : 'nl-dl'}>{it.deadline || '–'}</td>
              <td><Ext url={it.url} className="nl-golink">공고 ›</Ext></td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* 모바일: 카드 */}
      <div className="nl-tender-cards">
        {items.map((it, i) => (
          <div className="nl-tender-card" key={i}>
            <div className="nl-tc-head">
              <span className="nl-country">{it.country}</span>
              <span className={it.urgent ? 'nl-dl nl-urgent' : 'nl-dl'}>
                {it.deadline ? `마감 ${it.deadline}` : it.stage}
              </span>
            </div>
            <Ext url={it.url} className="nl-tender-title">{it.title}</Ext>
            {it.note && <Html className="nl-note" text={it.note} />}
            <div className="nl-tc-foot">
              <span className="nl-stage">{it.stage}</span>
              <Ext url={it.url} className="nl-golink">공고 원문 ›</Ext>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Briefs({ items }) {
  return (
    <div className="nl-briefs">
      {items.map((it, i) => (
        <div className="nl-brief" key={i}>
          <Ext url={it.url} className="nl-brief-title">{it.title}</Ext>
          {it.title_orig && <WithFlag className="nl-orig" text={it.title_orig} />}
          {it.note && <Html className="nl-brief-note" text={it.note} />}
          <div className="nl-brief-src">{it.source} · <Ext url={it.url}>원문 ›</Ext></div>
        </div>
      ))}
    </div>
  )
}

function Scrap({ items }) {
  return (
    <div className="nl-briefs">
      {items.map((it, i) => (
        <div className="nl-brief" key={i}>
          <div className="nl-scrap-row">
            <div className="nl-scrap-main">
              <Ext url={it.url} className="nl-brief-title">{it.title}</Ext>
              {it.title_orig && <WithFlag className="nl-orig" text={it.title_orig} />}
              {it.note && <Html className="nl-brief-note" text={it.note} />}
              <div className="nl-brief-src">
                {it.outlet}{it.date ? ` · ${it.date}` : ''}
                {(it.others || []).length > 0 && (
                  <span className="nl-others">
                    {' '}· 같은 사안:{' '}
                    {it.others.slice(0, 3).map((o, j) => (
                      <span key={j}>{j > 0 && ' · '}<Ext url={o.url}>{o.outlet || '관련기사'}</Ext></span>
                    ))}
                  </span>
                )}
              </div>
            </div>
            <Ext url={it.url} className="nl-golink nl-scrap-go">원문 ›</Ext>
          </div>
        </div>
      ))}
    </div>
  )
}

const FLAG = {
  대한민국: '🇰🇷', 미국: '🇺🇸', 프랑스: '🇫🇷', 폴란드: '🇵🇱', 필리핀: '🇵🇭',
  인도네시아: '🇮🇩', 이집트: '🇪🇬', UAE: '🇦🇪', 인도: '🇮🇳', 영국: '🇬🇧',
  사우디아라비아: '🇸🇦', 사우디: '🇸🇦', 싱가포르: '🇸🇬', 말레이시아: '🇲🇾',
  독일: '🇩🇪', 일본: '🇯🇵', 튀르키예: '🇹🇷', 캐나다: '🇨🇦', 호주: '🇦🇺',
}

function CalendarList({ items }) {
  const tone = (it) => {
    if (it.dday == null) return 'd-tbd'
    if (it.dday <= 30) return 'd-soon'
    if (it.dday <= 90) return 'd-mid'
    return 'd-far'
  }
  return (
    <div>
      {items.map((it, i) => (
        <div className={'exh' + (it.country === '대한민국' ? ' exh-kr' : '')} key={i}>
          <div className={`dday ${tone(it)}`}>
            <b>{it.dday == null ? '미정' : it.dday < 0 ? '진행 중' : `D-${it.dday}`}</b>
            <span>{it.country}</span>
            {FLAG[it.country] && (
              <span style={{ display: 'block', marginTop: 3 }}>
                <img src={flagSrc(FLAG[it.country])} alt="" width={20} height={20}
                     style={{ borderRadius: 2, marginRight: 0 }} loading="lazy" />
              </span>
            )}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h3><Ext url={it.url}>{it.name_ko || it.name}</Ext></h3>
            <div className="when">
              {it.start}{it.end ? ` ~ ${it.end.slice(5)}` : ''} · {it.city} · {it.focus}
            </div>
            <Html className="why" text={it.why} />
            {it.note && <Html className="note" text={it.note} />}
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <Ext url={it.url} className="nl-golink">공식 사이트 ›</Ext>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

/* 주간·월간 결산용 지표 그리드 — items: [{label, value, delta, note}] */
function Stats({ items }) {
  return (
    <div className="nl-stats">
      {items.map((it, i) => (
        <div className="nl-stat" key={i}>
          <div className="nl-stat-label">{it.label}</div>
          <div className="nl-stat-value">{it.value}</div>
          {it.delta && (
            <div className={'nl-stat-delta' + (String(it.delta).startsWith('-') ? ' down' : '')}>
              {it.delta}
            </div>
          )}
          {it.note && <div className="nl-stat-note">{it.note}</div>}
        </div>
      ))}
    </div>
  )
}

/* 월간 결산용 타임라인 — items: [{date, title, note, url, source}] */
function Timeline({ items }) {
  return (
    <div className="nl-timeline">
      {items.map((it, i) => (
        <div className="nl-tl-row" key={i}>
          <div className="nl-tl-date">{it.date}</div>
          <div className="nl-tl-body">
            <Ext url={it.url} className="nl-brief-title">{it.title}</Ext>
            {it.note && <Html className="nl-brief-note" text={it.note} />}
            {it.source && <WithFlag className="nl-brief-src" text={it.source} />}
          </div>
        </div>
      ))}
    </div>
  )
}

function Section({ sec, hideHead }) {
  const items = sec.items || []
  if (items.length === 0) return null
  return (
    <div className="nl-section">
      {!hideHead && (
        <div className="nl-sec-head">
          <h2>{sec.title}</h2>
          {sec.subtitle && <p>{sec.subtitle}</p>}
        </div>
      )}
      {hideHead && sec.subtitle && <p className="nl-subdesc">{sec.subtitle}</p>}
      {sec.kind === 'feature' && items.map((it, i) => <Feature it={it} key={i} />)}
      {sec.kind === 'table' && <TenderTable items={items} />}
      {sec.kind === 'brief' && <Briefs items={items} />}
      {sec.kind === 'scrap' && <Scrap items={items} />}
      {sec.kind === 'calendar' && <CalendarList items={items} />}
      {sec.kind === 'stats' && <Stats items={items} />}
      {sec.kind === 'timeline' && <Timeline items={items} />}
    </div>
  )
}

const SUBTAB_IDS = ['global', 'scrap', 'tenders']

export default function Newsletter({ doc }) {
  const tabs = (doc.tabs || []).filter(
    (t) => t.sections?.some((s) => (s.items || []).length > 0),
  )
  const [tabId, setTabId] = useState(tabs[0]?.id)
  const [subIdx, setSubIdx] = useState(0)
  const active = tabs.find((t) => t.id === tabId) || tabs[0]
  const count = (t) => t.sections.reduce((a, s) => a + (s.items || []).length, 0)

  const activeSecs = (active?.sections || []).filter((s) => (s.items || []).length > 0)
  const useSub = SUBTAB_IDS.includes(active?.id) && activeSecs.length > 1
  const curSub = Math.min(subIdx, activeSecs.length - 1)

  const d = new Date(doc.date + 'T00:00:00')
  const dateStr = `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 (${'일월화수목금토'[d.getDay()]})`
  // 메일 제목의 "[방산MICE 데일리] 8/25 — " 접두어는 웹 커버에서 뗀다
  const coverTitle = (doc.subject || '')
    .replace(/^\[[^\]]*\]\s*/, '')
    .replace(/^[0-9]{1,2}\/[0-9]{1,2}\s*—\s*/, '')
    || '방산MICE 글로벌 마켓 인텔리전스'

  return (
    <div className="nl">
      {/* 커버 (브런치 아티클형) */}
      <div className="nl-cover">
        <div className="nl-cover-eyebrow">K-DEFENSE GLOBAL MARKET INTELLIGENCE</div>
        <h1 className="nl-cover-title">{coverTitle}</h1>
        <div className="nl-cover-sub">{doc.cadence || ''} 제{doc.issue}호</div>
        <div className="nl-cover-meta">
          <span><i>by</i> 방산MICE 글로벌 마켓 인텔리전스</span>
          <span>·</span>
          <span>{dateStr}</span>
        </div>
      </div>

      {/* 리드 */}
      {doc.lead && (
        <div className="nl-lead">
          <div className="nl-lead-label">{doc.lead_title || '오늘의 핵심'}</div>
          <Html text={doc.lead} />
        </div>
      )}

      {/* 탭 */}
      <div className="nl-tabs" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id} role="tab" aria-selected={t.id === active?.id}
            className={'nl-tab' + (t.id === active?.id ? ' on' : '')}
            onClick={() => { setTabId(t.id); setSubIdx(0) }}
          >
            {t.label} <span className="nl-cnt">{count(t)}</span>
          </button>
        ))}
      </div>
      {active?.desc && <p className="nl-tab-desc">{active.desc}</p>}

      {useSub && (
        <div className="nl-subtabs">
          {activeSecs.map((sec, i) => (
            <button key={i} className={'nl-subtab' + (i === curSub ? ' on' : '')}
                    onClick={() => setSubIdx(i)}>
              {sec.title} <span className="nl-cnt">{(sec.items || []).length}</span>
            </button>
          ))}
        </div>
      )}

      {useSub
        ? <Section sec={activeSecs[curSub]} hideHead key={active.id + curSub} />
        : active?.sections.map((sec, i) => <Section sec={sec} key={i} />)}

      {/* 꼬리 */}
      <div className="nl-foot">
        {doc.stats && (
          <div className="nl-foot-stats">
            {Object.entries(doc.stats).map(([k, v]) => <span key={k}>{k} <b>{v}</b></span>)}
          </div>
        )}
        <p>
          신뢰등급 — A 해외 정부·군·조달기관 공식자료 · B 기업 공식발표·KOTRA·무관 확인 ·
          C 복수 전문매체 · D 단일 매체. 본 뉴스는 공개 자료를 확인해 자체 작성했으며 모든 항목에
          원문 링크를 제공합니다. 계약 조건·자격요건은 반드시 원문 공고로 확인하십시오.
        </p>
      </div>
    </div>
  )
}
