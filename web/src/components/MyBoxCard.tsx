import { BoxLogo } from "@/components/BoxLogo";
import { Card } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";

/** "Tu box" (o "Tu coach", si entrena con un coach independiente): perfil de atleta y de coach. */
export function MyBoxCard({ className }: { className?: string }) {
  const { box } = useCurrentUser();
  if (!box) return null;

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
