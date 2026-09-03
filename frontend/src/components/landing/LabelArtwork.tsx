/** Original label-pack illustration. Not sourced from the reference site. */
export function LabelArtwork() {
  return (
    <div className="pack-stage" aria-hidden="true">
      <div className="pack-shadow" />
      <svg
        className="pack-svg"
        viewBox="0 0 360 480"
        role="img"
        aria-label="Stylized packaged commodity label"
      >
        <rect x="28" y="16" width="304" height="448" rx="8" fill="#f6f1e8" />
        <rect x="28" y="16" width="304" height="96" fill="#171717" />
        <text
          x="180"
          y="58"
          textAnchor="middle"
          fill="#f6f1e8"
          fontFamily="Syne, sans-serif"
          fontSize="22"
          fontWeight="800"
          letterSpacing="4"
        >
          LABEL LENS
        </text>
        <text
          x="180"
          y="82"
          textAnchor="middle"
          fill="#c9c3b8"
          fontFamily="Manrope, sans-serif"
          fontSize="10"
          letterSpacing="2.4"
        >
          PACKAGED COMMODITY
        </text>
        <rect x="52" y="136" width="256" height="8" fill="#171717" />
        <text
          x="52"
          y="172"
          fill="#171717"
          fontFamily="Syne, sans-serif"
          fontSize="28"
          fontWeight="800"
        >
          NET 500 g
        </text>
        <text
          x="52"
          y="208"
          fill="#5a564e"
          fontFamily="Manrope, sans-serif"
          fontSize="13"
        >
          Common name · Packaged food
        </text>
        <rect x="52" y="232" width="256" height="1" fill="#d9d2c6" />
        <text x="52" y="262" fill="#8a8478" fontSize="10" letterSpacing="1.6">
          MRP
        </text>
        <text
          x="52"
          y="286"
          fill="#171717"
          fontFamily="Syne, sans-serif"
          fontSize="20"
          fontWeight="700"
        >
          ₹ 94.00
        </text>
        <text x="52" y="308" fill="#5a564e" fontSize="11">
          Inclusive of all taxes
        </text>
        <rect x="52" y="332" width="256" height="1" fill="#d9d2c6" />
        <text x="52" y="362" fill="#8a8478" fontSize="10" letterSpacing="1.6">
          MFG · BEST BEFORE
        </text>
        <text x="52" y="386" fill="#171717" fontSize="13">
          03 / 2026  ·  12 months
        </text>
        <text x="52" y="418" fill="#8a8478" fontSize="10" letterSpacing="1.6">
          CONSUMER CARE
        </text>
        <text x="52" y="440" fill="#171717" fontSize="12">
          care@product.example
        </text>
      </svg>
      <div className="pack-stamp">LMPC · 2011</div>
    </div>
  )
}
