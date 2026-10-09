/* @ds-bundle: {"format":4,"namespace":"EquilibriumDesignSystem_83a4c4","components":[{"name":"Isotipo","sourcePath":"components/brand/Isotipo.jsx"},{"name":"Logo","sourcePath":"components/brand/Logo.jsx"},{"name":"Card","sourcePath":"components/content/Card.jsx"},{"name":"NumberedList","sourcePath":"components/content/NumberedList.jsx"},{"name":"Quote","sourcePath":"components/content/Quote.jsx"},{"name":"SectionHeader","sourcePath":"components/content/SectionHeader.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"BarChart","sourcePath":"components/data/BarChart.jsx"},{"name":"ColumnChart","sourcePath":"components/data/ColumnChart.jsx"},{"name":"StatFigure","sourcePath":"components/data/StatFigure.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Radio","sourcePath":"components/forms/Radio.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"DuotonePhoto","sourcePath":"components/media/DuotonePhoto.jsx"},{"name":"NavBar","sourcePath":"components/navigation/NavBar.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"}],"sourceHashes":{"components/brand/Isotipo.jsx":"f1e4d7e18033","components/brand/Logo.jsx":"d0171712c054","components/content/Card.jsx":"07500f2d9a12","components/content/NumberedList.jsx":"bdc72cb792fb","components/content/Quote.jsx":"cd68580e80e7","components/content/SectionHeader.jsx":"a8965d31ed6f","components/core/Button.jsx":"1e79dcef0700","components/core/Icon.jsx":"2636fdf7ace3","components/core/IconButton.jsx":"bec5d71518a3","components/core/Tag.jsx":"31c12187466d","components/data/BarChart.jsx":"e865535c6d73","components/data/ColumnChart.jsx":"42e235457359","components/data/StatFigure.jsx":"421066104eaa","components/feedback/Dialog.jsx":"4daa4aebaddd","components/forms/Checkbox.jsx":"499cbddd039c","components/forms/Input.jsx":"96bc9287e39f","components/forms/Radio.jsx":"cd361db32466","components/forms/Select.jsx":"a0618810107f","components/forms/Switch.jsx":"234ba6202b6b","components/media/DuotonePhoto.jsx":"a0a87bececf1","components/navigation/NavBar.jsx":"b160badaf476","components/navigation/Tabs.jsx":"89ca010bb9fc","slides/fit.js":"72d631be2540","ui_kits/website/About.jsx":"acf842e942cd","ui_kits/website/Contact.jsx":"1445ff6233e2","ui_kits/website/Footer.jsx":"76bff3a052fb","ui_kits/website/Home.jsx":"02078bd60ed1","ui_kits/website/Reports.jsx":"f7e579b32502","ui_kits/website/Services.jsx":"9f7fdda302f5"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.EquilibriumDesignSystem_83a4c4 = window.EquilibriumDesignSystem_83a4c4 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/brand/Isotipo.jsx
try { (() => {
const P1 = 'M196.88,255.21c24.63,0,47.35-8.14,65.63-21.88-26.61,35.42-68.96,58.33-116.67,58.33C65.29,291.67,0,226.38,0,145.83h87.5c0,60.41,48.97,109.38,109.38,109.38Z';
const P2 = 'M145.83,0C98.13,0,55.77,22.91,29.17,58.33c18.28-13.73,41-21.88,65.63-21.88,60.41,0,109.38,48.97,109.38,109.38h87.5C291.67,65.29,226.38,0,145.83,0Z';
function Isotipo({
  size = 64,
  color = 'var(--eq-coral)',
  style,
  title
}) {
  return /*#__PURE__*/React.createElement("svg", {
    className: "eq-isotipo",
    viewBox: "0 0 291.67 291.67",
    width: size,
    height: size,
    fill: "currentColor",
    role: title ? 'img' : undefined,
    "aria-hidden": title ? undefined : true,
    style: {
      display: 'block',
      flex: 'none',
      color,
      pointerEvents: 'none',
      ...style
    }
  }, title && /*#__PURE__*/React.createElement("title", null, title), /*#__PURE__*/React.createElement("path", {
    d: P1
  }), /*#__PURE__*/React.createElement("path", {
    d: P2
  }));
}
Object.assign(__ds_scope, { Isotipo });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/Isotipo.jsx", error: String((e && e.message) || e) }); }

// components/brand/Logo.jsx
try { (() => {
const FILES = {
  principal: 'logo-principal',
  tagline: 'logo-tagline',
  isotipo: 'isotipo'
};
function Logo({
  variant = 'principal',
  color = 'azul',
  height = 40,
  basePath = '',
  style,
  alt = 'Equilibrium'
}) {
  const src = basePath + 'assets/logos/' + FILES[variant] + '-' + color + '.svg';
  return /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: alt,
    style: {
      height,
      width: 'auto',
      display: 'block',
      ...style
    }
  });
}
Object.assign(__ds_scope, { Logo });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/Logo.jsx", error: String((e && e.message) || e) }); }

// components/content/Card.jsx
try { (() => {
const TONES = {
  white: ['var(--eq-white)', 'var(--eq-navy)', 'var(--eq-gray-600)'],
  paper: ['var(--eq-paper)', 'var(--eq-navy)', 'var(--eq-gray-600)'],
  navy: ['var(--eq-navy)', 'var(--eq-paper)', 'var(--eq-paper)'],
  coral: ['var(--eq-coral)', 'var(--eq-navy)', 'var(--eq-navy)'],
  teal: ['var(--eq-teal)', 'var(--eq-navy)', 'var(--eq-navy)'],
  muted: ['var(--eq-gray-100)', 'var(--eq-navy)', 'var(--eq-gray-600)']
};
function Card({
  tone = 'white',
  kicker,
  title,
  children,
  image,
  imageHeight = 200,
  accentCorner,
  footer,
  onClick,
  style
}) {
  const [bg, tc, bc] = TONES[tone] || TONES.white;
  const [h, setH] = React.useState(false);
  const r = accentCorner ? {
    'top-left': 'var(--radius-accent) 0 0 0',
    'top-right': '0 var(--radius-accent) 0 0',
    'bottom-right': '0 0 var(--radius-accent) 0',
    'bottom-left': '0 0 0 var(--radius-accent)'
  }[accentCorner] : 0;
  return /*#__PURE__*/React.createElement("div", {
    onClick: onClick,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      background: bg,
      borderRadius: r,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'var(--font-sans)',
      cursor: onClick ? 'pointer' : 'default',
      boxShadow: tone === 'white' ? h && onClick ? 'var(--shadow-1)' : 'inset 0 0 0 1px var(--eq-gray-100)' : 'none',
      transition: 'box-shadow var(--dur-base)',
      ...style
    }
  }, image && /*#__PURE__*/React.createElement("div", {
    style: {
      height: imageHeight,
      background: 'var(--eq-gray-100) center/cover url(' + image + ')',
      transform: h && onClick ? 'scale(1.02)' : 'none',
      transition: 'transform 400ms var(--ease-out)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 28,
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      flex: 1
    }
  }, kicker && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 700,
      letterSpacing: '.12em',
      textTransform: 'uppercase',
      color: tone === 'navy' ? 'var(--eq-coral)' : tc
    }
  }, kicker), title && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 22,
      fontWeight: 700,
      lineHeight: 1.2,
      color: tc,
      textWrap: 'balance'
    }
  }, title), children && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 16,
      lineHeight: 1.5,
      color: bc
    }
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'auto',
      paddingTop: 12
    }
  }, footer)));
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/Card.jsx", error: String((e && e.message) || e) }); }

