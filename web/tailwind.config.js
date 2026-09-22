import daisyui from "daisyui";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  daisyui: {
    themes: ["light", "dark"],
  },
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        navy: "#111b2e",
        mint: "#9ee7d2",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(25, 40, 68, .07)",
      },
    },
  },
  plugins: [daisyui],
};
