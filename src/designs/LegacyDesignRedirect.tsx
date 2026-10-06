import {Navigate, useLocation} from "react-router";
import {stripDesignPrefix} from "./designRoutes";

function LegacyDesignRedirect() {
  const {pathname, search, hash} = useLocation();
  return <Navigate to={`${stripDesignPrefix(pathname)}${search}${hash}`} replace />;
}

export default LegacyDesignRedirect;