// components/content/NumberedList.jsx
try { (() => {
function NumberedList({
  items = [],
  variant = 'rail',
  numberTone = 'navy',
  style
}) {
  const bg = numberTone === 'coral' ? 'var(--eq-coral)' : 'var(--eq-navy)';
  const fg = numberTone === 'coral' ? 'var(--eq-navy)' : 'var(--eq-paper)';
  if (variant === 'index') return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: bg,
      color: fg,
      borderRadius: '40px 0 0 40px',
      width: 72,
      display: 'flex',
      flexDirection: 'column',
      flex: 'none'
    }
  }, items.map((_, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      height: 64,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 26
    }
  }, i + 1))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      paddingLeft: 28
    }
  }, items.map((it, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      height: 64,
      display: 'flex',
      alignItems: 'center',
      fontSize: 22,
      fontWeight: 600,
      color: 'var(--eq-navy)',
      borderBottom: i < items.length - 1 ? '2px solid var(--eq-navy)' : 'none',
      boxSizing: 'border-box'
    }
  }, typeof it === 'string' ? it : it.title))));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'var(--font-sans)',
      background: 'var(--eq-gray-100)',
      ...style
    }
  }, items.map((it, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      borderTop: i ? '2px dotted var(--eq-navy)' : 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 64,
      flex: 'none',
      background: bg,
      color: fg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 18,
      borderTop: i ? '2px dotted var(--eq-paper)' : 'none',
      marginTop: i ? -2 : 0
    }
  }, i + 1, "."), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '18px 22px',
      fontSize: 16,
      lineHeight: 1.45,
      color: 'var(--eq-navy)'
    }
  }, typeof it === 'string' ? it : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("b", null, it.title), it.body && /*#__PURE__*/React.createElement("span", null, " \u2014 ", it.body))))));
}
Object.assign(__ds_scope, { NumberedList });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/NumberedList.jsx", error: String((e && e.message) || e) }); }

