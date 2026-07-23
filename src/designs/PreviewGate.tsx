import {useEffect, useState} from "react";
import type {ReactNode} from "react";
import {Navigate, useParams} from "react-router";
import {isValidDesignPreviewToken} from "./previewConfig";

interface PreviewGateProps {
  children: ReactNode;
}

function PreviewGate({children}: PreviewGateProps) {
  const {previewToken = ""} = useParams();
  const [isAllowed, setIsAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;

    void isValidDesignPreviewToken(previewToken).then((isValid) => {
      if (active) setIsAllowed(isValid);
    });

    return () => {
      active = false;
    };
  }, [previewToken]);

  if (isAllowed === null) return null;
  if (!isAllowed) return <Navigate to="/" replace />;
  return children;
}

export default PreviewGate;
