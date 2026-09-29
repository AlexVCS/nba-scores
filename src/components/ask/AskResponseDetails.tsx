import type {AskInterpreterInfo} from "@/services/ask/types";

interface AskResponseDetailsProps {
  interpreter: AskInterpreterInfo;
}

function AskResponseDetails({interpreter}: AskResponseDetailsProps) {
  const {model_called: modelCalled, cache_hit: cacheHit, adapter, model} = interpreter;
  const reportedModel = modelCalled || (cacheHit && Boolean(adapter));

  return (
    <details className="basis-full text-hw-muted">
      <summary className="w-fit cursor-pointer rounded-sm font-bold text-hw-accent-ink underline underline-offset-3 focus-visible:outline-2 focus-visible:outline-hw-accent">
        Response details
      </summary>
      <dl className="mt-2 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1 leading-relaxed">
        <dt>Model call this request</dt>
        <dd className="font-semibold text-hw-ink">{modelCalled ? "Yes" : "No"}</dd>
        <dt>Cache hit</dt>
        <dd className="font-semibold text-hw-ink">{cacheHit ? "Yes" : "No"}</dd>
        {reportedModel ? (
          <>
            <dt>Interpreter model</dt>
            <dd className="break-all font-semibold text-hw-ink">{model ?? "Not reported"}</dd>
            {adapter && <><dt>Adapter</dt><dd className="break-all font-semibold text-hw-ink">{adapter}</dd></>}
          </>
        ) : (
          <>
            <dt>Model</dt>
            <dd className="font-semibold text-hw-ink">No model used for this response</dd>
          </>
        )}
      </dl>
    </details>
  );
}

export default AskResponseDetails;