// components/content/Quote.jsx
try { (() => {
function Quote({
  children,
  source,
  align = 'right',
  style
}) {
  return /*#__PURE__*/React.createElement("figure", {
    style: {
      margin: 0,
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("blockquote", {
    style: {
      margin: 0,
      fontStyle: 'italic',
      fontSize: 'inherit',
      lineHeight: 1.5,
      color: 'var(--eq-gray-600)'
    }
  }, "\u201C", children, "\u201D"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      margin: '20px 0 12px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: align === 'right' ? 3 : 1,
      borderTop: '2px solid var(--eq-navy)'
    }
  }), /*#__PURE__*/React.createElement("svg", {
    width: "34",
    height: "22",
    viewBox: "0 0 34 22",
    style: {
      marginTop: -1,
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M0 1 L17 21 L34 1",
    fill: "none",
    stroke: "#030F50",
    strokeWidth: "2"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: align === 'right' ? 1 : 3,
      borderTop: '2px solid var(--eq-navy)'
    }
  })), source && /*#__PURE__*/React.createElement("figcaption", {
    style: {
      textAlign: align === 'right' ? 'right' : 'left',
      color: 'var(--eq-navy)',
      fontSize: '0.85em'
    }
  }, "(", source, ")"));
}
Object.assign(__ds_scope, { Quote });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/Quote.jsx", error: String((e && e.message) || e) }); }

// components/content/SectionHeader.jsx
try { (() => {
function SectionHeader({
  title,
  band = 'coral',
  variant = 'tab',
  basePath = '',
  height = 72,
  uppercase,
  style
}) {
  const bands = {
    coral: 'var(--eq-coral)',
    periwinkle: 'var(--eq-periwinkle)',
    teal: 'var(--eq-teal)',
    yellow: 'var(--eq-yellow)'
  };
  const t = {
    color: 'var(--eq-navy)',
    fontWeight: 700,
    fontSize: height * 0.42,
    textTransform: uppercase ? 'uppercase' : 'none',
    letterSpacing: uppercase ? '.02em' : 0,
    fontFamily: 'var(--font-sans)'
  };
  if (variant === 'rule') return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: height * 0.35,
      height,
      borderBottom: '2px solid var(--eq-navy)',
      padding: '0 ' + height * 0.25 + 'px',
      ...style
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: basePath + 'assets/logos/isotipo-azul.svg',
    alt: "",
    style: {
      height: height * 0.5,
      filter: band === 'coral' ? 'none' : 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: t
  }, title));
  const r = height * 0.32;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      height,
      background: 'var(--eq-navy)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: height * 1.2,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: basePath + 'assets/logos/isotipo-blanco.svg',
    alt: "",
    style: {
      height: height * 0.5
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      background: bands[band] || band,
      borderBottomLeftRadius: r,
      display: 'flex',
      alignItems: 'center',
      paddingLeft: height * 0.55
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: t
  }, title)));
}
Object.assign(__ds_scope, { SectionHeader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/SectionHeader.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CDN = 'https://unpkg.com/lucide-static@0.460.0/icons/';
function Icon({
  name,
  size = 20,
  color = 'currentColor',
  style,
  ...rest
}) {
  const url = 'url(' + CDN + name + '.svg)';
  return /*#__PURE__*/React.createElement("span", _extends({
    "aria-hidden": "true"
  }, rest, {
    style: {
      display: 'inline-block',
      flex: 'none',
      width: size,
      height: size,
      background: color,
      WebkitMask: url + ' center/contain no-repeat',
      mask: url + ' center/contain no-repeat',
      ...style
    }
  }));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const SIZES = {
  sm: {
    h: 36,
    px: 16,
    fs: 14
  },
  md: {
    h: 48,
    px: 24,
    fs: 16
  },
  lg: {
    h: 60,
    px: 32,
    fs: 18
  }
};
const VARIANTS = {
  primary: {
    bg: 'var(--eq-navy)',
    fg: 'var(--eq-paper)',
    bd: 'var(--eq-navy)',
    hbg: 'var(--eq-blue)',
    hfg: 'var(--eq-paper)',
    hbd: 'var(--eq-blue)'
  },
  accent: {
    bg: 'var(--eq-coral)',
    fg: 'var(--eq-navy)',
    bd: 'var(--eq-coral)',
    hbg: 'var(--eq-navy)',
    hfg: 'var(--eq-paper)',
    hbd: 'var(--eq-navy)'
  },
  secondary: {
    bg: 'transparent',
    fg: 'var(--eq-navy)',
    bd: 'var(--eq-navy)',
    hbg: 'var(--eq-navy)',
    hfg: 'var(--eq-paper)',
    hbd: 'var(--eq-navy)'
  },
  inverse: {
    bg: 'var(--eq-paper)',
    fg: 'var(--eq-navy)',
    bd: 'var(--eq-paper)',
    hbg: 'var(--eq-coral)',
    hfg: 'var(--eq-navy)',
    hbd: 'var(--eq-coral)'
  },
  ghost: {
    bg: 'transparent',
    fg: 'var(--eq-navy)',
    bd: 'transparent',
    hbg: 'transparent',
    hfg: 'var(--eq-blue)',
    hbd: 'transparent'
  }
};
function Button({
  variant = 'primary',
  size = 'md',
  iconRight,
  iconLeft,
  disabled,
  fullWidth,
  children,
  style,
  onClick,
  type = 'button',
  href,
  ...rest
}) {
  const [h, setH] = React.useState(false);
  const [p, setP] = React.useState(false);
  const s = SIZES[size] || SIZES.md,
    v = VARIANTS[variant] || VARIANTS.primary;
  const on = h && !disabled;
  const Tag = href ? 'a' : 'button';
  return /*#__PURE__*/React.createElement(Tag, _extends({}, rest, {
    href: href,
    type: href ? undefined : type,
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => {
      setH(false);
      setP(false);
    },
    onMouseDown: () => setP(true),
    onMouseUp: () => setP(false),
    style: {
      display: fullWidth ? 'flex' : 'inline-flex',
      width: fullWidth ? '100%' : undefined,
      alignItems: 'center',
      justifyContent: 'center',
      gap: 10,
      height: s.h,
      padding: variant === 'ghost' ? 0 : '0 ' + s.px + 'px',
      borderRadius: 0,
      border: '2px solid ' + (on ? v.hbd : v.bd),
      background: on ? v.hbg : v.bg,
      color: on ? v.hfg : v.fg,
      fontFamily: 'var(--font-sans)',
      fontWeight: 700,
      fontSize: s.fs,
      letterSpacing: '.01em',
      textDecoration: 'none',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      transform: p && !disabled ? 'translateY(1px)' : 'none',
      transition: 'background var(--dur-fast) var(--ease-out), color var(--dur-fast), border-color var(--dur-fast)',
      boxSizing: 'border-box',
      whiteSpace: 'nowrap',
      ...style
    }
  }), iconLeft && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconLeft,
    size: s.fs + 2
  }), children, iconRight && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconRight,
    size: s.fs + 2,
    style: {
      transform: on && variant === 'ghost' ? 'translateX(3px)' : 'none',
      transition: 'transform var(--dur-base) var(--ease-out)'
    }
  }));
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function IconButton({
  icon,
  label,
  variant = 'primary',
  size = 48,
  onClick,
  style,
  disabled
}) {
  const [h, setH] = React.useState(false);
  const pal = {
    primary: ['var(--eq-navy)', 'var(--eq-paper)', 'var(--eq-blue)'],
    accent: ['var(--eq-coral)', 'var(--eq-navy)', 'var(--eq-peach)'],
    secondary: ['transparent', 'var(--eq-navy)', 'var(--eq-gray-100)'],
    inverse: ['var(--eq-paper)', 'var(--eq-navy)', 'var(--eq-coral)']
  }[variant];
  return /*#__PURE__*/React.createElement("button", {
    "aria-label": label,
    title: label,
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      width: size,
      height: size,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: 0,
      border: variant === 'secondary' ? '2px solid var(--eq-navy)' : 'none',
      background: h && !disabled ? pal[2] : pal[0],
      color: pal[1],
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? .4 : 1,
      transition: 'background var(--dur-fast)',
      padding: 0,
      boxSizing: 'border-box',
      ...style
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: Math.round(size * 0.42)
  }));
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
const TONES = {
  navy: ['var(--eq-navy)', 'var(--eq-paper)'],
  coral: ['var(--eq-coral)', 'var(--eq-navy)'],
  teal: ['var(--eq-teal)', 'var(--eq-navy)'],
  yellow: ['var(--eq-yellow)', 'var(--eq-navy)'],
  periwinkle: ['var(--eq-periwinkle)', 'var(--eq-navy)'],
  paper: ['var(--eq-paper)', 'var(--eq-navy)'],
  muted: ['var(--eq-gray-100)', 'var(--eq-navy)']
};
function Tag({
  tone = 'navy',
  shape = 'square',
  outline,
  size = 'md',
  children,
  style
}) {
  const [bg, fg] = TONES[tone] || TONES.navy;
  const s = size === 'lg' ? {
    h: 44,
    px: 22,
    fs: 16
  } : size === 'sm' ? {
    h: 24,
    px: 10,
    fs: 11
  } : {
    h: 30,
    px: 14,
    fs: 13
  };
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      height: s.h,
      padding: '0 ' + s.px + 'px',
      borderRadius: shape === 'pill' ? 999 : 0,
      background: outline ? 'transparent' : bg,
      color: outline ? bg : fg,
      border: outline ? '1.5px solid ' + bg : 'none',
      fontFamily: 'var(--font-sans)',
      fontWeight: 700,
      fontSize: s.fs,
      letterSpacing: '.06em',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      boxSizing: 'border-box',
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/data/BarChart.jsx
try { (() => {
function BarChart({
  data = [],
  color = 'var(--eq-coral)',
  track = 'var(--data-track)',
  labelInside = true,
  barHeight = 40,
  gap = 14,
  max,
  note,
  decimals = 1,
  decimalSep = ',',
  style
}) {
  const m = max || Math.max(...data.map(d => d.value), 1);
  const fmt = v => v.toFixed(decimals).replace('.', decimalSep) + '%';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap
    }
  }, data.map((d, i) => {
    const w = d.value / m * 100;
    const inside = labelInside && w > 55;
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        position: 'relative',
        height: barHeight,
        background: track
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'absolute',
        left: 0,
        top: 0,
        bottom: 0,
        width: w + '%',
        background: d.color || color,
        borderRadius: 0
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: inside ? 'flex-start' : 'flex-end',
        padding: '0 14px',
        fontSize: barHeight * 0.42,
        color: inside ? 'var(--eq-paper)' : 'var(--eq-navy)',
        whiteSpace: 'nowrap'
      }
    }, /*#__PURE__*/React.createElement("b", null, d.label), "\xA0| ", fmt(d.value)));
  })), note && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 14,
      fontSize: 13,
      fontStyle: 'italic',
      color: 'var(--eq-gray-600)',
      textAlign: 'center'
    }
  }, note));
}
Object.assign(__ds_scope, { BarChart });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/BarChart.jsx", error: String((e && e.message) || e) }); }

