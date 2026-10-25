import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#080A0F",
        surface: "#10141E",
        elevated: "#171D2B",
        gold: {
          300: "#F3DFA2",
          400: "#E5C07B",
          500: "#D4AF37",
          600: "#B89428",
        },
        titanium: "#94A3B8",
      },
    },
  },
  plugins: [],
};
export default config;
