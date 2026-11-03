/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Syne'", "sans-serif"],
        body: ["'DM Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        surface: {
          0: "#080c10",
          1: "#0d1117",
          2: "#131920",
          3: "#1a2332",
          4: "#1f2d3d",
        },
        accent: {
          green: "#00e87a",
          yellow: "#ffd166",
          red: "#ff4757",
          blue: "#4fc3f7",
          purple: "#9c6bff",
        },
        border: "rgba(255,255,255,0.08)",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
        "glass-card":
          "linear-gradient(135deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.02) 100%)",
      },
      backgroundSize: {
        "grid-pattern": "40px 40px",
      },
      boxShadow: {
        glass: "0 0 0 1px rgba(255,255,255,0.08), 0 8px 32px rgba(0,0,0,0.4)",
        "glow-green": "0 0 20px rgba(0,232,122,0.25)",
        "glow-yellow": "0 0 20px rgba(255,209,102,0.25)",
        "glow-red": "0 0 20px rgba(255,71,87,0.25)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        shimmer: "shimmer 2s linear infinite",
        "slide-up": "slideUp 0.4s ease-out",
        float: "float 3s ease-in-out infinite",
      },
      keyframes: {
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        slideUp: {
          "0%": { opacity: 0, transform: "translateY(16px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
    },
  },
  plugins: [],
};
