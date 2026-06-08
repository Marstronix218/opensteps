import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#13211a",
        paper: "#f4f1e8",
        signal: "#d2ff3e",
        rust: "#c55732",
        line: "#c9c5b8",
      },
    },
  },
  plugins: [],
} satisfies Config;

