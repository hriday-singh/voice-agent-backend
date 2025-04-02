/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        // Main color scheme from caw.tech
        border: "#e7e2d3",
        background: "#f2efe3",
        foreground: "#140d0c",
        primary: {
          DEFAULT: "#140d0c", // Dark Brown (main text color)
          light: "#f2efe3", // Light Cream (background color)
          foreground: "#f2efe3", // Light Cream (text on primary)
        },
        secondary: {
          DEFAULT: "#e7e2d3", // Light Gray/Cream
          foreground: "#140d0c", // Dark Brown (text on secondary)
        },
        accent: {
          yellow: "#ffcc33", // Yellow star/accent color
          red: "#c8364a", // Red accent
          blue: "#3c50bc", // Blue accent
          teal: "#7ea6b0", // Teal accent
          DEFAULT: "#ffcc33", // Default accent (yellow)
          foreground: "#140d0c", // Text on accent
        },
        destructive: {
          DEFAULT: "#c8364a", // Red accent
          foreground: "#f2efe3", // Light Cream (text on destructive)
        },
        muted: {
          DEFAULT: "#e7e2d3", // Light Gray/Cream
          foreground: "#6c6c6c", // Gray text
        },
        neutral: {
          50: "#f2efe3",
          100: "#e7e2d3",
          200: "#d5ceb5",
          300: "#c4b998",
          400: "#b2a47a",
          800: "#382e1e",
          900: "#140d0c",
        },
        card: {
          DEFAULT: "#ffffff",
          foreground: "#140d0c",
        },
        popover: {
          DEFAULT: "#ffffff",
          foreground: "#140d0c",
        },
        input: "#e7e2d3",
        ring: "#ffcc33",
      },
      fontFamily: {
        sans: ["var(--font-wix)", "Work Sans", "system-ui", "sans-serif"],
        display: ["var(--font-wix)", "Work Sans", "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        md: "0.375rem",
        sm: "0.25rem",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
