// src/providers/ThemeProvider.tsx
import {useState, useEffect, type ReactNode} from "react";
import { ThemeContext, type Theme } from "@/context/ThemeContext";

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({children}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => {
    let initialTheme: Theme = "light"; // Fallback
    if (typeof window !== "undefined") {
      const storedTheme = localStorage.getItem("theme") as Theme | null;
      if (storedTheme) {
        initialTheme = storedTheme;
      } else {
        if (window.matchMedia?.("(prefers-color-scheme: dark)")?.matches) {
          initialTheme = "dark";
        }
      }
    }
    return initialTheme;
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      const root = window.document.documentElement;
      root.classList.remove("dark", "light");
      if (theme === "dark") {
        root.classList.add("dark");
      } else {
        root.classList.add("light");
      }
      localStorage.setItem("theme", theme);
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === "light" ? "dark" : "light"));
  };

  return (
    <ThemeContext.Provider value={{theme, toggleTheme}}>
      {children}
    </ThemeContext.Provider>
  );
}
