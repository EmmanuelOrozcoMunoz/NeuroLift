import { PageHeader } from "@/components/AppShell";
import { AvatarUploader } from "@/components/AvatarUploader";
import { IconLogout } from "@/components/icons";
import { InstallAppCard } from "@/components/InstallApp";
import { MyBoxCard } from "@/components/MyBoxCard";
import { Button, Card } from "@/components/ui";
import { WeightUnitToggle } from "@/components/WeightUnitToggle";
import { useAuth } from "@/lib/auth";

export default function CoachProfile() {
  const { logout } = useAuth();

  return (
    <>
      <PageHeader title="Perfil" />

      <Card className="mb-4">
        <AvatarUploader />
      </Card>

      <MyBoxCard className="mb-4" />

      <Card className="mb-4">
        <WeightUnitToggle />
      </Card>

      <InstallAppCard className="mb-4" />

      <Button variant="danger" full onClick={() => void logout()}>
        <IconLogout className="h-5 w-5" />
        Cerrar sesión
      </Button>
    </>
  );
}
