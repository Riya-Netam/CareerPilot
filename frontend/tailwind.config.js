/** Brand: CareerPilot AI. Navigation / flight-deck palette, kept restrained. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F2F5F7",
        ink: { DEFAULT: "#10243A", soft: "#44586B", faint: "#6B7D8E" },
        line: "#D5DEE5",
        signal: { DEFAULT: "#E39B1B", dark: "#9A6205", tint: "#FCEFD6" },
        teal: { DEFAULT: "#1B7A8C", dark: "#135A68", tint: "#DDF0F3" },
        clay: { DEFAULT: "#B3472F", tint: "#F8E4DE" },
      },
      fontFamily: { sans: ['"Figtree Variable"', "system-ui", "sans-serif"] },
      borderRadius: { card: "10px" },
    },
  },
  plugins: [],
};
