import { ConvSidebar } from "@/components/ConvSidebar";
import { SidebarInset } from "@/components/ui/sidebar";
import { EntityDossierClient } from "./EntityDossierClient";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function EntityDossierPage({ params }: Props) {
  const { id } = await params;
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <ConvSidebar />
      <SidebarInset className="flex flex-1 flex-col">
        <EntityDossierClient entityId={id} />
      </SidebarInset>
    </div>
  );
}
