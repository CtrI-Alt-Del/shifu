import { RestError } from "@/rest/errors/rest-error";

export class RestResponse<ResponseBody> {
  readonly body: ResponseBody | undefined;
  readonly statusCode: number;
  readonly headers: Record<string, string>;
  readonly errorMessage: string | undefined;

  constructor({
    body,
    statusCode,
    headers = {},
    errorMessage,
  }: {
    body?: ResponseBody;
    statusCode: number;
    headers?: Record<string, string>;
    errorMessage?: string;
  }) {
    this.body = body;
    this.statusCode = statusCode;
    this.headers = headers;
    this.errorMessage = errorMessage;
  }

  get isSuccessful() {
    return this.statusCode >= 200 && this.statusCode < 300;
  }

  get isFailure() {
    return !this.isSuccessful;
  }

  throwError(): never {
    throw new RestError(
      this.errorMessage ?? "Não foi possível concluir a solicitação.",
      this.statusCode,
    );
  }
}
