import { ComplianceShowcase } from '../components/landing/ComplianceShowcase'
import { FieldVerification } from '../components/landing/FieldVerification'
import { Footer } from '../components/landing/Footer'
import { Hero } from '../components/landing/Hero'
import { HowItWorks } from '../components/landing/HowItWorks'
import { Intro } from '../components/landing/Intro'
import { Navbar } from '../components/landing/Navbar'
import { RuleEngine } from '../components/landing/RuleEngine'
import { ScanCta } from '../components/landing/ScanCta'
import type { User } from '../types/auth'

interface LandingPageProps {
  user: User | null
  onScan: () => void
  onLogout: () => void
}

export function LandingPage({ user, onScan, onLogout }: LandingPageProps) {
  function jump(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="landing">
      <Navbar user={user} onScan={onScan} onJump={jump} onLogout={onLogout} />
      <Hero onScan={onScan} onExplore={() => jump('how')} />
      <Intro />
      <HowItWorks />
      <ComplianceShowcase />
      <FieldVerification />
      <RuleEngine />
      <ScanCta onScan={onScan} />
      <Footer onScan={onScan} onJump={jump} />
    </div>
  )
}
