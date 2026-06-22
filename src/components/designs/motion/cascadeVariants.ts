import type {Variants} from "framer-motion";

export const cascadeItemVariants: Variants = {
  hidden: {opacity: 0, y: 18, scale: 0.98},
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {type: "spring", stiffness: 100, damping: 20},
  },
};
