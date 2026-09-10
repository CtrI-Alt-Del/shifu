import { useContext } from "react";

import { RestError } from "@/rest/errors/rest-error";
import { RestContext } from "@/ui/shared/contexts/rest-context";

export function useRestContext() {
  const context = useContext(RestContext);

  if (!context) {
    throw new RestError(
      "useRestContext must be used inside RestContextProvider",
      0,
    );
  }

  return context;
}
