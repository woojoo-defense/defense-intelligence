import { Routes, Route, Link, NavLink, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Home from './pages/Home.jsx'
import HowItWorks from './pages/HowItWorks.jsx'
import Archive from './pages/Archive.jsx'
import Issue from './pages/Issue.jsx'
import Calendar from './pages/Calendar.jsx'

const NAV = [
  { to: '/', label: '소개', end: true },
  { to: '/how-it-works', label: '작동 방식' },
  { to: '/archive', label: '아카이브' },
  { to: '/calendar', label: '전시회 캘린더' },
]

function ScrollTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

export default function App() {
  return (
    <>
      <ScrollTop />
      <header className="topbar">
        <div className="topbar-in">
          <Link className="brand" to="/">
            <span>K-DEFENSE GLOBAL MARKET INTELLIGENCE</span>
            <b>방산MICE 글로벌 마켓 인텔리전스</b>
          </Link>
          <nav className="nav">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) => (isActive ? 'on' : undefined)}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/archive" element={<Archive />} />
          <Route path="/archive/:date" element={<Issue />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>

      <footer>
        <div className="wrap fgrid">
          <div>
            <b>방산MICE 글로벌 마켓 인텔리전스</b>
            디펜스엑스포 · 한국방위산업MICE협회<br />
            뉴스에서 수출기회까지
          </div>
          <div>
            <b>수록 원칙</b>
            공개된 조달공고·정부 발표·기업 보도자료를 확인해 자체 작성합니다.<br />
            모든 항목에 원문 링크를 제공하며 기사 본문을 복제하지 않습니다.
          </div>
          <div>
            <b>바로가기</b>
            <Link to="/archive">주간호 아카이브</Link> · <Link to="/calendar">전시회 캘린더</Link><br />
            <Link to="/how-it-works">작동 방식</Link>
          </div>
        </div>
      </footer>
    </>
  )
}
