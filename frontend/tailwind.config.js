/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0d0d14",
        surface: "#12121e",
        card: "#1a1a2e",
        border: "#2a2a42",
        accent: "#7c3aed",
        "accent-hover": "#6d28d9",
        "accent-soft": "#7c3aed33",
        cyan: "#06b6d4",
        muted: "#64748b",
        "text-primary": "#e2e8f0",
        "text-secondary": "#94a3b8",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
      },
    },
  },
  plugins: [],
}