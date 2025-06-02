import {useTheme} from "@/hooks/useTheme";
import {Moon, Sun} from "lucide-react";
import {
  motion,
  AnimatePresence,
  useReducedMotion,
  type Variants,
} from "framer-motion";

const DarkModeToggle = () => {
  const {theme, toggleTheme} = useTheme();
  const prefersReducedMotion = useReducedMotion();

  const themeButtonLabel =
    theme === "light" ? "toggle_theme_dark" : "toggle_theme_light";

  const themeIconSwitchVariants: Variants = prefersReducedMotion
    ? {}
    : {
        enter: (direction: number) => ({
          y: direction > 0 ? 10 : -10,
          x: direction > 0 ? -10 : 10,
          opacity: 0,
          scale: 0.7,
          rotateZ: direction * -90,
        }),
        center: {
          zIndex: 1,
          y: 0,
          x: 0,
          opacity: 1,
          scale: 1,
          rotateZ: 0,
          transition: {
            duration: 0.35,
            ease: [0.215, 0.61, 0.355, 1.0],
          },
        },
        exit: (direction: number) => ({
          zIndex: 0,
          y: direction > 0 ? -10 : 10,
          x: direction > 0 ? 10 : -10,
          opacity: 0,
          scale: 0.7,
          rotateZ: direction * 90,
          transition: {
            duration: 0.3,
            ease: [0.55, 0.055, 0.675, 0.19],
          },
        }),
      };

  const iconWrapperHoverVariants = prefersReducedMotion
    ? undefined
    : {
        rest: {scale: 1},
        hover: {
          scale: 1.15,
          transition: {type: "spring", stiffness: 400, damping: 10},
        },
      };

  const themeChangeDirection = theme === "light" ? 1 : -1;

  return (
    <div className="flex items-center space-x-1 sm:space-x-2">
      <motion.div
        variants={iconWrapperHoverVariants}
        initial="rest"
        whileHover="hover"
      >
        <button
          onClick={toggleTheme}
          aria-label={themeButtonLabel}
          title={themeButtonLabel}
          className="relative overflow-hidden flex items-center justify-center text-primary w-8 h-8 sm:w-9 sm:h-9 transition-colors-only hover:text-accent" // CAMBIADO a transition-colors-only
        >
          <AnimatePresence
            mode="wait"
            initial={false}
            custom={themeChangeDirection}
          >
            {theme === "light" ? (
              <motion.div
                key="moon"
                custom={themeChangeDirection}
                variants={themeIconSwitchVariants}
                initial="enter"
                animate="center"
                exit="exit"
                className="absolute flex items-center justify-center"
              >
                <Moon className="h-5 w-5" />
              </motion.div>
            ) : (
              <motion.div
                key="sun"
                custom={themeChangeDirection * -1}
                variants={themeIconSwitchVariants}
                initial="enter"
                animate="center"
                exit="exit"
                className="absolute flex items-center justify-center"
              >
                <Sun className="h-5 w-5" />
              </motion.div>
            )}
          </AnimatePresence>
        </button>
      </motion.div>
    </div>
  );
};

export default DarkModeToggle