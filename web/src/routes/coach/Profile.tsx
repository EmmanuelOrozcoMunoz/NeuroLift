import { PageHeader } from "@/components/AppShell";
import { AvatarUploader } from "@/components/AvatarUploader";
import { IconLogout } from "@/components/icons";
import { Button, Card } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function CoachProfile() {
  const { logout } = useAuth();

  return (
    <>
      <PageHeader title="Perfil" />

      <Card className="mb-4">
        <AvatarUploader />
      </Card>

      <Button variant="danger" full onClick={() => void logout()}>
        <IconLogout className="h-5 w-5" />
        Cerrar sesión
      </Button>
    </>
  );
}
