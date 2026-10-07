import type { OperationInputs } from "./operations";
// OpenAPI binary is emitted as string. FormData accepts File at runtime; adapt once here, never stringify it.
export function documentBody(file: File, kind: OperationInputs["uploadDocument"]["body"]["kind"]): OperationInputs["uploadDocument"]["body"] {
  return { kind, file: file as unknown as string };
}
