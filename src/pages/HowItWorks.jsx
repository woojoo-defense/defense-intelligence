import { useEffect, useState } from 'react'

const STAGES = [
  {
    key: 'collect',
    no: '01',
    title: '수집',
    tone: 'blue',
    desc: '조달포털 API·RSS·타깃 검색을 동시에 호출합니다. 하루 약 40초.',
    nodes: [
      { n: 'TED (EU 27개국)', f: 'ted.png', t: 'API', d: '국방 CPV 공고' },
      { n: 'SAM.gov', f: 'sam.png', t: 'API', d: '사전수요조사·사전공고' },
      { n: 'CanadaBuys', f: 'canadabuys.png', t: 'CSV', d: '공개 입찰 전체' },
      { n: 'Find a Tender', f: 'findtender.ico', t: 'OCDS', d: '영국 고액 공고' },
      { n: 'U.S. DoD', f: 'dod.png', t: 'RSS', d: '일일 계약공고' },
      { n: '전문매체 21종', f: 'defensenews.png', t: 'RSS', d: '이슈 탐지' },
      { n: 'Google News', f: 'googlenews.png', t: '쿼리 30', d: 'OEM·국가·품목' },
      { n: 'OpenAlex', f: 'openalex.png', t: 'API', d: '학술논문' },
      { n: '오피니언 9종', f: 'wotr.png', t: 'RSS', d: '싱크탱크 논평' },
    ],
  },
  {
    key: 'clean',
    no: '02',
    title: '정제',
    tone: 'amber',
    desc: '같은 사안을 다룬 기사를 하나로 묶고 잡음을 걷어냅니다.',
    nodes: [
      { n: '기간 필터', t: '규칙', d: '최근 3일 이내만' },
      { n: '중복 제거', t: '규칙', d: '제목 정규화 + 30일 발행이력 대조' },
      { n: '유사기사 군집', t: '알고리즘', d: '대표기사 1건 + 타 매체 링크' },
      { n: '블록리스트', t: '규칙', d: '기계번역 사이트·주가/사건사고 제외' },
      { n: '품목코드 판정', t: '규칙', d: 'CPV·FSC로 비국방 건 제외' },
    ],
  },
  {
    key: 'score',
    no: '03',
    title: '자동 채점',
    tone: 'green',
    desc: '“한국 기업이 쓸 수 있는 정보인가”를 기준으로 100점 만점 채점해 정렬합니다.',
    nodes: [
      { n: '사업단계', t: '+25', d: 'RFI·입찰·낙찰 여부' },
      { n: '공급망 신호', t: '+20', d: '협력사·오프셋·현지생산·MRO' },
      { n: '한국 연관', t: '+20', d: 'K9·K2·천무·FA-50·국내 기업' },
      { n: '중점국가', t: '+15', d: '32개국 낱말 단위 매칭' },
      { n: '품목 적합도', t: '+15', d: '탄약·장갑차·함정·광학·C-UAS' },
      { n: '공식 출처', t: '+10', d: '정부·조달기관 자료 가산' },
      { n: '순수 전황 기사', t: '−25', d: '사업기회와 무관한 건 감점' },
    ],
  },
  {
    key: 'verify',
    no: '04',
    title: '사람 검증',
    tone: 'red',
    desc: '자동 요약을 그대로 내보내지 않습니다. 이 단계가 서비스의 본체입니다.',
    nodes: [
      { n: '원문 대조', t: '필수', d: '날짜·금액·기관·마감일' },
      { n: '신뢰등급 부여', t: 'A~E', d: 'E등급은 외부 발행 금지' },
      { n: '수출통제 검토', t: '필수', d: '민감 품목 별도 심사' },
      { n: '한국어 재작성', t: '편집', d: '왜 중요 → 누구에게 → 지금 할 일' },
      { n: '링크 검증', t: '자동', d: '전 항목 접속 확인 후 발행' },
    ],
  },
  {
    key: 'publish',
    no: '05',
    title: '발행',
    tone: 'navy',
    desc: '같은 편집본에서 메일과 웹을 함께 만들어 냅니다.',
    nodes: [
      { n: '주간 뉴스레터', t: 'HTML', d: '메일 클라이언트 호환' },
      { n: '웹 아카이브', t: '사이트', d: '이 페이지' },
      { n: '전시회 캘린더', t: 'D-day', d: '지난 일정 자동 제외' },
      { n: '긴급 알림', t: '수시', d: '마감 임박 공고' },
    ],
  },
]

