import { useEffect, useState } from "react";

import { BoxLogo } from "@/components/BoxLogo";
import { IconCheck } from "@/components/icons";
import { Button, Card, Field } from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { useJoinBox } from "@/lib/boxQueries";

const CODE_LENGTH = 8;

/**
 * "Tu box" (o "Tu coach", si entrena con un coach independiente): perfil de atleta y de coach.
 * Para un atleta solo, en su lugar ofrece unirse a un box o a un coach con su código.
 */
export function MyBoxCard({ className }: { className?: string }) {
  const { box } = useCurrentUser();
  if (!box) return null;
  if (box.kind === "athlete") return <JoinBoxCard className={className} />;

  return (
    <Card className={className}>
      <div className="flex items-center gap-3">
        <BoxLogo boxId={box.id} name={box.name} hasLogo={box.has_logo} className="h-12 w-12" />
        <div className="min-w-0">
          <p className="text-xs font-semibold tracking-wide text-muted uppercase">
            {box.kind === "coach" ? "Tu coach" : "Tu box"}
          </p>
          <p className="truncate font-bold">{box.name}</p>
          {box.city && <p className="truncate text-sm text-muted">{box.city}</p>}
        </div>
      </div>
    </Card>
  );
}

interface BoxPublicInfo {
  name: string;
  city: string | null;
  kind: "box" | "coach";
}

/** Atleta solo -> se une a un box o a un coach. Conserva sesiones, planes y marcas. */
function JoinBoxCard({ className }: { className?: string }) {
  const join = useJoinBox();
  const [code, setCode] = useState("");
  const [preview, setPreview] = useState<BoxPublicInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    setPreview(null);
    setError(null);
    if (code.length !== CODE_LENGTH) return;
    const controller = new AbortController();
    apiFetch<BoxPublicInfo>(`/boxes/by-code/${code}`, { auth: false, signal: controller.signal })
      .then(setPreview)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err instanceof ApiError ? err.message : "No se pudo verificar el código.");
      });
    return () => controller.abort();
  }, [code]);

  if (done) {
    return (
      <Card className={className}>
        <p className="flex items-center gap-2 font-semibold text-done">
          <IconCheck className="h-5 w-5" /> Ya entrenas con {done}
        </p>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <p className="font-bold">¿Entrenas en un box o con un coach?</p>
      <p className="mt-1 text-sm text-muted">
        Escribe el código que te compartieron. Conservas tus sesiones, planes y marcas.
      </p>
      <form
        className="mt-3 space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (!preview) return;
          join.mutate(code, {
            onSuccess: (box) => setDone(box.name),
            onError: (err) => setError(err instanceof ApiError ? err.message : "No se pudo unir."),
          });
        }}
      >
        <Field
          label="Código de invitación"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          maxLength={CODE_LENGTH}
          placeholder="Ej. K7M2QX9P"
          className="font-mono tracking-[0.2em] uppercase placeholder:font-sans placeholder:tracking-normal placeholder:normal-case"
          value={code}
          onChange={(event) => setCode(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
        />
        {preview && (
          <p className="flex items-start gap-2 rounded-xl bg-done-soft px-3 py-2 text-sm font-medium text-done">
            <IconCheck className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {preview.kind === "coach" ? "Entrenarás con " : "Te unirás a "}
              <b>{preview.name}</b>
              {preview.city && <span className="text-done/80"> · {preview.city}</span>}
            </span>
          </p>
        )}
        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button type="submit" full disabled={!preview} loading={join.isPending}>
          Unirme
        </Button>
      </form>
    </Card>
  );
}
