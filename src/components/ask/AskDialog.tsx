import {Dialog, Modal, ModalOverlay} from "react-aria-components";
import useMediaQuery from "@/hooks/useMediaQuery";
import {useAskViewportHeight} from "@/hooks/useAskViewportHeight";
import AskPanel from "./AskPanel";

interface AskDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

/**
 * Command palette on desktop, full-screen search sheet on phones. react-aria handles Escape, the focus
 * trap, background scroll locking, and returning focus to whatever opened the dialog.
 */
function AskDialog({isOpen, onOpenChange}: AskDialogProps) {
  const isNarrow = useMediaQuery("(max-width: 700px)");
  // Size the phone sheet to the visible viewport so the list scrolls above the on-screen keyboard.
  const viewportHeight = useAskViewportHeight(isOpen && isNarrow);

  return (
    // Portals render under document.body, so the overlay carries the Hardwood token scope itself.
    // bg needs ! because .design-hardwood sets an unlayered page background.
    <ModalOverlay
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDismissable
      className="design-hardwood fixed inset-0 z-[140] flex items-start justify-center bg-[rgb(10_8_4/58%)]! pt-16 font-hw-display text-hw-ink backdrop-blur-[2px] data-entering:animate-hw-fade-in data-exiting:animate-hw-fade-out max-[700px]:items-stretch max-[700px]:bg-hw-surface! max-[700px]:p-0 max-[700px]:backdrop-blur-none motion-reduce:data-entering:animate-none motion-reduce:data-exiting:animate-none"
    >
      <Modal
        className="flex max-h-[calc(100dvh-128px)] w-[min(760px,92vw)] flex-col overflow-hidden rounded-[14px] bg-hw-surface shadow-hw-card-hover data-entering:animate-hw-pop-in max-[700px]:fixed max-[700px]:inset-x-0 max-[700px]:top-0 max-[700px]:max-h-none max-[700px]:w-full max-[700px]:rounded-none max-[700px]:shadow-none motion-reduce:data-entering:animate-none"
        style={isNarrow ? {height: viewportHeight ?? "100dvh"} : undefined}
      >
        <Dialog aria-label="Ask" className="flex min-h-0 flex-1 flex-col outline-none">
          {({close}) => <AskPanel onClose={close} />}
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}

export default AskDialog;