// components/data/ColumnChart.jsx
try { (() => {
function ColumnChart({
  data = [],
  series = [],
  height = 240,
  max,
  unit = '%',
  style
}) {
  const m = max || Math.max(...data.flatMap(d => d.values), 1);
  const cols = ['var(--data-1)', 'var(--data-2)', 'var(--data-3)', 'var(--data-4)', 'var(--data-5)', 'var(--data-6)'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, series.length > 1 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 18,
      marginBottom: 16,
      fontSize: 13,
      color: 'var(--eq-navy)'
    }
  }, series.map((s, i) => /*#__PURE__*/React.createElement("span", {
    key: s,
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 12,
      height: 12,
      background: cols[i]
    }
  }), s))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      gap: 28,
      height,
      borderBottom: '2px solid var(--eq-navy)'
    }
  }, data.map((d, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      display: 'flex',
      alignItems: 'flex-end',
      gap: 4,
      height: '100%'
    }
  }, d.values.map((v, j) => /*#__PURE__*/React.createElement("div", {
    key: j,
    style: {
      flex: 1,
      height: v / m * 100 + '%',
      background: cols[j],
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: -22,
      left: 0,
      right: 0,
      textAlign: 'center',
      fontSize: 13,
      fontWeight: 700,
      color: 'var(--eq-navy)'
    }
  }, v, unit)))))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 28,
      marginTop: 8
    }
  }, data.map((d, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      textAlign: 'center',
      fontSize: 13,
      color: 'var(--eq-gray-600)'
    }
  }, d.label))));
}
Object.assign(__ds_scope, { ColumnChart });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/ColumnChart.jsx", error: String((e && e.message) || e) }); }

// components/data/StatFigure.jsx
try { (() => {
function StatFigure({
  value,
  label,
  note,
  size = 48,
  tone = 'navy',
  divider,
  style
}) {
  const c = tone === 'inverse' ? 'var(--eq-paper)' : tone === 'coral' ? 'var(--eq-coral)' : 'var(--eq-navy)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      paddingLeft: divider ? 24 : 0,
      borderLeft: divider ? '2px solid ' + (tone === 'inverse' ? 'var(--eq-paper)' : 'var(--eq-navy)') : 'none',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: size,
      fontWeight: 700,
      lineHeight: 1,
      color: c,
      fontVariantNumeric: 'tabular-nums'
    }
  }, value), label && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: Math.max(14, size * 0.33),
      lineHeight: 1.3,
      marginTop: 8,
      color: tone === 'inverse' ? 'var(--eq-paper)' : 'var(--eq-gray-600)'
    }
  }, label), note && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: Math.max(11, size * 0.22),
      marginTop: 4,
      color: tone === 'inverse' ? 'var(--eq-paper)' : 'var(--eq-gray-600)'
    }
  }, note));
}
Object.assign(__ds_scope, { StatFigure });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/StatFigure.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
function Dialog({
  open,
  onClose,
  title,
  children,
  actions,
  width = 520,
  style
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    onClick: onClose,
    style: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(3,15,80,.55)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: 24
    }
  }, /*#__PURE__*/React.createElement("div", {
    role: "dialog",
    "aria-modal": "true",
    onClick: e => e.stopPropagation(),
    style: {
      width: '100%',
      maxWidth: width,
      background: 'var(--eq-paper)',
      fontFamily: 'var(--font-sans)',
      borderTopLeftRadius: 'var(--radius-accent)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: 16,
      padding: '28px 28px 0'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      fontSize: 24,
      fontWeight: 700,
      color: 'var(--eq-navy)',
      lineHeight: 1.2
    }
  }, title), /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Cerrar",
    variant: "secondary",
    size: 36,
    onClick: onClose
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 28px 28px',
      color: 'var(--eq-gray-600)',
      fontSize: 16,
      lineHeight: 1.5
    }
  }, children), actions && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 12,
      justifyContent: 'flex-end',
      padding: '20px 28px',
      borderTop: '2px dotted var(--eq-navy)'
    }
  }, actions)));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function Checkbox({
  label,
  checked,
  defaultChecked,
  onChange,
  disabled,
  name,
  value,
  style
}) {
  const [c, setC] = React.useState(!!defaultChecked);
  const on = checked !== undefined ? checked : c;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      fontFamily: 'var(--font-sans)',
      fontSize: 16,
      color: 'var(--eq-navy)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? .45 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    name: name,
    value: value,
    checked: on,
    disabled: disabled,
    onChange: e => {
      setC(e.target.checked);
      onChange && onChange(e);
    },
    style: {
      position: 'absolute',
      opacity: 0,
      width: 0,
      height: 0
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 20,
      height: 20,
      flex: 'none',
      boxSizing: 'border-box',
      border: '2px solid var(--eq-navy)',
      borderRadius: 0,
      background: on ? 'var(--eq-navy)' : 'var(--eq-white)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, on && /*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "10",
    viewBox: "0 0 12 10"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M1 5l3.5 3.5L11 1",
    fill: "none",
    stroke: "#F7FAF2",
    strokeWidth: "2"
  }))), label);
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const labelStyle = {
  display: 'block',
  fontSize: 13,
  fontWeight: 700,
  color: 'var(--eq-navy)',
  marginBottom: 8,
  letterSpacing: '.02em'
};
const helpStyle = err => ({
  fontSize: 12,
  marginTop: 6,
  color: err ? 'var(--eq-navy)' : 'var(--eq-gray-600)',
  fontWeight: err ? 700 : 400
});
function Input({
  label,
  hint,
  error,
  multiline,
  rows = 4,
  id,
  style,
  ...rest
}) {
  const [f, setF] = React.useState(false);
  const iid = id || React.useId();
  const El = multiline ? 'textarea' : 'input';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("label", {
    htmlFor: iid,
    style: labelStyle
  }, label), /*#__PURE__*/React.createElement(El, _extends({
    id: iid,
    rows: multiline ? rows : undefined
  }, rest, {
    onFocus: e => {
      setF(true);
      rest.onFocus && rest.onFocus(e);
    },
    onBlur: e => {
      setF(false);
      rest.onBlur && rest.onBlur(e);
    },
    style: {
      width: '100%',
      boxSizing: 'border-box',
      height: multiline ? undefined : 48,
      padding: multiline ? '12px 14px' : '0 14px',
      borderRadius: 0,
      border: 'none',
      borderBottom: '2px solid ' + (error ? 'var(--eq-coral)' : f ? 'var(--eq-blue)' : 'var(--eq-navy)'),
      background: 'var(--eq-white)',
      color: 'var(--eq-navy)',
      fontFamily: 'inherit',
      fontSize: 16,
      outline: 'none',
      resize: 'vertical',
      boxShadow: f ? 'inset 0 0 0 1px var(--eq-blue)' : 'inset 0 0 0 1px var(--eq-gray-300)'
    }
  })), (hint || error) && /*#__PURE__*/React.createElement("div", {
    style: helpStyle(error)
  }, error || hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Radio.jsx
try { (() => {
function Radio({
  label,
  checked,
  defaultChecked,
  onChange,
  disabled,
  name,
  value,
  style
}) {
  const [c, setC] = React.useState(!!defaultChecked);
  const on = checked !== undefined ? checked : c;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      fontFamily: 'var(--font-sans)',
      fontSize: 16,
      color: 'var(--eq-navy)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? .45 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "radio",
    name: name,
    value: value,
    checked: on,
    disabled: disabled,
    onChange: e => {
      setC(e.target.checked);
      onChange && onChange(e);
    },
    style: {
      position: 'absolute',
      opacity: 0,
      width: 0,
      height: 0
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 20,
      height: 20,
      flex: 'none',
      boxSizing: 'border-box',
      border: '2px solid var(--eq-navy)',
      borderRadius: '50%',
      background: on ? 'var(--eq-navy)' : 'var(--eq-white)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, on && /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: 'var(--eq-paper)'
    }
  })), label);
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Radio.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
const labelStyle = {
  display: 'block',
  fontSize: 13,
  fontWeight: 700,
  color: 'var(--eq-navy)',
  marginBottom: 8,
  letterSpacing: '.02em'
};
const helpStyle = err => ({
  fontSize: 12,
  marginTop: 6,
  color: err ? 'var(--eq-navy)' : 'var(--eq-gray-600)',
  fontWeight: err ? 700 : 400
});
function Select({
  label,
  hint,
  options = [],
  value,
  onChange,
  placeholder,
  id,
  style,
  disabled
}) {
  const iid = id || React.useId();
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("label", {
    htmlFor: iid,
    style: labelStyle
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("select", {
    id: iid,
    value: value,
    onChange: onChange,
    disabled: disabled,
    style: {
      appearance: 'none',
      width: '100%',
      height: 48,
      padding: '0 44px 0 14px',
      borderRadius: 0,
      border: 'none',
      borderBottom: '2px solid var(--eq-navy)',
      boxShadow: 'inset 0 0 0 1px var(--eq-gray-300)',
      background: 'var(--eq-white)',
      color: 'var(--eq-navy)',
      fontFamily: 'inherit',
      fontSize: 16,
      cursor: 'pointer',
      opacity: disabled ? .5 : 1
    }
  }, placeholder && /*#__PURE__*/React.createElement("option", {
    value: ""
  }, placeholder), options.map(o => typeof o === 'string' ? /*#__PURE__*/React.createElement("option", {
    key: o,
    value: o
  }, o) : /*#__PURE__*/React.createElement("option", {
    key: o.value,
    value: o.value
  }, o.label))), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 18,
    color: "var(--eq-navy)",
    style: {
      position: 'absolute',
      right: 14,
      top: 15,
      pointerEvents: 'none'
    }
  })), hint && /*#__PURE__*/React.createElement("div", {
    style: helpStyle()
  }, hint));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function Switch({
  label,
  checked,
  defaultChecked,
  onChange,
  disabled,
  style
}) {
  const [c, setC] = React.useState(!!defaultChecked);
  const on = checked !== undefined ? checked : c;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      fontFamily: 'var(--font-sans)',
      fontSize: 16,
      color: 'var(--eq-navy)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? .45 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: on,
    disabled: disabled,
    onChange: e => {
      setC(e.target.checked);
      onChange && onChange(e);
    },
    style: {
      position: 'absolute',
      opacity: 0,
      width: 0,
      height: 0
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 44,
      height: 24,
      flex: 'none',
      boxSizing: 'border-box',
      border: '2px solid var(--eq-navy)',
      background: on ? 'var(--eq-navy)' : 'var(--eq-white)',
      position: 'relative',
      transition: 'background var(--dur-fast)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: 2,
      left: on ? 22 : 2,
      width: 16,
      height: 16,
      background: on ? 'var(--eq-coral)' : 'var(--eq-navy)',
      transition: 'left var(--dur-base) var(--ease-out)'
    }
  })), label);
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/media/DuotonePhoto.jsx
try { (() => {
const PAIRS = {
  navy: ['var(--eq-periwinkle)', 'var(--eq-navy)'],
  teal: ['var(--eq-teal)', 'var(--eq-navy)'],
  coral: ['var(--eq-paper)', 'var(--eq-coral)'],
  'coral-navy': ['var(--eq-coral)', 'var(--eq-navy)'],
  blue: ['var(--eq-cyan)', 'var(--eq-navy)']
};
function DuotonePhoto({
  src,
  tone = 'navy',
  texture = 'halftone',
  height = '100%',
  position = 'center',
  radius = 0,
  children,
  style
}) {
  const [light, dark] = PAIRS[tone] || PAIRS.navy;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      overflow: 'hidden',
      isolation: 'isolate',
      background: light,
      height,
      borderRadius: radius,
      ...style
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: "",
    style: {
      position: 'absolute',
      inset: 0,
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      objectPosition: position,
      filter: 'grayscale(1) contrast(1.1)',
      mixBlendMode: 'multiply'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: dark,
      mixBlendMode: 'lighten'
    }
  }), (texture === 'halftone' || texture === 'both') && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      backgroundImage: 'var(--tex-halftone)',
      backgroundSize: 'var(--tex-halftone-size)',
      opacity: .5
    }
  }), (texture === 'grain' || texture === 'both') && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      backgroundImage: 'var(--tex-grain)',
      mixBlendMode: 'multiply',
      opacity: .35
    }
  }), children && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      zIndex: 2,
      height: '100%'
    }
  }, children));
}
Object.assign(__ds_scope, { DuotonePhoto });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/media/DuotonePhoto.jsx", error: String((e && e.message) || e) }); }

