interface FooterProps {
  onScan: () => void
  onJump: (id: string) => void
}

export function Footer({ onScan, onJump }: FooterProps) {
  return (
    <footer className="site-footer">
      <div>
        <p className="wordmark">Label Lens</p>
        <p>SIH26034</p>
        <p>Legal Metrology Compliance</p>
      </div>
      <div className="footer-links">
        <button type="button" onClick={() => onJump('product')}>
          Product
        </button>
        <button type="button" onClick={() => onJump('how')}>
          How it Works
        </button>
        <button type="button" onClick={onScan}>
          Contact
        </button>
      </div>
    </footer>
  )
}
