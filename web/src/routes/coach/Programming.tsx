import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { PageHeader } from "@/components/AppShell";
import { IconChevronRight, IconDumbbell, IconStore } from "@/components/icons";

/**
 * Programación personalizada: lo que el coach arma para sus atletas con coach personal
 * (grupos y sus mesociclos) y los planes que publica. Las clases del box van aparte.
 */
export default function Programming() {
  return (
    <>
      <PageHeader title="Programación" subtitle="Para tus atletas con coach personal" />
      <div className="space-y-2">
        <Row
          to="/coach/grupos"
          icon={<IconDumbbell />}
          title="Grupos y mesociclos"
          subtitle="Programa a varios atletas a la vez"
        />
        <Row to="/coach/planes" icon={<IconStore />} title="Planes" subtitle="Plantillas que los atletas adquieren" />
      </div>
    </>
  );
}

function Row({ to, icon, title, subtitle }: { to: string; icon: ReactNode; title: string; subtitle: string }) {
  return (
    <Link to={to} className="press flex min-h-touch items-center gap-4 rounded-2xl bg-surface p-4 active:bg-surface-2">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-fg [&>svg]:h-5 [&>svg]:w-5">
        {icon}
      </span>
      <span className="min-w-0 grow">
        <span className="block font-semibold">{title}</span>
        <span className="block truncate text-sm text-muted">{subtitle}</span>
      </span>
      <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
    </Link>
  );
}