const FUNNEL = [
  ['수집 원시', '1,289건'],
  ['기간 필터 후', '1,095건'],
  ['중복 제거·군집', '786건'],
  ['사람이 검증', '상위 80건'],
  ['실제 발행', '65건'],
]

export default function HowItWorks() {
  const [open, setOpen] = useState(null)
  useEffect(() => { setOpen(null) }, [])

  return (
    <>
      <div className="hero" style={{ padding: '54px 0 44px' }}>
        <div className="wrap">
          <div className="eyebrow">HOW IT WORKS</div>
          <h1 style={{ fontSize: 34 }}>수백 곳의 신호를, 한 통의 메일로</h1>
          <p style={{ marginBottom: 0 }}>
            수집부터 발행까지 5단계 파이프라인입니다. 자동화는 앞의 3단계까지이고,
            <b> 네 번째 단계는 사람이 합니다.</b> 자동 요약을 그대로 내보내는 순간
            이 서비스의 존재 이유가 사라지기 때문입니다.
          </p>
        </div>
      </div>

      <section>
        <div className="wrap">
          <div className="flow">
            {STAGES.map((s, i) => (
              <div className="flow-col" key={s.key}>
                <div className={`stage stage-${s.tone}`}>
                  <div className="stage-head">
                    <span className="stage-no">{s.no}</span>
                    <b>{s.title}</b>
                  </div>
                  <p className="stage-desc">{s.desc}</p>
                  <div className="nodes">
                    {s.nodes.map((n) => (
                      <div className="node" key={n.n}
                           onMouseEnter={() => setOpen(n.n)} onMouseLeave={() => setOpen(null)}>
                        <div className="node-ico">
                          {n.f
                            ? <img src={`/logos/${n.f}`} alt="" width="18" height="18"
                                   onError={(e) => { e.currentTarget.style.visibility = 'hidden' }} />
                            : <span className="dot" />}
                        </div>
                        <div className="node-body">
                          <div className="node-name">{n.n}</div>
                          <div className="node-desc">{n.d}</div>
                        </div>
                        <div className="node-tag">{n.t}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {i < STAGES.length - 1 && <div className="flow-arrow" aria-hidden="true">→</div>}
              </div>
            ))}
          </div>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 14 }}>
            화면이 좁으면 좌우로 밀어서 볼 수 있습니다.
          </p>
        </div>
      </section>

      <section style={{ background: '#fff', borderTop: '1px solid var(--line)' }}>
        <div className="wrap">
          <div className="kicker">실제 하루치 수치</div>
          <h2 className="sec">1,289건이 65건이 되기까지</h2>
          <p className="sub">
            2026년 8월 24일 수집 기준입니다. 걸러내는 일이 모으는 일보다 중요합니다.
          </p>
          <div className="funnel">
            {FUNNEL.map(([k, v], i) => (
              <div className="fstep" key={k} style={{ width: `${100 - i * 13}%` }}>
                <span>{k}</span><b>{v}</b>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <div className="wrap narrow">
          <div className="kicker">지키는 원칙</div>
          <h2 className="sec">무엇을 하지 않는가</h2>
          <div className="grid g2">
            {[
              ['기사 본문을 복제하지 않습니다',
               '제목·공개 요약·URL·발행일·출처만 저장합니다. 유료·로그인 콘텐츠는 수집하지 않고, 전문매체는 이슈 탐지용으로만 씁니다. 발행 기사는 원출처를 확인한 뒤 자체 문장으로 씁니다.'],
              ['자동 번역문을 그대로 싣지 않습니다',
               'AI가 번역·요약했더라도 저작권과 오역 책임은 사라지지 않습니다. 초안은 기계가 만들되 발행문은 사람이 다시 씁니다.'],
              ['미확인 정보를 발행하지 않습니다',
               '신뢰등급 E는 외부 발행 금지입니다. 매체마다 수치가 다르면 하나를 고르지 않고 “확정되지 않았다”고 적습니다.'],
              ['링크가 살아있는지 확인하고 보냅니다',
               '발행 전 모든 URL을 원자료와 대조하거나 실제 접속해 확인합니다. 한 건이라도 실패하면 발행을 멈춥니다.'],
            ].map(([t, d]) => (
              <div className="card" key={t}>
                <h3>{t}</h3>
                <p style={{ fontSize: 13.5, color: 'var(--muted)', margin: 0 }}>{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
