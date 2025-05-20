import React, {useState, useEffect} from "react";
import {setItem, getItem} from "@/helpers/helpers.jsx";


function DarkModeToggle() {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const item = getItem("isDarkMode");
    return item === undefined ? false : item;
  });

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
  };

  useEffect(() => {
    if (isDarkMode) {
      document.body.classList.add("dark");
    } else {
      document.body.classList.remove("dark");
    }

    setItem("isDarkMode", isDarkMode);
  }, [isDarkMode]);

  return (
    <div className="flex justify-center pt-2">
      <button
        onClick={toggleDarkMode}
        className="px-4 py-2 rounded bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white"
      >
        Toggle {isDarkMode ? "Light" : "Dark"} Mode 🏀
      </button>
    </div>
  );
}

export default DarkModeToggle;
