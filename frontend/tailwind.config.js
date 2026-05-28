/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#E8621A",
          dark: "#C4511A",
          light: "#F59240",
          pale: "#FAC066",
        },
        surface: {
          DEFAULT: "#F3F3F3",
          raised: "#FFFFFF",
          border: "#E0E0E0",
        },
        "ink": "#1A1A1A",
        "ink-mid": "#4A4A4A",
        "ink-muted": "#888888",
        accent: {
          DEFAULT: "#E8621A",
          muted: "#C4511A",
        },
        danger: "#C4511A",
        success: "#6B9E45",
        warning: "#F5A623",
      },
      fontFamily: {
        sans: ["'Segoe UI'", "Tahoma", "Geneva", "Verdana", "sans-serif"],
        display: ["'Segoe UI'", "Tahoma", "Geneva", "Verdana", "sans-serif"],
      },
      borderRadius: {
        card: "6px",
      },
      boxShadow: {
        card: "0 1px 4px rgba(0, 0, 0, 0.10)",
      },
    },
  },
  plugins: [],
};
