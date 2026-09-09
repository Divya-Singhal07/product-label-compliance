import { useEffect, useMemo, useState } from 'react'
import { getPastRecords } from '../services/api'
import type { InspectionRecord } from '../services/api'
import type { User } from '../types/auth'

interface AdminDashboardPageProps {
  user: User | null
  onOpenScan: () => void
  onLogout: () => void
}

type NavSection =
  | 'overview'
  | 'inspections'
  | 'officers'
  | 'violations'
  | 'analytics'
  | 'audit'

function getScore(record: InspectionRecord) {
  return Number(record.confidence_score || 0)
}

function isToday(value: string) {
  const d = new Date(value)
  const now = new Date()

  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  )
}

function categoryFor(record: InspectionRecord) {
  const fields = (record.extracted_fields || {}) as Record<
    string,
    unknown
  >

  if (fields.is_imported === true) {
    return 'Imported Goods'
  }

  const value = String(
    fields.product_type ||
      fields.specific_product ||
      'Other',
  ).toLowerCase()

  if (value.includes('food')) return 'Food'
  if (value.includes('cosmetic')) return 'Cosmetics'
  if (value.includes('electronic')) return 'Electronics'
  if (
    value.includes('beverage') ||
    value.includes('drink')
  ) {
    return 'Beverages'
  }

  return 'Other'
}

function violationLabel(item: unknown) {
  if (!item || typeof item !== 'object') {
    return 'Unknown violation'
  }

  const value = item as Record<string, unknown>

  const raw = String(
    value.rule_name ||
      value.rule_id ||
      value.name ||
      value.message ||
      'Unknown violation',
  )

  const known: Record<string, string> = {
    PRESENCE_MRP: 'MRP declaration missing',
    PRESENCE_NET_QUANTITY: 'Net quantity missing',
    PRESENCE_MANUFACTURER: 'Manufacturer details missing',
    PRESENCE_CONSUMER_CARE: 'Consumer care details missing',
    CARE_001: 'Consumer care details missing',
    PRESENCE_COUNTRY_OF_ORIGIN:
      'Country of origin missing',
    COUNTRY_OF_ORIGIN:
      'Country of origin missing',
    PRESENCE_PACKER: 'Packer details missing',
    PRESENCE_IMPORTER: 'Importer details missing',
    PRESENCE_GENERIC_NAME: 'Generic name missing',
    MFG_DATE: 'Manufacturing date issue',
    BEST_BEFORE: 'Best-before declaration issue',
  }

  return (
    known[raw] ||
    raw
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
  )
}

function riskFor(score: number) {
  if (score < 50) {
    return {
      label: 'Critical',
      className: 'critical',
    }
  }

  if (score < 70) {
    return {
      label: 'High',
      className: 'high',
    }
  }

  if (score < 85) {
    return {
      label: 'Medium',
      className: 'medium',
    }
  }

  return {
    label: 'Low',
    className: 'low',
  }
}

function officerKey(record: InspectionRecord) {
  return (
    record.officer_id ||
    record.officer_email ||
    record.officer_name ||
    'UNKNOWN'
  )
}

function scrollToSection(section: NavSection) {
  document
    .getElementById(`admin-${section}`)
    ?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
}

