interface ScanCtaProps {
  onScan: () => void
}

export function ScanCta({ onScan }: ScanCtaProps) {
  return (
    <section className="cta-band">
      <h2>
        READY TO CHECK
        <br />
        YOUR PRODUCT?
      </h2>
      <button type="button" className="btn-solid invert" onClick={onScan}>
        START SCANNING →
      </button>
    </section>
  )
}
