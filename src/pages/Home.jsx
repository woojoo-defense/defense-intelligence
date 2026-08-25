import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  const [sources, setSources] = useState(null)
  const [issues, setIssues] = useState([])

  useEffect(() => {
    fetch('/data/sources.json').then((r) => r.json()).then(setSources).catch(() => {})
    fetch('/data/issues.json').then((r) => r.json()).then(setIssues).catch(() => {})
  }, [])

  const latest = issues[0]
  const srcCount = sources
    ? Object.values(sources).reduce((a, g) => a + g.items.length, 0)
    : 31

  return (
    <>
      {/* ------------------------------------------------ 히어로: 짧은 헤드라인 */}
      <div className="hero" style={{ textAlign: 'center' }}>
        <div className="wrap">
          <div className="eyebrow">K-DEFENSE GLOBAL MARKET INTELLIGENCE</div>
          <h1>
            뉴스에서, <em>수출기회</em>까지
          </h1>
          <div className="hero-date">
            매일 · 매주 월요일 · 매월 1일 발행 <b>|</b> 방산MICE 글로벌 마켓 인텔리전스
          </div>
          <p style={{ margin: '0 auto 30px' }}>
            전 세계 조달포털·정부 발표·전문매체의 신호를
            국내 방산기업의 <b style={{ color: '#fff' }}>사업기회</b>로 바꿔 전달합니다.
          </p>
          <div>
            {latest && (
              <Link className="btn btn-primary" to={`/archive/${latest.slug || latest.date}`}>
                최신호 읽기 ▸
              </Link>
            )}
            <Link className="btn btn-ghost" to="/archive">아카이브</Link>
          </div>

          <div className="stats">
            <div><b>{issues.length || 35}+</b><span>ISSUE</span><small>일간·주간·월간 3종 발행</small></div>
            <div><b>{srcCount}</b><span>SOURCE</span><small>상시 수집 정보원</small></div>
            <div><b>32</b><span>COUNTRY</span><small>조달공고 원문 수집국</small></div>
            <div><b>300+</b><span>WEEKLY</span><small>주간 수집 후 30건으로 압축</small></div>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------ 퀵메뉴 (K-DEX 스트립) */}
      <div className="quickbar">
        <div className="quickbar-in">
          <Link to={latest ? `/archive/${latest.slug || latest.date}` : '/archive'}>
            <span className="qi">◎</span> 최신호 보기
          </Link>
          <Link to="/archive"><span className="qi">▤</span> 아카이브</Link>
          <Link to="/how-it-works"><span className="qi">⚙</span> 작동 방식</Link>
          <Link to="/calendar"><span className="qi">▦</span> 전시회 캘린더</Link>
        </div>
      </div>

      {/* ------------------------------------------------ 문제 정의 (히어로에서 내려온 카피) */}
      <section>
        <div className="wrap narrow">
          <div className="kicker">Why Intelligence</div>
          <h2 className="sec">
            해외 조달공고는 이미 공개돼 있습니다.<br />
            문제는 아무도 한국 기업 관점으로 읽어주지 않는다는 것입니다.
          </h2>
          <p className="lead" style={{ color: 'var(--ink)', marginTop: 18 }}>
            매주 전 세계에서 수백 건을 수집해, 국내 기업이 실제로 대응할 수 있는 건만 골라
            <b> “왜 중요한가 → 누구에게 기회인가 → 이번 주에 무엇을 할 것인가”</b>로 바꿔 보내드립니다.
          </p>
          <p className="lead" style={{ color: 'var(--muted)' }}>
            핀란드가 기관총 사전시장조사를 시작했다는 사실 자체는 검색하면 나옵니다.
            그러나 <b>그 단계가 요구사양이 확정되기 전이라 우리 제품 규격을 반영시킬 수 있는
            사실상 마지막 시점</b>이라는 것, 스웨덴 조달청과 공동 진행이라 한 번의 대응으로
            두 시장에 들어간다는 것 — 그 해석이 이 서비스가 하는 일입니다.
          </p>

          <div className="cmp-scroll" style={{ marginTop: 34 }}>
          <table className="cmp">
            <thead>
              <tr><th style={{ width: '22%' }}></th><th style={{ width: '39%' }}>일반 방산뉴스</th>
                <th style={{ width: '39%' }}>방산MICE 마켓 인텔리전스</th></tr>
            </thead>
            <tbody>
              {[
                ['목적', '업계 동향 전달', '국내 기업의 해외사업 발굴'],
                ['주 내용', '계약·수출·정책 기사 요약', '조달계획·입찰·RFI·현지생산·공급망'],
                ['정보 출처', '국내외 언론기사 중심', '해외 정부·군·조달기관 원문 + 매체 교차확인'],
                ['기사 결론', '주요 내용 소개', '누가, 무엇을, 언제까지 해야 하는가'],
                ['후속 지원', '별도 지원 없음', 'KOTRA 무역관·전시회·상담회 연계'],
              ].map(([k, a, b]) => (
                <tr key={k}><td>{k}</td><td>{a}</td><td className="us">{b}</td></tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ 기사 구조 (다크 밴드) */}
      <section className="dark-band">
        <div className="wrap">
          <div className="kicker">Editorial Format</div>
          <h2 className="sec">모든 기사는 네 가지에 답합니다</h2>
          <p className="sub">읽을거리가 아니라 업무 지시서에 가깝게 씁니다.</p>
          <div className="grid g4">
            {[
              ['01', '왜 중요한가', '단순 사실이 아니라 이 움직임이 시장에서 무엇을 뜻하는지 씁니다. 사업단계가 사전시장조사인지 입찰공고인지에 따라 대응이 완전히 달라집니다.'],
              ['02', '누구에게 기회인가', '완제품·부품·정비·훈련체계 중 어느 기업군이 들어갈 수 있는지 품목 단위로 지목합니다.'],
              ['03', '지금 할 일', '공급업체 등록 여부 점검, 영문 자료 준비, 회신 마감 확인처럼 이번 주에 실행할 항목으로 적습니다.'],
              ['04', '누구와 연결하나', '해당 국가 KOTRA 무역관, 현지 파트너 후보, 참가할 전시회를 함께 제시합니다.'],
            ].map(([n, t, d]) => (
              <div key={n} style={{
                background: 'var(--dark-card)', border: '1px solid var(--dark-line)',
                borderRadius: 8, padding: 24,
              }}>
                <div style={{ color: 'var(--orange)', fontWeight: 800, fontSize: 13, letterSpacing: 2 }}>{n}</div>
                <h3 style={{ color: '#fff', margin: '8px 0' }}>{t}</h3>
                <p style={{ fontSize: 13.5, color: '#9fb0d8', margin: 0, lineHeight: 1.7 }}>{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ 소스 */}
      <section style={{ background: '#fff' }}>
        <div className="wrap">
          <div className="kicker">Sources</div>
          <h2 className="sec">{srcCount}곳에서 매일 모읍니다</h2>
          <p className="sub">
            기사만 모으지 않습니다. 발주기관·마감일·품목분류가 들어 있는 <b>조달공고 원문</b>이 핵심 계층입니다.
          </p>

          {sources && Object.entries(sources).map(([key, g]) => (
            <div className="tier" key={key}>
              <h4>{g.label} <span style={{ color: 'var(--muted)', fontWeight: 400, fontSize: 12 }}>
                · 신뢰등급 {g.grade}</span></h4>
              <p>{g.desc}</p>
              <div className="src">
                {g.items.map((s) => (
                  <a key={s.n} href={s.u} target="_blank" rel="noopener noreferrer"
                     style={{ textDecoration: 'none' }}>
                    <span>
                      <img src={`/logos/${s.f}`} alt="" width="16" height="16"
                           style={{ verticalAlign: '-3px', marginRight: 7, borderRadius: 3 }}
                           onError={(e) => { e.currentTarget.style.display = 'none' }} />
                      {s.n}{s.d ? <b style={{ fontWeight: 400 }}> · {s.d}</b> : null}
                    </span>
                  </a>
                ))}
              </div>
            </div>
          ))}

          <div className="card" style={{ marginTop: 10, borderLeft: '4px solid var(--orange)' }}>
            <h3 style={{ marginBottom: 6 }}>정보 신뢰등급을 함께 표기합니다</h3>
            <p style={{ margin: 0, fontSize: 13.5 }}>
              <b>A</b> 해외 정부·군·조달기관 공식자료 &nbsp;·&nbsp;
              <b>B</b> 기업 공식발표·KOTRA·무관 확인 &nbsp;·&nbsp;
              <b>C</b> 복수 전문매체 &nbsp;·&nbsp; <b>D</b> 단일 매체 &nbsp;·&nbsp; <b>E</b> 미확인(발행 금지)<br />
              <span style={{ color: 'var(--muted)' }}>
                수치가 매체마다 다르면 하나를 고르지 않고 “확정되지 않았다”고 적고 등급을 내립니다.
                한 번의 오보가 신뢰를 소멸시키기 때문입니다.
              </span>
            </p>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ 최근호 */}
      {issues.length > 0 && (
        <section>
          <div className="wrap">
            <div className="kicker">Latest Issues</div>
            <h2 className="sec">지난 호 살펴보기</h2>
            <p className="sub">일간·주간·월간 최신호입니다. 아카이브에서 종류별로 모아볼 수 있습니다.</p>
            <div className="grid g3">
              {issues.slice(0, 6).map((it) => (
                <Link className="issue" key={it.slug || it.date} to={`/archive/${it.slug || it.date}`}>
                  <div className="no">제{it.no}호 · {it.date}</div>
                  <h3>{it.subject}</h3>
                  <p>{it.summary}</p>
                  <div className="meta">
                    수집 <b>{it.counts?.collected}건</b> · 조달공고 <b>{it.counts?.tender}건</b>
                  </div>
                </Link>
              ))}
            </div>
            <div style={{ marginTop: 24 }}>
              <Link className="btn btn-primary" to="/archive">전체 아카이브 보기 ▸</Link>
            </div>
          </div>
        </section>
      )}

      {/* ------------------------------------------------ CTA (다크) */}
      <section className="dark-band" style={{ textAlign: 'center' }}>
        <div className="wrap narrow">
          <div className="kicker" style={{ textAlign: 'center' }}>Contact</div>
          <h2 className="sec" style={{ textAlign: 'center' }}>관심 국가와 품목을 알려주시면</h2>
          <p style={{ color: '#9fb0d8', fontSize: 16.5, lineHeight: 1.8 }}>
            해당 분야 공고를 우선 발송하고, 사업 발굴 시 KOTRA 무역관 연결과
            전시회·상담회 참가까지 이어드립니다.
          </p>
          <div style={{ marginTop: 20 }}>
            <a className="btn btn-primary" href="mailto:defensemice@example.org?subject=%5B%EB%B0%A9%EC%82%B0MICE%5D%20%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0%20%EA%B5%AC%EB%8F%85%20%EB%B0%8F%20%EA%B4%80%EC%8B%AC%EB%B6%84%EC%95%BC%20%EB%93%B1%EB%A1%9D">
              구독·관심분야 등록 ▸
            </a>
          </div>
        </div>
      </section>
    </>
  )
}