export function AdminDashboardPage({
  user,
  onOpenScan,
  onLogout,
}: AdminDashboardPageProps) {
  const [records, setRecords] = useState<InspectionRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] =
    useState<NavSection>('overview')
  const [selectedOfficer, setSelectedOfficer] =
    useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [lastRefresh, setLastRefresh] =
    useState<Date | null>(null)

  async function refreshRecords() {
    setLoading(true)

    try {
      const data = await getPastRecords()
      setRecords(data)
      setLastRefresh(new Date())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshRecords()
  }, [])

  useEffect(() => {
    const sections: NavSection[] = [
      'overview',
      'inspections',
      'officers',
      'violations',
      'analytics',
      'audit',
    ]

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort(
            (a, b) =>
              b.intersectionRatio -
              a.intersectionRatio,
          )[0]

        if (visible) {
          const id = visible.target.id
          const section = sections.find(
            (item) => `admin-${item}` === id,
          )

          if (section) {
            setActiveSection(section)
          }
        }
      },
      {
        rootMargin: '-18% 0px -65% 0px',
        threshold: [0.05, 0.2, 0.5],
      },
    )

    sections.forEach((section) => {
      const element = document.getElementById(
        `admin-${section}`,
      )

      if (element) observer.observe(element)
    })

    return () => observer.disconnect()
  }, [])

  const analytics = useMemo(() => {
    const total = records.length

    const compliant = records.filter(
      (record) => record.is_compliant,
    ).length

    const nonCompliant = total - compliant

    const averageScore =
      total > 0
        ? records.reduce(
            (sum, record) => sum + getScore(record),
            0,
          ) / total
        : 0

    const complianceRate =
      total > 0 ? (compliant / total) * 100 : 0

    const manualReviews = records.filter(
      (record) => record.needs_manual_review,
    ).length

    const inspectionsToday = records.filter((record) =>
      isToday(record.created_at),
    ).length

    const officerMap = new Map<
      string,
      {
        id: string
        name: string
        department: string
        email: string
        inspections: number
        compliant: number
        totalScore: number
        latest: number
      }
    >()

    records.forEach((record) => {
      const key = officerKey(record)

      const existing = officerMap.get(key)
      const createdAt =
        new Date(record.created_at).getTime()

      if (existing) {
        existing.inspections += 1
        existing.compliant += record.is_compliant
          ? 1
          : 0
        existing.totalScore += getScore(record)
        existing.latest = Math.max(
          existing.latest,
          createdAt,
        )
      } else {
        officerMap.set(key, {
          id: key,
          name:
            record.officer_name ||
            record.officer_id ||
            'Unknown Officer',
          department:
            record.department || 'Not specified',
          email:
            record.officer_email || 'Not specified',
          inspections: 1,
          compliant: record.is_compliant ? 1 : 0,
          totalScore: getScore(record),
          latest: createdAt,
        })
      }
    })

    const officers = [...officerMap.values()]
      .map((officer) => ({
        ...officer,
        complianceRate:
          officer.inspections > 0
            ? (officer.compliant /
                officer.inspections) *
              100
            : 0,
        averageScore:
          officer.inspections > 0
            ? officer.totalScore /
              officer.inspections
            : 0,
        active:
          Date.now() - officer.latest <
          30 * 24 * 60 * 60 * 1000,
      }))
      .sort((a, b) => b.inspections - a.inspections)

    const categories = new Map<
      string,
      {
        total: number
        compliant: number
      }
    >()

    records.forEach((record) => {
      const category = categoryFor(record)
      const existing =
        categories.get(category) || {
          total: 0,
          compliant: 0,
        }

      existing.total += 1

      if (record.is_compliant) {
        existing.compliant += 1
      }

      categories.set(category, existing)
    })

    const categoryData = [...categories.entries()]
      .map(([name, data]) => ({
        name,
        total: data.total,
        compliant: data.compliant,
        complianceRate:
          data.total > 0
            ? (data.compliant / data.total) *
              100
            : 0,
      }))
      .sort((a, b) => b.total - a.total)

    const violationMap = new Map<string, number>()

    records.forEach((record) => {
      ;(record.violations || []).forEach(
        (item) => {
          const name = violationLabel(item)

          violationMap.set(
            name,
            (violationMap.get(name) || 0) + 1,
          )
        },
      )
    })

    const violations = [
      ...violationMap.entries(),
    ]
      .map(([name, count]) => ({
        name,
        count,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)

    const days = Array.from(
      { length: 7 },
      (_, index) => {
        const date = new Date()
        date.setHours(0, 0, 0, 0)
        date.setDate(
          date.getDate() - (6 - index),
        )

        const dayRecords = records.filter(
          (record) => {
            const recordDate = new Date(
              record.created_at,
            )
            recordDate.setHours(
              0,
              0,
              0,
              0,
            )

            return (
              recordDate.getTime() ===
              date.getTime()
            )
          },
        )

        const scoreAverage =
          dayRecords.length > 0
            ? dayRecords.reduce(
                (sum, record) =>
                  sum + getScore(record),
                0,
              ) / dayRecords.length
            : 0

        return {
          label:
            date.toLocaleDateString(
              undefined,
              {
                weekday: 'short',
              },
            ),
          compliant:
            dayRecords.filter(
              (record) => record.is_compliant,
            ).length,
          nonCompliant:
            dayRecords.filter(
              (record) => !record.is_compliant,
            ).length,
          averageScore: scoreAverage,
        }
      },
    )

    const highRisk = [...records]
      .sort(
        (a, b) =>
          getScore(a) - getScore(b),
      )
      .slice(0, 8)

    const recent = [...records]
      .sort(
        (a, b) =>
          new Date(
            b.created_at,
          ).getTime() -
          new Date(
            a.created_at,
          ).getTime(),
      )
      .slice(0, 10)

    const riskCounts = {
      critical: records.filter(
        (record) => getScore(record) < 50,
      ).length,
      high: records.filter((record) => {
        const value = getScore(record)
        return value >= 50 && value < 70
      }).length,
      medium: records.filter((record) => {
        const value = getScore(record)
        return value >= 70 && value < 85
      }).length,
      low: records.filter(
        (record) => getScore(record) >= 85,
      ).length,
    }

    return {
      total,
      compliant,
      nonCompliant,
      averageScore,
      complianceRate,
      manualReviews,
      inspectionsToday,
      officers,
      categoryData,
      violations,
      days,
      highRisk,
      recent,
      riskCounts,
      activeOfficers: officers.filter(
        (officer) => officer.active,
      ).length,
      averagePerOfficer:
        officers.length > 0
          ? total / officers.length
          : 0,
    }
  }, [records])

  const filteredRecords = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) return records

    return records.filter((record) => {
      return [
        record.product_id,
        record.officer_id,
        record.officer_name,
        record.officer_email,
        record.department,
        record.summary,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value)
            .toLowerCase()
            .includes(query),
        )
    })
  }, [records, search])

  const maxDaily = Math.max(
    ...analytics.days.map(
      (day) =>
        day.compliant +
        day.nonCompliant,
    ),
    1,
  )

  const maxViolation = Math.max(
    ...analytics.violations.map(
      (item) => item.count,
    ),
    1,
  )

  const maxCategory = Math.max(
    ...analytics.categoryData.map(
      (item) => item.total,
    ),
    1,
  )

  const donutAngle =
    analytics.complianceRate * 3.6

  const selectedOfficerData =
    analytics.officers.find(
      (officer) =>
        officer.id === selectedOfficer,
    )

  const sectionItems: {
    id: NavSection
    label: string
    number: string
  }[] = [
    {
      id: 'overview',
      label: 'Overview',
      number: '01',
    },
    {
      id: 'inspections',
      label: 'Inspections',
      number: '02',
    },
    {
      id: 'officers',
      label: 'Officers',
      number: '03',
    },
    {
      id: 'violations',
      label: 'Violations',
      number: '04',
    },
    {
      id: 'analytics',
      label: 'Analytics',
      number: '05',
    },
    {
      id: 'audit',
      label: 'Audit Log',
      number: '06',
    },
  ]

  return (
    <div className="admin-command">
      <style>{`
        .admin-command {
          min-height: 100vh;
          background: #f2eee6;
          color: #181715;
        }

        .admin-command *,
        .admin-command *::before,
        .admin-command *::after {
          box-sizing: border-box;
        }

        .admin-command-shell {
          display: flex;
          min-height: 100vh;
        }

        .admin-command-sidebar {
          position: sticky;
          top: 0;
          height: 100vh;
          width: 238px;
          flex: 0 0 238px;
          border-right: 1px solid rgba(24,23,21,.11);
          background: #e9e3d9;
          display: flex;
          flex-direction: column;
          padding: 26px 17px;
          z-index: 30;
        }

        .admin-command-logo {
          padding: 2px 11px 27px;
          border-bottom: 1px solid rgba(24,23,21,.10);
        }

        .admin-command-logo strong {
          display: block;
          font-size: 21px;
          font-weight: 900;
          letter-spacing: .09em;
        }

        .admin-command-logo span {
          display: block;
          margin-top: 8px;
          font-size: 9px;
          font-weight: 800;
          letter-spacing: .15em;
          text-transform: uppercase;
          color: rgba(24,23,21,.48);
        }

        .admin-command-nav {
          margin-top: 24px;
          display: grid;
          gap: 5px;
        }

        .admin-command-nav button {
          width: 100%;
          display: grid;
          grid-template-columns: 28px 1fr;
          align-items: center;
          gap: 7px;
          padding: 11px 10px;
          border: 0;
          border-radius: 8px;
          background: transparent;
          color: rgba(24,23,21,.54);
          font: inherit;
          font-size: 11px;
          text-align: left;
          cursor: pointer;
        }

        .admin-command-nav button:hover {
          background: rgba(255,255,255,.4);
          color: #181715;
        }

        .admin-command-nav button.active {
          background: #181715;
          color: #fff;
        }

        .admin-command-nav-number {
          font-size: 9px;
          opacity: .5;
          letter-spacing: .08em;
        }

        .admin-command-sidebar-bottom {
          margin-top: auto;
          padding: 17px 10px 0;
          border-top: 1px solid rgba(24,23,21,.10);
        }

        .admin-command-sidebar-user {
          font-size: 12px;
          font-weight: 800;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .admin-command-sidebar-role {
          margin-top: 5px;
          color: rgba(24,23,21,.48);
          font-size: 9px;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: .1em;
        }

        .admin-command-main {
          min-width: 0;
          flex: 1;
        }

        .admin-command-topbar {
          position: sticky;
          top: 0;
          z-index: 25;
          min-height: 76px;
          padding: 0 190px 0 30px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 18px;
          border-bottom: 1px solid rgba(24,23,21,.10);
          background: rgba(248,246,240,.94);
          backdrop-filter: blur(14px);
        }

        .admin-command-topbar-left {
          min-width: 0;
        }

        .admin-command-topbar-label {
          font-size: 9px;
          font-weight: 850;
          letter-spacing: .15em;
          text-transform: uppercase;
          color: rgba(24,23,21,.48);
        }

        .admin-command-topbar-title {
          margin-top: 4px;
          font-size: 14px;
          font-weight: 800;
        }

        .admin-command-topbar-actions {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }

        .admin-command-button {
          padding: 10px 13px;
          border-radius: 8px;
          border: 1px solid rgba(24,23,21,.14);
          background: #fff;
          color: #181715;
          font: inherit;
          font-size: 10px;
          font-weight: 800;
          cursor: pointer;
        }

        .admin-command-button:hover {
          background: #f4f0e8;
        }

        .admin-command-button.dark {
          background: #181715;
          color: #fff;
          border-color: #181715;
        }

        .admin-command-page {
          width: min(1500px, calc(100% - 54px));
          margin: 0 auto;
          padding: 36px 0 70px;
        }

        .admin-command-section {
          scroll-margin-top: 100px;
          margin-bottom: 14px;
        }

        .admin-command-hero {
          display: flex;
          align-items: end;
          justify-content: space-between;
          gap: 25px;
          margin-bottom: 27px;
        }

        .admin-command-kicker {
          margin: 0 0 8px;
          font-size: 9px;
          font-weight: 900;
          letter-spacing: .17em;
          text-transform: uppercase;
          color: rgba(24,23,21,.46);
        }

        .admin-command-hero h1 {
          margin: 0;
          font-size: clamp(38px, 5vw, 62px);
          line-height: .9;
          letter-spacing: -.06em;
        }

        .admin-command-hero p {
          max-width: 700px;
          margin: 14px 0 0;
          color: rgba(24,23,21,.58);
          font-size: 13px;
          line-height: 1.55;
        }

        .admin-command-updated {
          color: rgba(24,23,21,.45);
          font-size: 10px;
          white-space: nowrap;
        }

        .admin-command-kpis {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 12px;
        }

        .admin-command-kpi {
          min-height: 150px;
          padding: 20px;
          border: 1px solid rgba(24,23,21,.10);
          border-radius: 14px;
          background: #faf8f3;
          position: relative;
          overflow: hidden;
        }

        .admin-command-kpi::after {
          content: "";
          position: absolute;
          right: -30px;
          bottom: -47px;
          width: 100px;
          height: 100px;
          border-radius: 50%;
          background: rgba(24,23,21,.045);
        }

        .admin-command-kpi-label {
          font-size: 9px;
          font-weight: 900;
          letter-spacing: .12em;
          text-transform: uppercase;
          color: rgba(24,23,21,.47);
        }

        .admin-command-kpi-value {
          display: block;
          margin-top: 17px;
          font-size: 39px;
          line-height: 1;
          letter-spacing: -.055em;
        }

        .admin-command-kpi-note {
          display: block;
          margin-top: 10px;
          color: rgba(24,23,21,.48);
          font-size: 10px;
        }

        .admin-command-ops {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          margin-bottom: 12px;
        }

        .admin-command-op {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 20px;
          padding: 17px 20px;
          border: 1px solid rgba(24,23,21,.10);
          border-radius: 12px;
          background: #faf8f3;
        }

        .admin-command-op span {
          font-size: 9px;
          font-weight: 900;
          letter-spacing: .10em;
          text-transform: uppercase;
          color: rgba(24,23,21,.47);
        }

        .admin-command-op strong {
          font-size: 23px;
          letter-spacing: -.04em;
        }

        .admin-command-grid {
          display: grid;
          grid-template-columns: 1.4fr .9fr;
          gap: 12px;
          margin-bottom: 12px;
        }

        .admin-command-grid-equal {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 12px;
        }

        .admin-command-card {
          border: 1px solid rgba(24,23,21,.10);
          border-radius: 14px;
          background: #faf8f3;
          padding: 20px;
          overflow: hidden;
        }

        .admin-command-card-heading {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 15px;
          margin-bottom: 17px;
        }

        .admin-command-card-heading h2 {
          margin: 0;
          font-size: 18px;
          letter-spacing: -.035em;
        }

        .admin-command-card-heading p {
          margin: 5px 0 0;
          color: rgba(24,23,21,.46);
          font-size: 10px;
        }

        .admin-command-legend {
          display: flex;
          gap: 13px;
          color: rgba(24,23,21,.53);
          font-size: 9px;
          white-space: nowrap;
        }

        .admin-command-legend-item {
          display: flex;
          align-items: center;
          gap: 5px;
        }

        .admin-command-legend-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #1f2722;
        }

        .admin-command-legend-dot.soft {
          background: #aaa193;
        }

        .admin-command-chart-scroll {
          width: 100%;
          overflow-x: auto;
        }

        .admin-command-donut-layout {
          min-height: 245px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 25px;
        }

        .admin-command-donut {
          width: 170px;
          height: 170px;
          flex: 0 0 170px;
          border-radius: 50%;
          display: grid;
          place-items: center;
          position: relative;
          background:
            conic-gradient(
              #26382d 0deg ${donutAngle}deg,
              #bdb5a8 ${donutAngle}deg 360deg
            );
        }

        .admin-command-donut::before {
          content: "";
          position: absolute;
          width: 108px;
          height: 108px;
          border-radius: 50%;
          background: #faf8f3;
        }

        .admin-command-donut-center {
          position: relative;
          z-index: 1;
          text-align: center;
        }

        .admin-command-donut-center strong {
          display: block;
          font-size: 27px;
          letter-spacing: -.05em;
        }

        .admin-command-donut-center span {
          display: block;
          margin-top: 3px;
          color: rgba(24,23,21,.45);
          font-size: 9px;
          text-transform: uppercase;
          letter-spacing: .08em;
        }

        .admin-command-mini-stats {
          min-width: 150px;
        }

        .admin-command-mini-stat {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          padding: 10px 0;
          border-bottom: 1px solid rgba(24,23,21,.07);
          font-size: 11px;
        }

        .admin-command-mini-stat:last-child {
          border-bottom: none;
        }

        .admin-command-mini-stat strong {
          font-size: 15px;
        }

        .admin-command-category {
          display: grid;
          grid-template-columns: 125px 1fr 48px 55px;
          align-items: center;
          gap: 9px;
          margin-bottom: 14px;
          font-size: 10px;
        }

        .admin-command-category:last-child {
          margin-bottom: 0;
        }

        .admin-command-category-name {
          font-weight: 850;
        }

        .admin-command-bar {
          height: 9px;
          border-radius: 999px;
          background: #e1dbd1;
          overflow: hidden;
        }

        .admin-command-bar span {
          display: block;
          height: 100%;
          border-radius: inherit;
          background: #27372d;
        }

        .admin-command-category-count {
          text-align: right;
          color: rgba(24,23,21,.45);
        }

        .admin-command-category-rate {
          text-align: right;
          font-weight: 900;
        }

        .admin-command-violation {
          display: grid;
          grid-template-columns: 23px 1fr 38px;
          align-items: center;
          gap: 9px;
          margin-bottom: 14px;
          font-size: 10px;
        }

        .admin-command-violation-number {
          color: rgba(24,23,21,.35);
          font-size: 9px;
        }

        .admin-command-violation-name {
          font-weight: 750;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
        }

        .admin-command-violation-count {
          text-align: right;
          font-weight: 900;
        }

        .admin-command-risk-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
        }

        .admin-command-risk-box {
          padding: 15px;
          border-radius: 11px;
          background: #f1ece4;
          border: 1px solid rgba(24,23,21,.08);
        }

        .admin-command-risk-box span {
          display: block;
          color: rgba(24,23,21,.45);
          font-size: 8px;
          font-weight: 900;
          letter-spacing: .10em;
          text-transform: uppercase;
        }

        .admin-command-risk-box strong {
          display: block;
          margin-top: 8px;
          font-size: 25px;
          letter-spacing: -.04em;
        }

        .admin-command-search-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 15px;
          margin-bottom: 15px;
        }

        .admin-command-search {
          width: min(410px, 100%);
          padding: 11px 13px;
          border: 1px solid rgba(24,23,21,.13);
          border-radius: 8px;
          background: #fff;
          color: #181715;
          font: inherit;
          font-size: 11px;
          outline: none;
        }

        .admin-command-search:focus {
          border-color: rgba(24,23,21,.35);
        }

        .admin-command-table-wrap {
          overflow-x: auto;
        }

        .admin-command-table {
          min-width: 850px;
          width: 100%;
          border-collapse: collapse;
        }

        .admin-command-table th {
          padding: 10px;
          border-bottom: 1px solid rgba(24,23,21,.10);
          text-align: left;
          color: rgba(24,23,21,.43);
          font-size: 8px;
          font-weight: 900;
          letter-spacing: .10em;
          text-transform: uppercase;
        }

        .admin-command-table td {
          padding: 13px 10px;
          border-bottom: 1px solid rgba(24,23,21,.065);
          font-size: 10px;
          vertical-align: middle;
        }

        .admin-command-table tr:last-child td {
          border-bottom: none;
        }

        .admin-command-name {
          font-weight: 850;
        }

        .admin-command-sub {
          display: block;
          margin-top: 4px;
          color: rgba(24,23,21,.42);
          font-size: 9px;
        }

        .admin-command-progress {
          display: inline-block;
          width: 90px;
          height: 7px;
          margin-right: 7px;
          overflow: hidden;
          vertical-align: middle;
          border-radius: 999px;
          background: #dfd9cf;
        }

        .admin-command-progress span {
          display: block;
          height: 100%;
          border-radius: inherit;
          background: #27372d;
        }

        .admin-command-status {
          display: inline-flex;
          padding: 5px 8px;
          border-radius: 999px;
          background: #e9e3da;
          font-size: 8px;
          font-weight: 900;
          letter-spacing: .06em;
          text-transform: uppercase;
        }

        .admin-command-status.active {
          background: #27372d;
          color: #fff;
        }

        .admin-command-view {
          padding: 7px 9px;
          border: 1px solid rgba(24,23,21,.13);
          border-radius: 7px;
          background: #fff;
          color: #181715;
          font: inherit;
          font-size: 9px;
          font-weight: 800;
          cursor: pointer;
        }

        .admin-command-highrisk {
          display: grid;
          gap: 0;
        }

        .admin-command-highrisk-row {
          display: grid;
          grid-template-columns: 1.25fr .8fr 65px 80px;
          gap: 10px;
          align-items: center;
          padding: 11px 0;
          border-bottom: 1px solid rgba(24,23,21,.07);
          font-size: 10px;
        }

        .admin-command-highrisk-row:last-child {
          border-bottom: none;
        }

        .admin-command-risk-pill {
          display: inline-flex;
          justify-content: center;
          width: fit-content;
          padding: 5px 8px;
          border-radius: 999px;
          font-size: 8px;
          font-weight: 900;
          letter-spacing: .06em;
          text-transform: uppercase;
        }

        .admin-command-risk-pill.critical {
          background: #a5463b;
          color: white;
        }

        .admin-command-risk-pill.high {
          background: #d5c0ae;
        }

        .admin-command-risk-pill.medium {
          background: #e3ddd3;
        }

        .admin-command-risk-pill.low {
          background: #ece7df;
          color: rgba(24,23,21,.5);
        }

        .admin-command-audit {
          display: grid;
        }

        .admin-command-audit-row {
          display: grid;
          grid-template-columns: 88px 18px 1fr;
          gap: 10px;
          min-height: 69px;
        }

        .admin-command-audit-time {
          padding-top: 2px;
          text-align: right;
          color: rgba(24,23,21,.40);
          font-size: 9px;
        }

        .admin-command-audit-dot {
          position: relative;
          display: flex;
          justify-content: center;
        }

        .admin-command-audit-dot::after {
          content: "";
          position: absolute;
          top: 10px;
          bottom: -4px;
          width: 1px;
          background: rgba(24,23,21,.09);
        }

        .admin-command-audit-dot span {
          position: relative;
          z-index: 2;
          width: 8px;
          height: 8px;
          margin-top: 3px;
          border-radius: 50%;
          background: #27372d;
        }

        .admin-command-audit-copy strong {
          display: block;
          font-size: 10px;
        }

        .admin-command-audit-copy p {
          margin: 4px 0 0;
          color: rgba(24,23,21,.43);
          font-size: 9px;
        }

        .admin-command-empty {
          padding: 35px 10px;
          text-align: center;
          color: rgba(24,23,21,.43);
          font-size: 11px;
        }

        .admin-command-modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 100;
          display: grid;
          place-items: center;
          padding: 20px;
          background: rgba(24,23,21,.28);
          backdrop-filter: blur(6px);
        }

        .admin-command-modal {
          width: min(530px, 100%);
          padding: 25px;
          border-radius: 15px;
          background: #faf8f3;
          box-shadow: 0 28px 90px rgba(0,0,0,.18);
        }

        .admin-command-modal h3 {
          margin: 0;
          font-size: 24px;
          letter-spacing: -.045em;
        }

        .admin-command-modal-meta {
          margin: 7px 0 18px;
          color: rgba(24,23,21,.48);
          font-size: 10px;
        }

        .admin-command-modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 19px;
        }

        @media (max-width: 1150px) {
          .admin-command-sidebar {
            width: 200px;
            flex-basis: 200px;
          }

          .admin-command-topbar {
            padding-right: 180px;
          }

          .admin-command-kpis {
            grid-template-columns: repeat(2, 1fr);
          }

          .admin-command-grid,
          .admin-command-grid-equal {
            grid-template-columns: 1fr;
          }

          .admin-command-ops {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 820px) {
          .admin-command-shell {
            display: block;
          }

          .admin-command-sidebar {
            position: sticky;
            width: 100%;
            height: auto;
            padding: 11px 12px;
            border-right: 0;
            border-bottom: 1px solid rgba(24,23,21,.11);
          }

          .admin-command-logo {
            display: none;
          }

          .admin-command-nav {
            margin: 0;
            display: flex;
            overflow-x: auto;
            gap: 4px;
          }

          .admin-command-nav button {
            min-width: max-content;
            width: auto;
            grid-template-columns: auto auto;
          }

          .admin-command-sidebar-bottom {
            display: none;
          }

          .admin-command-topbar {
            min-height: 64px;
            padding: 0 145px 0 16px;
          }

          .admin-command-topbar-actions {
            gap: 5px;
          }

          .admin-command-topbar-actions .admin-command-button:first-child {
            display: none;
          }

          .admin-command-page {
            width: min(100% - 26px, 1500px);
            padding-top: 24px;
          }

          .admin-command-hero {
            flex-direction: column;
            align-items: flex-start;
          }

          .admin-command-kpis {
            grid-template-columns: 1fr;
          }

          .admin-command-donut-layout {
            flex-direction: column;
            padding-bottom: 15px;
          }

          .admin-command-risk-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
      `}</style>

      <div className="admin-command-shell">
        <aside className="admin-command-sidebar">
          <div className="admin-command-logo">
            <strong>LABEL LENS</strong>
            <span>Admin Control Center</span>
          </div>

          <nav className="admin-command-nav">
            {sectionItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className={
                  activeSection === item.id
                    ? 'active'
                    : ''
                }
                onClick={() =>
                  scrollToSection(item.id)
                }
              >
                <span className="admin-command-nav-number">
                  {item.number}
                </span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="admin-command-sidebar-bottom">
            <div className="admin-command-sidebar-user">
              {user?.full_name ||
                user?.email ||
                'Administrator'}
            </div>

            <div className="admin-command-sidebar-role">
              {user?.role || 'admin'}
            </div>
          </div>
        </aside>

        <div className="admin-command-main">
          <header className="admin-command-topbar">
            <div className="admin-command-topbar-left">
              <div className="admin-command-topbar-label">
                Department Compliance Platform
              </div>
              <div className="admin-command-topbar-title">
                Administrative Intelligence
              </div>
            </div>

            <div className="admin-command-topbar-actions">
              <button
                type="button"
                className="admin-command-button"
                onClick={() =>
                  void refreshRecords()
                }
                disabled={loading}
              >
                {loading
                  ? 'Refreshing…'
                  : 'Refresh Data'}
              </button>

              <button
                type="button"
                className="admin-command-button dark"
                onClick={onOpenScan}
              >
                + New Inspection
              </button>

              <button
                type="button"
                className="admin-command-button"
                onClick={onLogout}
              >
                Log out
              </button>
            </div>
          </header>

          <main className="admin-command-page">
            <section
              id="admin-overview"
              className="admin-command-section"
            >
              <div className="admin-command-hero">
                <div>
                  <p className="admin-command-kicker">
                    System-Wide Compliance Intelligence
                  </p>

                  <h1>Admin Dashboard</h1>

                  <p>
                    Monitor inspections, officer performance,
                    product categories, violations and
                    high-risk cases from one administrative
                    command center.
                  </p>
                </div>

                <div className="admin-command-updated">
                  {lastRefresh
                    ? `Updated ${lastRefresh.toLocaleTimeString(
                        [],
                        {
                          hour: 'numeric',
                          minute: '2-digit',
                        },
                      )}`
                    : 'Loading…'}
                </div>
              </div>

              {loading &&
              records.length === 0 ? (
                <div className="admin-command-card admin-command-empty">
                  Loading system intelligence…
                </div>
              ) : (
                <>
                  <div className="admin-command-kpis">
                    <article className="admin-command-kpi">
                      <span className="admin-command-kpi-label">
                        Total Inspections
                      </span>
                      <strong className="admin-command-kpi-value">
                        {analytics.total}
                      </strong>
                      <span className="admin-command-kpi-note">
                        All recorded inspections
                      </span>
                    </article>

                    <article className="admin-command-kpi">
                      <span className="admin-command-kpi-label">
                        Compliant
                      </span>
                      <strong className="admin-command-kpi-value">
                        {analytics.compliant}
                      </strong>
                      <span className="admin-command-kpi-note">
                        Passed compliance checks
                      </span>
                    </article>

                    <article className="admin-command-kpi">
                      <span className="admin-command-kpi-label">
                        Non-Compliant
                      </span>
                      <strong className="admin-command-kpi-value">
                        {analytics.nonCompliant}
                      </strong>
                      <span className="admin-command-kpi-note">
                        Requiring correction or action
                      </span>
                    </article>

                    <article className="admin-command-kpi">
                      <span className="admin-command-kpi-label">
                        Compliance Rate
                      </span>
                      <strong className="admin-command-kpi-value">
                        {analytics.complianceRate.toFixed(
                          1,
                        )}
                        %
                      </strong>
                      <span className="admin-command-kpi-note">
                        Overall system performance
                      </span>
                    </article>
                  </div>

                  <div className="admin-command-ops">
                    <div className="admin-command-op">
                      <span>Active Officers</span>
                      <strong>
                        {analytics.activeOfficers}
                      </strong>
                    </div>

                    <div className="admin-command-op">
                      <span>Inspections Today</span>
                      <strong>
                        {analytics.inspectionsToday}
                      </strong>
                    </div>

                    <div className="admin-command-op">
                      <span>Avg. Inspections / Officer</span>
                      <strong>
                        {analytics.averagePerOfficer.toFixed(
                          1,
                        )}
                      </strong>
                    </div>
                  </div>

                  <div className="admin-command-grid">
                    <article className="admin-command-card">
                      <div className="admin-command-card-heading">
                        <div>
                          <h2>
                            Daily Inspection Activity
                          </h2>
                          <p>
                            Last 7 days · compliant vs
                            non-compliant
                          </p>
                        </div>

                        <div className="admin-command-legend">
                          <span className="admin-command-legend-item">
                            <span className="admin-command-legend-dot" />
                            Compliant
                          </span>

                          <span className="admin-command-legend-item">
                            <span className="admin-command-legend-dot soft" />
                            Non-compliant
                          </span>
                        </div>
                      </div>

                      <div className="admin-command-chart-scroll">
                        <svg
                          viewBox="0 0 760 285"
                          width="100%"
                          height="285"
                          role="img"
                          aria-label="Daily inspection activity"
                        >
                          {[0, 1, 2, 3].map(
                            (line) => (
                              <line
                                key={line}
                                x1="40"
                                y1={
                                  35 +
                                  line *
                                    58
                                }
                                x2="735"
                                y2={
                                  35 +
                                  line *
                                    58
                                }
                                stroke="rgba(24,23,21,.08)"
                              />
                            ),
                          )}

                          {analytics.days.map(
                            (day, index) => {
                              const total =
                                day.compliant +
                                day.nonCompliant

                              const x =
                                60 +
                                index *
                                  100

                              const totalHeight =
                                (total /
                                  maxDaily) *
                                155

                              const compliantHeight =
                                (day.compliant /
                                  maxDaily) *
                                155

                              return (
                                <g
                                  key={
                                    day.label
                                  }
                                >
                                  <rect
                                    x={x}
                                    y={
                                      215 -
                                      totalHeight
                                    }
                                    width="42"
                                    height={
                                      totalHeight
                                    }
                                    rx="6"
                                    fill="#bdb5a8"
                                  />

                                  <rect
                                    x={x}
                                    y={
                                      215 -
                                      compliantHeight
                                    }
                                    width="42"
                                    height={
                                      compliantHeight
                                    }
                                    rx="6"
                                    fill="#27372d"
                                  />

                                  <text
                                    x={
                                      x +
                                      21
                                    }
                                    y="241"
                                    textAnchor="middle"
                                    fontSize="10"
                                    fill="rgba(24,23,21,.48)"
                                  >
                                    {
                                      day.label
                                    }
                                  </text>

                                  <text
                                    x={
                                      x +
                                      21
                                    }
                                    y={
                                      207 -
                                      totalHeight
                                    }
                                    textAnchor="middle"
                                    fontSize="9"
                                    fill="rgba(24,23,21,.55)"
                                  >
                                    {total}
                                  </text>
                                </g>
                              )
                            },
                          )}
                        </svg>
                      </div>
                    </article>

                    <article className="admin-command-card">
                      <div className="admin-command-card-heading">
                        <div>
                          <h2>
                            Compliance Health
                          </h2>
                          <p>
                            Overall inspection outcome
                          </p>
                        </div>
                      </div>

                      <div className="admin-command-donut-layout">
                        <div className="admin-command-donut">
                          <div className="admin-command-donut-center">
                            <strong>
                              {analytics.complianceRate.toFixed(
                                0,
                              )}
                              %
                            </strong>
                            <span>
                              compliant
                            </span>
                          </div>
                        </div>

                        <div className="admin-command-mini-stats">
                          <div className="admin-command-mini-stat">
                            <span>
                              Compliant
                            </span>
                            <strong>
                              {
                                analytics.compliant
                              }
                            </strong>
                          </div>

                          <div className="admin-command-mini-stat">
                            <span>
                              Non-Compliant
                            </span>
                            <strong>
                              {
                                analytics.nonCompliant
                              }
                            </strong>
                          </div>

                          <div className="admin-command-mini-stat">
                            <span>
                              Avg. Score
                            </span>
                            <strong>
                              {analytics.averageScore.toFixed(
                                1,
                              )}
                            </strong>
                          </div>

                          <div className="admin-command-mini-stat">
                            <span>
                              Manual Review
                            </span>
                            <strong>
                              {
                                analytics.manualReviews
                              }
                            </strong>
                          </div>
                        </div>
                      </div>
                    </article>
                  </div>
                </>
              )}
            </section>

            <section
              id="admin-inspections"
              className="admin-command-section"
            >
              <div className="admin-command-grid-equal">
                <article className="admin-command-card">
                  <div className="admin-command-card-heading">
                    <div>
                      <h2>
                        Inspection Search
                      </h2>
                      <p>
                        Search the department inspection
                        registry
                      </p>
                    </div>
                  </div>

                  <div className="admin-command-search-row">
                    <input
                      className="admin-command-search"
                      value={search}
                      onChange={(e) =>
                        setSearch(e.target.value)
                      }
                      placeholder="Search product, officer, ID, department..."
                    />
                  </div>

                  <div className="admin-command-table-wrap">
                    <table className="admin-command-table">
                      <thead>
                        <tr>
                          <th>Product</th>
                          <th>Officer</th>
                          <th>Date</th>
                          <th>Score</th>
                          <th>Status</th>
                        </tr>
                      </thead>

                      <tbody>
                        {filteredRecords
                          .slice(0, 8)
                          .map((record) => (
                            <tr key={record.id}>
                              <td>
                                <span className="admin-command-name">
                                  {record.product_id ||
                                    'Unknown Product'}
                                </span>
                              </td>

                              <td>
                                {record.officer_name ||
                                  record.officer_id ||
                                  'Unknown'}
                              </td>

                              <td>
                                {new Date(
                                  record.created_at,
                                ).toLocaleDateString(
                                  undefined,
                                  {
                                    day: 'numeric',
                                    month: 'short',
                                    year: 'numeric',
                                  },
                                )}
                              </td>

                              <td>
                                {getScore(
                                  record,
                                ).toFixed(0)}
                              </td>

                              <td>
                                <span
                                  className={
                                    record.is_compliant
                                      ? 'admin-command-status active'
                                      : 'admin-command-status'
                                  }
                                >
                                  {record.is_compliant
                                    ? 'Compliant'
                                    : 'Non-Compliant'}
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>

                  {filteredRecords.length === 0 && (
                    <div className="admin-command-empty">
                      No matching inspections.
                    </div>
                  )}
                </article>

                <article className="admin-command-card">
                  <div className="admin-command-card-heading">
                    <div>
                      <h2>
                        High-Risk Queue
                      </h2>
                      <p>
                        Lowest-scoring inspections requiring
                        attention
                      </p>
                    </div>
                  </div>

                  {analytics.highRisk.length === 0 ? (
                    <div className="admin-command-empty">
                      No high-risk inspections available.
                    </div>
                  ) : (
                    <div className="admin-command-highrisk">
                      {analytics.highRisk
                        .slice(0, 6)
                        .map((record) => {
                          const risk =
                            riskFor(
                              getScore(
                                record,
                              ),
                            )

                          return (
                            <div
                              key={
                                record.id
                              }
                              className="admin-command-highrisk-row"
                            >
                              <div>
                                <strong>
                                  {record.product_id ||
                                    'Unknown Product'}
                                </strong>
                              </div>

                              <span>
                                {record.officer_name ||
                                  record.officer_id ||
                                  'Unknown'}
                              </span>

                              <strong>
                                {getScore(
                                  record,
                                ).toFixed(0)}
                              </strong>

                              <span
                                className={`admin-command-risk-pill ${risk.className}`}
                              >
                                {risk.label}
                              </span>
                            </div>
                          )
                        })}
                    </div>
                  )}
                </article>
              </div>
            </section>

            <section
              id="admin-officers"
              className="admin-command-section"
            >
              <article className="admin-command-card">
                <div className="admin-command-card-heading">
                  <div>
                    <h2>
                      Officer Management
                    </h2>
                    <p>
                      Workload, compliance performance and
                      account activity
                    </p>
                  </div>
                </div>

                {analytics.officers.length === 0 ? (
                  <div className="admin-command-empty">
                    No officer activity available.
                  </div>
                ) : (
                  <div className="admin-command-table-wrap">
                    <table className="admin-command-table">
                      <thead>
                        <tr>
                          <th>
                            Officer ID / Name
                          </th>
                          <th>
                            Department
                          </th>
                          <th>
                            Inspections
                          </th>
                          <th>
                            Compliance Rate
                          </th>
                          <th>
                            Avg. Score
                          </th>
                          <th>
                            Status
                          </th>
                          <th>
                            Action
                          </th>
                        </tr>
                      </thead>

                      <tbody>
                        {analytics.officers
                          .slice(0, 10)
                          .map(
                            (officer) => (
                              <tr
                                key={
                                  officer.id
                                }
                              >
                                <td>
                                  <span className="admin-command-name">
                                    {
                                      officer.name
                                    }
                                  </span>
                                  <span className="admin-command-sub">
                                    {
                                      officer.id
                                    }
                                  </span>
                                </td>

                                <td>
                                  {
                                    officer.department
                                  }
                                </td>

                                <td>
                                  {
                                    officer.inspections
                                  }
                                </td>

                                <td>
                                  <span className="admin-command-progress">
                                    <span
                                      style={{
                                        width: `${Math.min(
                                          officer.complianceRate,
                                          100,
                                        )}%`,
                                      }}
                                    />
                                  </span>
                                  {officer.complianceRate.toFixed(
                                    0,
                                  )}
                                  %
                                </td>

                                <td>
                                  {officer.averageScore.toFixed(
                                    1,
                                  )}
                                </td>

                                <td>
                                  <span
                                    className={
                                      officer.active
                                        ? 'admin-command-status active'
                                        : 'admin-command-status'
                                    }
                                  >
                                    {officer.active
                                      ? 'Active'
                                      : 'Inactive'}
                                  </span>
                                </td>

                                <td>
                                  <button
                                    type="button"
                                    className="admin-command-view"
                                    onClick={() =>
                                      setSelectedOfficer(
                                        officer.id,
                                      )
                                    }
                                  >
                                    View Officer
                                  </button>
                                </td>
                              </tr>
                            ),
                          )}
                      </tbody>
                    </table>
                  </div>
                )}
              </article>
            </section>

            <section
              id="admin-violations"
              className="admin-command-section"
            >
              <div className="admin-command-grid-equal">
                <article className="admin-command-card">
                  <div className="admin-command-card-heading">
                    <div>
                      <h2>
                        Top Violations
                      </h2>
                      <p>
                        Most frequently triggered compliance
                        rules
                      </p>
                    </div>
                  </div>

                  {analytics.violations.length === 0 ? (
                    <div className="admin-command-empty">
                      No violations recorded.
                    </div>
                  ) : (
                    analytics.violations.map(
                      (violation, index) => (
                        <div
                          key={
                            violation.name
                          }
                          className="admin-command-violation"
                        >
                          <span className="admin-command-violation-number">
                            {String(
                              index + 1,
                            ).padStart(
                              2,
                              '0',
                            )}
                          </span>

                          <div>
                            <div className="admin-command-violation-name">
                              {
                                violation.name
                              }
                            </div>

                            <div className="admin-command-bar">
                              <span
                                style={{
                                  width: `${
                                    (violation.count /
                                      maxViolation) *
                                    100
                                  }%`,
                                }}
                              />
                            </div>
                          </div>

                          <span className="admin-command-violation-count">
                            {
                              violation.count
                            }
                          </span>
                        </div>
                      ),
                    )
                  )}
                </article>

                <article className="admin-command-card">
                  <div className="admin-command-card-heading">
                    <div>
                      <h2>
                        Risk Distribution
                      </h2>
                      <p>
                        Inspection distribution by score
                      </p>
                    </div>
                  </div>

                  <div className="admin-command-risk-grid">
                    <div className="admin-command-risk-box">
                      <span>
                        Critical
                      </span>
                      <strong>
                        {
                          analytics.riskCounts
                            .critical
                        }
                      </strong>
                    </div>

                    <div className="admin-command-risk-box">
                      <span>High</span>
                      <strong>
                        {
                          analytics.riskCounts
                            .high
                        }
                      </strong>
                    </div>

                    <div className="admin-command-risk-box">
                      <span>
                        Medium
                      </span>
                      <strong>
                        {
                          analytics.riskCounts
                            .medium
                        }
                      </strong>
                    </div>

                    <div className="admin-command-risk-box">
                      <span>Low</span>
                      <strong>
                        {
                          analytics.riskCounts
                            .low
                        }
                      </strong>
                    </div>
                  </div>
                </article>
              </div>
            </section>

            <section
              id="admin-analytics"
              className="admin-command-section"
            >
              <div className="admin-command-grid-equal">
                <article className="admin-command-card">
                  <div className="admin-command-card-heading">
                    <div>
                      <h2>
                        Compliance by Product Category
                      </h2>
                      <p>
                        Volume and compliance performance
                      </p>
                    </div>
                  </div>

                  {analytics.categoryData.length ===
                  0 ? (
                    <div className="admin-command-empty">
                      No category data available.
                    </div>
                  ) : (
                    analytics.categoryData.map(
                      (category) => (
                        <div
                          key={
                            category.name
                          }
                          className="admin-command-category"
                        >
                          <span className="admin-command-category-name">
                            {
                              category.name
                            }
                          </span>

                          <div className="admin-command-bar">
                            <span
                              style={{
                                width: `${
                                  (category.total /
                                    maxCategory) *
                                  100
                                }%`,
                              }}
                            />
                          </div>

                          <span className="admin-command-category-count">
                            {
                              category.total
                            }
                          </span>

                          <strong className="admin-command-category-rate">
                            {category.complianceRate.toFixed(
                              0,
                            )}
                            %
                          </strong>
                        </div>
                      ),
                    )
                  )}
                </article>

                <article className="admin-command-card">
                  <div className="admin-command-card-heading">
                    <div>
                      <h2>
                        Average Compliance Score
                      </h2>
                      <p>
                        Daily score trend over the last 7 days
                      </p>
                    </div>
                  </div>

                  <div className="admin-command-chart-scroll">
                    <svg
                      viewBox="0 0 720 260"
                      width="100%"
                      height="260"
                      role="img"
                      aria-label="Average compliance score trend"
                    >
                      {[0, 1, 2, 3, 4].map(
                        (line) => (
                          <g key={line}>
                            <line
                              x1="48"
                              y1={
                                35 +
                                line *
                                  45
                              }
                              x2="700"
                              y2={
                                35 +
                                line *
                                  45
                              }
                              stroke="rgba(24,23,21,.08)"
                            />

                            <text
                              x="35"
                              y={
                                39 +
                                line *
                                  45
                              }
                              textAnchor="end"
                              fontSize="9"
                              fill="rgba(24,23,21,.42)"
                            >
                              {
                                100 -
                                line *
                                  25
                              }
                            </text>
                          </g>
                        ),
                      )}

                      <polyline
                        fill="none"
                        stroke="#27372d"
                        strokeWidth="4"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                        points={analytics.days
                          .map(
                            (
                              day,
                              index,
                            ) => {
                              const x =
                                65 +
                                index *
                                  102

                              const y =
                                215 -
                                (day.averageScore /
                                  100) *
                                  180

                              return `${x},${y}`
                            },
                          )
                          .join(
                            ' ',
                          )}
                      />

                      {analytics.days.map(
                        (day, index) => {
                          const x =
                            65 +
                            index *
                              102

                          const y =
                            215 -
                            (day.averageScore /
                              100) *
                              180

                          return (
                            <g
                              key={
                                day.label
                              }
                            >
                              <circle
                                cx={x}
                                cy={y}
                                r="5"
                                fill="#27372d"
                              />

                              <text
                                x={x}
                                y="240"
                                textAnchor="middle"
                                fontSize="10"
                                fill="rgba(24,23,21,.48)"
                              >
                                {
                                  day.label
                                }
                              </text>

                              <text
                                x={x}
                                y={
                                  y -
                                  11
                                }
                                textAnchor="middle"
                                fontSize="9"
                                fill="rgba(24,23,21,.55)"
                              >
                                {day.averageScore.toFixed(
                                  0,
                                )}
                              </text>
                            </g>
                          )
                        },
                      )}
                    </svg>
                  </div>
                </article>
              </div>

              <article className="admin-command-card">
                <div className="admin-command-card-heading">
                  <div>
                    <h2>
                      Department Performance Snapshot
                    </h2>
                    <p>
                      Officer-level workload and outcomes
                    </p>
                  </div>
                </div>

                <div className="admin-command-table-wrap">
                  <table className="admin-command-table">
                    <thead>
                      <tr>
                        <th>
                          Officer
                        </th>
                        <th>
                          Department
                        </th>
                        <th>
                          Inspections
                        </th>
                        <th>
                          Compliance
                        </th>
                        <th>
                          Average Score
                        </th>
                        <th>
                          Activity
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {analytics.officers
                        .slice(0, 12)
                        .map(
                          (officer) => (
                            <tr
                              key={
                                officer.id
                              }
                            >
                              <td>
                                <span className="admin-command-name">
                                  {
                                    officer.name
                                  }
                                </span>

                                <span className="admin-command-sub">
                                  {
                                    officer.email
                                  }
                                </span>
                              </td>

                              <td>
                                {
                                  officer.department
                                }
                              </td>

                              <td>
                                {
                                  officer.inspections
                                }
                              </td>

                              <td>
                                {officer.complianceRate.toFixed(
                                  0,
                                )}
                                %
                              </td>

                              <td>
                                {officer.averageScore.toFixed(
                                  1,
                                )}
                              </td>

                              <td>
                                <span
                                  className={
                                    officer.active
                                      ? 'admin-command-status active'
                                      : 'admin-command-status'
                                  }
                                >
                                  {officer.active
                                    ? 'Active'
                                    : 'Inactive'}
                                </span>
                              </td>
                            </tr>
                          ),
                        )}
                    </tbody>
                  </table>
                </div>
              </article>
            </section>

            <section
              id="admin-audit"
              className="admin-command-section"
            >
              <article className="admin-command-card">
                <div className="admin-command-card-heading">
                  <div>
                    <h2>
                      Recent Activity / Audit Log
                    </h2>
                    <p>
                      Latest recorded compliance events
                    </p>
                  </div>
                </div>

                {analytics.recent.length === 0 ? (
                  <div className="admin-command-empty">
                    No recent activity available.
                  </div>
                ) : (
                  <div className="admin-command-audit">
                    {analytics.recent.map(
                      (record) => {
                        const date =
                          new Date(
                            record.created_at,
                          )

                        const time =
                          date.toLocaleTimeString(
                            [],
                            {
                              hour: 'numeric',
                              minute:
                                '2-digit',
                            },
                          )

                        let title =
                          'Inspection completed'

                        if (
                          record.needs_manual_review
                        ) {
                          title =
                            'Manual review required'
                        } else if (
                          !record.is_compliant
                        ) {
                          title =
                            'New non-compliant product detected'
                        } else {
                          title =
                            'Compliant inspection completed'
                        }

                        return (
                          <div
                            key={
                              record.id
                            }
                            className="admin-command-audit-row"
                          >
                            <div className="admin-command-audit-time">
                              {time}
                            </div>

                            <div className="admin-command-audit-dot">
                              <span />
                            </div>

                            <div className="admin-command-audit-copy">
                              <strong>
                                {title}
                              </strong>

                              <p>
                                {record.product_id ||
                                  'Unknown product'}
                                {' · '}
                                {record.officer_name ||
                                  record.officer_id ||
                                  'Unknown officer'}
                                {' · '}
                                Score{' '}
                                {getScore(
                                  record,
                                ).toFixed(0)}
                              </p>
                            </div>
                          </div>
                        )
                      },
                    )}
                  </div>
                )}
              </article>
            </section>
          </main>
        </div>
      </div>

      {selectedOfficerData && (
        <div
          className="admin-command-modal-backdrop"
          onClick={() =>
            setSelectedOfficer(null)
          }
        >
          <div
            className="admin-command-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <p className="admin-command-kicker">
              Officer Profile
            </p>

            <h3>
              {selectedOfficerData.name}
            </h3>

            <p className="admin-command-modal-meta">
              {selectedOfficerData.id}
              {' · '}
              {selectedOfficerData.department}
            </p>

            <div className="admin-command-mini-stat">
              <span>
                Email
              </span>
              <strong style={{ fontSize: 10 }}>
                {selectedOfficerData.email}
              </strong>
            </div>

            <div className="admin-command-mini-stat">
              <span>
                Inspections
              </span>
              <strong>
                {
                  selectedOfficerData.inspections
                }
              </strong>
            </div>

            <div className="admin-command-mini-stat">
              <span>
                Compliance rate
              </span>
              <strong>
                {selectedOfficerData.complianceRate.toFixed(
                  1,
                )}
                %
              </strong>
            </div>

            <div className="admin-command-mini-stat">
              <span>
                Average score
              </span>
              <strong>
                {selectedOfficerData.averageScore.toFixed(
                  1,
                )}
              </strong>
            </div>

            <div className="admin-command-mini-stat">
              <span>
                Account activity
              </span>
              <strong>
                {selectedOfficerData.active
                  ? 'Active'
                  : 'Inactive'}
              </strong>
            </div>

            <div className="admin-command-modal-actions">
              <button
                type="button"
                className="admin-command-button"
                onClick={() =>
                  setSelectedOfficer(null)
                }
              >
                Close
              </button>

              <button
                type="button"
                className="admin-command-button dark"
                onClick={() =>
                  alert(
                    'Officer deactivation requires the admin account-management endpoint.',
                  )
                }
              >
                Deactivate Officer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
