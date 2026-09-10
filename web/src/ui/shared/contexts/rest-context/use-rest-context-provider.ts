import { BROWSER_ENV } from "@/constants/browser-env";
import { AxiosRestClient } from "@/rest/axios/axios-rest-client";

import type { RestContextValue } from "./types";

export function useRestContextProvider(): RestContextValue {
  return {
    restClient: AxiosRestClient(BROWSER_ENV.shifuApiUrl),
  };
}