// components/navigation/NavBar.jsx
try { (() => {
function NavBar({
  links = [],
  active,
  onNavigate,
  basePath = '',
  cta,
  tone = 'navy',
  style
}) {
  const dark = tone === 'navy';
  return /*#__PURE__*/React.createElement("header", {
    style: {
      background: dark ? 'var(--eq-navy)' : 'var(--eq-paper)',
      borderBottom: dark ? 'none' : '1px solid var(--eq-gray-300)',
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      height: 76,
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 24,
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    onClick: e => {
      e.preventDefault();
      onNavigate && onNavigate(links[0]);
    },
    style: {
      display: 'flex'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: basePath + 'assets/logos/logo-principal-' + (dark ? 'blanco' : 'azul') + '.svg',
    alt: "Equilibrium",
    style: {
      height: 30
    }
  })), /*#__PURE__*/React.createElement("nav", {
    style: {
      marginLeft: 'auto',
      display: 'flex',
      gap: 36,
      flexWrap: 'wrap'
    }
  }, links.map(l => {
    const on = l === active;
    return /*#__PURE__*/React.createElement("a", {
      key: l,
      href: "#",
      onClick: e => {
        e.preventDefault();
        onNavigate && onNavigate(l);
      },
      style: {
        color: dark ? 'var(--eq-paper)' : 'var(--eq-navy)',
        textDecoration: 'none',
        fontSize: 15,
        fontWeight: on ? 700 : 400,
        paddingBottom: 4,
        borderBottom: '2px solid ' + (on ? 'var(--eq-coral)' : 'transparent')
      }
    }, l);
  })), cta));
}
Object.assign(__ds_scope, { NavBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/NavBar.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function Tabs({
  tabs = [],
  value,
  onChange,
  style
}) {
  const [v, setV] = React.useState(value || tabs[0]);
  const cur = value !== undefined ? value : v;
  return /*#__PURE__*/React.createElement("div", {
    role: "tablist",
    style: {
      display: 'flex',
      gap: 0,
      borderBottom: '2px solid var(--eq-navy)',
      fontFamily: 'var(--font-sans)',
      ...style
    }
  }, tabs.map(t => {
    const on = t === cur;
    return /*#__PURE__*/React.createElement("button", {
      key: t,
      role: "tab",
      "aria-selected": on,
      onClick: () => {
        setV(t);
        onChange && onChange(t);
      },
      style: {
        border: 'none',
        borderRadius: 0,
        cursor: 'pointer',
        padding: '12px 22px',
        background: on ? 'var(--eq-navy)' : 'transparent',
        color: on ? 'var(--eq-paper)' : 'var(--eq-navy)',
        fontFamily: 'inherit',
        fontSize: 15,
        fontWeight: 700
      }
    }, t);
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// slides/fit.js
try { (() => {
(function () {
  function fit() {
    var s = document.querySelector('.stage');
    if (!s) return;
    var k = Math.min(innerWidth / 1920, innerHeight / 1080);
    s.style.transform = 'translate(-50%,-50%) scale(' + k + ')';
  }
  addEventListener('resize', fit);
  addEventListener('DOMContentLoaded', fit);
  fit();
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "slides/fit.js", error: String((e && e.message) || e) }); }

// ui_kits/website/About.jsx
try { (() => {
const {
  StatFigure,
  Quote,
  Tag
} = window.EquilibriumDesignSystem_83a4c4;
function About() {
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("section", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '80px 24px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))',
      gap: 56
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "eq-kicker"
  }, "Nosotros"), /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'clamp(36px,4vw,52px)',
      marginTop: 12
    }
  }, "Investigaci\xF3n social y empresarial en Am\xE9rica Latina y el Caribe")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 18,
      fontSize: 18
    }
  }, /*#__PURE__*/React.createElement("p", null, "Observamos la realidad a partir de la evidencia, investigamos para comprender el contexto y transformamos ese conocimiento en servicios, metodolog\xEDas y herramientas adaptadas a cada desaf\xEDo."), /*#__PURE__*/React.createElement("p", null, "Trabajamos con empresas, organismos multilaterales, ONG y gobiernos."))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: 'var(--eq-coral)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '72px 24px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))',
      gap: 40,
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 36
    }
  }, "Somos el Sabio que explora el terreno para crear soluciones."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      flexWrap: 'wrap'
    }
  }, ['Rigurosa', 'Ágil', 'Experta', 'Empática', 'Innovadora'].map((t, i) => /*#__PURE__*/React.createElement(Tag, {
    key: t,
    tone: "navy",
    shape: i === 2 ? 'pill' : 'square',
    size: "lg"
  }, t))))));
}
window.About = About;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/About.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Contact.jsx
try { (() => {
const {
  Input,
  Select,
  Checkbox,
  Radio,
  Button,
  DuotonePhoto
} = window.EquilibriumDesignSystem_83a4c4;
function Contact() {
  const [done, setDone] = React.useState(false);
  return /*#__PURE__*/React.createElement("section", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(340px,1fr))',
      minHeight: 640
    }
  }, /*#__PURE__*/React.createElement(DuotonePhoto, {
    src: "../../assets/photos/web-hero-team.png",
    tone: "navy",
    texture: "both",
    position: "40% 30%",
    style: {
      minHeight: 360
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 'max(32px,5vw)',
      height: '100%',
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'flex-end',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "eq-kicker",
    style: {
      color: 'var(--eq-coral)'
    }
  }, "Contacto"), /*#__PURE__*/React.createElement("h1", {
    style: {
      color: 'var(--eq-paper)',
      fontSize: 'clamp(34px,3.6vw,48px)'
    }
  }, "Cu\xE9ntanos qu\xE9 decisi\xF3n necesitas tomar."), /*#__PURE__*/React.createElement("p", {
    style: {
      color: 'var(--eq-paper)',
      fontSize: 17,
      maxWidth: 440
    }
  }, "Respondemos en un plazo de dos d\xEDas h\xE1biles con una primera propuesta de enfoque."))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 'max(32px,5vw)',
      background: 'var(--eq-paper)'
    }
  }, done ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
      maxWidth: 480
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 32
    }
  }, "Gracias. Recibimos tu mensaje."), /*#__PURE__*/React.createElement("p", null, "Un especialista de nuestro equipo te escribir\xE1 pronto."), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    onClick: () => setDone(false)
  }, "Enviar otro mensaje"))) : /*#__PURE__*/React.createElement("form", {
    onSubmit: e => {
      e.preventDefault();
      setDone(true);
    },
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 22,
      maxWidth: 520
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Input, {
    label: "Nombre",
    required: true
  }), /*#__PURE__*/React.createElement(Input, {
    label: "Organizaci\xF3n"
  })), /*#__PURE__*/React.createElement(Input, {
    label: "Correo institucional",
    type: "email",
    required: true,
    placeholder: "nombre@organizacion.org"
  }), /*#__PURE__*/React.createElement(Select, {
    label: "Pa\xEDs",
    placeholder: "Selecciona",
    options: ['Perú', 'Colombia', 'Ecuador', 'Venezuela', 'Chile', 'Otro']
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 700,
      color: 'var(--eq-navy)',
      marginBottom: 10
    }
  }, "Tipo de organizaci\xF3n"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 20,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement(Radio, {
    name: "org",
    label: "Empresa",
    defaultChecked: true
  }), /*#__PURE__*/React.createElement(Radio, {
    name: "org",
    label: "ONG / cooperaci\xF3n"
  }), /*#__PURE__*/React.createElement(Radio, {
    name: "org",
    label: "Gobierno"
  }))), /*#__PURE__*/React.createElement(Input, {
    label: "\xBFQu\xE9 necesitas resolver?",
    multiline: true,
    rows: 4
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Acepto el tratamiento de mis datos personales"
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Button, {
    type: "submit",
    iconRight: "arrow-right"
  }, "Enviar mensaje")))));
}
window.Contact = Contact;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Contact.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Footer.jsx
try { (() => {
const {
  Logo,
  Icon
} = window.EquilibriumDesignSystem_83a4c4;
function Footer({
  go
}) {
  const col = {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    fontSize: 15
  };
  const a = {
    color: 'var(--eq-paper)',
    textDecoration: 'none',
    cursor: 'pointer'
  };
  return /*#__PURE__*/React.createElement("footer", {
    style: {
      background: 'var(--eq-navy)',
      color: 'var(--eq-paper)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '64px 24px 40px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))',
      gap: 40
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: col
  }, /*#__PURE__*/React.createElement(Logo, {
    variant: "tagline",
    color: "blanco",
    height: 40,
    basePath: "../../"
  })), /*#__PURE__*/React.createElement("div", {
    style: col
  }, /*#__PURE__*/React.createElement("b", null, "Navegaci\xF3n"), ['Inicio', 'Nosotros', 'Servicios', 'Reportes', 'Contacto'].map(l => /*#__PURE__*/React.createElement("a", {
    key: l,
    style: a,
    onClick: () => go(l)
  }, l))), /*#__PURE__*/React.createElement("div", {
    style: col
  }, /*#__PURE__*/React.createElement("b", null, "Contacto"), /*#__PURE__*/React.createElement("span", null, "contacto@equilibriumbdc.com"), /*#__PURE__*/React.createElement("span", null, "Lima \xB7 Bogot\xE1 \xB7 Quito")), /*#__PURE__*/React.createElement("div", {
    style: col
  }, /*#__PURE__*/React.createElement("b", null, "S\xEDguenos"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 14
    }
  }, ['linkedin', 'instagram', 'twitter'].map(n => /*#__PURE__*/React.createElement(Icon, {
    key: n,
    name: n,
    size: 22
  }))), /*#__PURE__*/React.createElement("span", null, "@equilibriumbdc"))), /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '20px 24px 32px',
      borderTop: '1px solid rgba(247,250,242,.25)',
      fontSize: 13
    }
  }, "\xA9 2026 Equilibrium | Business, Data & Communities"));
}
window.Footer = Footer;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Footer.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Home.jsx
try { (() => {
const {
  Button,
  Tag,
  Card,
  StatFigure,
  DuotonePhoto,
  BarChart,
  Isotipo
} = window.EquilibriumDesignSystem_83a4c4;
const B = '../../';
function Hero({
  go
}) {
  return /*#__PURE__*/React.createElement("section", null, /*#__PURE__*/React.createElement("div", {
    style: {
      height: 520,
      background: 'var(--eq-gray-100) center 30%/cover url(' + B + 'assets/photos/web-hero-team.png)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--eq-teal)',
      padding: '72px max(24px,8vw) 72px max(24px,calc((100vw - 1200px)/2 + 24px))'
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'clamp(30px,3.4vw,44px)',
      fontWeight: 500,
      lineHeight: 1.2,
      color: 'var(--eq-navy)',
      maxWidth: 560
    }
  }, "Somos especialistas en consultor\xEDa estrat\xE9gica para optimizar decisiones y potenciar resultados.")), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--eq-paper)',
      padding: '72px max(24px,6vw)',
      display: 'flex',
      flexDirection: 'column',
      gap: 24,
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 18,
      color: 'var(--eq-navy)',
      lineHeight: 1.6,
      maxWidth: 520
    }
  }, "Realizamos diferentes estudios de mercado siendo aliados de nuestros clientes para la toma de decisiones."), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 18,
      color: 'var(--eq-navy)',
      lineHeight: 1.6,
      maxWidth: 520
    }
  }, "Contamos con acceso interno y externo a diversas bases de datos, p\xFAblicas y privadas, de mayor representatividad en el mercado."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 12,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    iconRight: "arrow-right",
    onClick: () => go('Contacto')
  }, "Conversemos"), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    onClick: () => go('Servicios')
  }, "Ver servicios")))));
}
function Figures() {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      background: 'var(--eq-navy)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '72px 24px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))',
      gap: 32
    }
  }, /*#__PURE__*/React.createElement(StatFigure, {
    tone: "inverse",
    value: "+15",
    label: "pa\xEDses de Am\xE9rica Latina y el Caribe con trabajo de campo"
  }), /*#__PURE__*/React.createElement(StatFigure, {
    tone: "inverse",
    divider: true,
    value: "4",
    label: "l\xEDneas de servicio: mercado, impacto, comunidades y datos"
  }), /*#__PURE__*/React.createElement(StatFigure, {
    tone: "inverse",
    divider: true,
    value: "2025",
    label: "reportes regionales publicados con metodolog\xEDa abierta"
  })));
}
function Featured({
  go
}) {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '96px 24px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))',
      gap: 56,
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 20
    }
  }, /*#__PURE__*/React.createElement(Tag, {
    tone: "coral"
  }, "Reporte \xB7 Narrativas"), /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 'clamp(30px,3vw,40px)'
    }
  }, "\xBFCu\xE1l es el panorama del consumo de informaci\xF3n en Venezuela?"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 17
    }
  }, "Un estudio mixto con j\xF3venes de 18 a 29 a\xF1os sobre las fuentes en las que conf\xEDan, los formatos que prefieren y c\xF3mo verifican lo que leen."), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Button, {
    variant: "accent",
    iconRight: "arrow-right",
    onClick: () => go('Reportes')
  }, "Leer el reporte"))), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--eq-white)',
      padding: 32,
      boxShadow: 'inset 0 0 0 1px var(--eq-gray-100)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      fontWeight: 700,
      color: 'var(--eq-navy)',
      marginBottom: 20
    }
  }, "Principal fuente de informaci\xF3n (%)"), /*#__PURE__*/React.createElement(BarChart, {
    barHeight: 34,
    gap: 10,
    note: "n = 1.200 encuestas \xB7 Equilibrium, 2025",
    data: [{
      label: 'Redes sociales',
      value: 64.2
    }, {
      label: 'Mensajería',
      value: 18.4
    }, {
      label: 'TV',
      value: 9.1
    }, {
      label: 'Radio',
      value: 5.3
    }, {
      label: 'Prensa',
      value: 3.0
    }]
  })));
}
function CTA({
  go
}) {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      position: 'relative',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'var(--grad-navy)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      backgroundImage: 'var(--tex-grain)',
      mixBlendMode: 'multiply',
      opacity: .4
    }
  }), /*#__PURE__*/React.createElement(Isotipo, {
    size: 560,
    color: "var(--eq-coral)",
    style: {
      position: 'absolute',
      right: -260,
      top: -220
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      maxWidth: 1200,
      margin: '0 auto',
      padding: '96px 24px',
      display: 'flex',
      flexDirection: 'column',
      gap: 24,
      alignItems: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "eq-kicker",
    style: {
      color: 'var(--eq-coral)'
    }
  }, "Principio rector"), /*#__PURE__*/React.createElement("h2", {
    style: {
      color: 'var(--eq-paper)',
      fontSize: 'clamp(34px,4vw,56px)',
      maxWidth: 760
    }
  }, "Comprendemos antes de recomendar."), /*#__PURE__*/React.createElement(Button, {
    variant: "inverse",
    iconRight: "arrow-right",
    onClick: () => go('Contacto')
  }, "Cu\xE9ntanos tu desaf\xEDo")));
}
function Home({
  go
}) {
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Hero, {
    go: go
  }), /*#__PURE__*/React.createElement(Figures, null), /*#__PURE__*/React.createElement(Featured, {
    go: go
  }), /*#__PURE__*/React.createElement(CTA, {
    go: go
  }));
}
window.Home = Home;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Home.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Reports.jsx
try { (() => {
const {
  Tabs,
  Card,
  Tag,
  Button,
  Dialog,
  Input,
  Checkbox
} = window.EquilibriumDesignSystem_83a4c4;
const REPORTS = [{
  type: 'Reportes',
  t: '¿Cuál es el panorama del consumo de información en Venezuela?',
  d: 'Septiembre 2026',
  img: 'duotone-navy',
  tone: 'navy'
}, {
  type: 'Reportes',
  t: 'Migración de los medios digitales',
  d: 'Julio 2026',
  img: 'duotone-teal',
  tone: 'teal'
}, {
  type: 'Webinars',
  t: 'Muestreo RDS en poblaciones de difícil acceso',
  d: 'Junio 2026',
  img: 'duotone-periwinkle',
  tone: 'periwinkle'
}, {
  type: 'Proyectos',
  t: 'Global Gateway Ecuador: sesiones creativas',
  d: 'Mayo 2026',
  img: 'duotone-yellow',
  tone: 'yellow'
}, {
  type: 'Reportes',
  t: 'Juventudes en LAC: optimismo frente a la precariedad',
  d: 'Abril 2026',
  img: 'duotone-coral',
  tone: 'coral'
}, {
  type: 'Webinars',
  t: 'Ética y protección de datos en trabajo de campo',
  d: 'Marzo 2026',
  img: 'duotone-blue',
  tone: 'navy'
}];
function Reports() {
  const [f, setF] = React.useState('Todos');
  const [open, setOpen] = React.useState(null);
  const [sent, setSent] = React.useState(false);
  const list = REPORTS.filter(r => f === 'Todos' || r.type === f);
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("section", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '80px 24px 32px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "eq-kicker"
  }, "Conocimiento"), /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'clamp(36px,4vw,52px)',
      marginTop: 12
    }
  }, "Reportes y recursos"), /*#__PURE__*/React.createElement(Tabs, {
    tabs: ['Todos', 'Reportes', 'Webinars', 'Proyectos'],
    value: f,
    onChange: setF,
    style: {
      marginTop: 32
    }
  })), /*#__PURE__*/React.createElement("section", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '0 24px 96px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))',
      gap: 20
    }
  }, list.map(r => /*#__PURE__*/React.createElement(Card, {
    key: r.t,
    tone: "white",
    image: '../../assets/photos/' + r.img + '.png',
    imageHeight: 180,
    title: r.t,
    onClick: () => {
      setOpen(r);
      setSent(false);
    },
    kicker: r.d,
    footer: /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }
    }, /*#__PURE__*/React.createElement(Tag, {
      tone: r.tone,
      size: "sm"
    }, r.type), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      size: "sm",
      iconRight: "arrow-right"
    }, "Ver"))
  }))), /*#__PURE__*/React.createElement(Dialog, {
    open: !!open,
    onClose: () => setOpen(null),
    title: sent ? 'Listo. Revisa tu correo.' : 'Descargar: ' + (open ? open.t : ''),
    actions: sent ? /*#__PURE__*/React.createElement(Button, {
      onClick: () => setOpen(null)
    }, "Cerrar") : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      size: "sm",
      onClick: () => setOpen(null)
    }, "Cancelar"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      iconRight: "download",
      onClick: () => setSent(true)
    }, "Enviar PDF"))
  }, sent ? 'Te enviamos el reporte completo y su ficha metodológica.' : /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Input, {
    label: "Correo institucional",
    placeholder: "nombre@organizacion.org"
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Quiero recibir nuevos reportes",
    defaultChecked: true
  }))));
}
window.Reports = Reports;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Reports.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Services.jsx
try { (() => {
const {
  Card,
  Button,
  NumberedList,
  Tag
} = window.EquilibriumDesignSystem_83a4c4;
const SERVICES = [{
  tone: 'teal',
  k: 'Business',
  t: 'Estudios de mercado',
  b: 'Segmentación, hábitos de consumo y evaluación de marca para decisiones de inversión en LAC.',
  img: 'duotone-teal'
}, {
  tone: 'navy',
  k: 'Data',
  t: 'Evaluación de impacto',
  b: 'Líneas de base, RCT y monitoreo para programas de cooperación y política pública.',
  img: 'duotone-navy'
}, {
  tone: 'coral',
  k: 'Communities',
  t: 'Relacionamiento comunitario',
  b: 'Diagnósticos territoriales y escucha activa con poblaciones en contextos complejos.',
  img: 'duotone-coral'
}, {
  tone: 'white',
  k: 'Data',
  t: 'Analítica y visualización',
  b: 'Tableros, modelos y reportes ejecutivos que convierten evidencia en decisiones.',
  img: 'duotone-periwinkle'
}];
function Services({
  go
}) {
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("section", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '80px 24px 40px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "eq-kicker"
  }, "Servicios"), /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'clamp(36px,4vw,52px)',
      marginTop: 12,
      maxWidth: 800
    }
  }, "Evidencia rigurosa, adaptada a cada desaf\xEDo")), /*#__PURE__*/React.createElement("section", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '0 24px 80px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))',
      gap: 20
    }
  }, SERVICES.map((s, i) => /*#__PURE__*/React.createElement(Card, {
    key: s.t,
    tone: s.tone,
    kicker: s.k,
    title: s.t,
    image: '../../assets/photos/' + s.img + '.png',
    imageHeight: 150,
    accentCorner: i === 1 ? 'top-right' : undefined,
    onClick: () => go('Contacto'),
    footer: /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: s.tone === 'navy' ? 'inverse' : 'ghost',
      iconRight: "arrow-right"
    }, "Solicitar propuesta")
  }, s.b))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: 'var(--eq-white)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '80px 24px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))',
      gap: 48
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "eq-kicker"
  }, "C\xF3mo trabajamos"), /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 36,
      marginTop: 12
    }
  }, "Primero comprendemos; luego estructuramos, dise\xF1amos y comunicamos.")), /*#__PURE__*/React.createElement(NumberedList, {
    items: [{
      title: 'Diagnóstico',
      body: 'entendemos el contexto y la pregunta de decisión.'
    }, {
      title: 'Diseño metodológico',
      body: 'muestra, instrumentos y protocolo ético.'
    }, {
      title: 'Trabajo de campo',
      body: 'equipos locales en cada territorio.'
    }, {
      title: 'Análisis y recomendaciones',
      body: 'hallazgos aplicables, no solo datos.'
    }]
  }))));
}
window.Services = Services;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Services.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Isotipo = __ds_scope.Isotipo;

__ds_ns.Logo = __ds_scope.Logo;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.NumberedList = __ds_scope.NumberedList;

__ds_ns.Quote = __ds_scope.Quote;

__ds_ns.SectionHeader = __ds_scope.SectionHeader;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.BarChart = __ds_scope.BarChart;

__ds_ns.ColumnChart = __ds_scope.ColumnChart;

__ds_ns.StatFigure = __ds_scope.StatFigure;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.DuotonePhoto = __ds_scope.DuotonePhoto;

__ds_ns.NavBar = __ds_scope.NavBar;

__ds_ns.Tabs = __ds_scope.Tabs;

})();
