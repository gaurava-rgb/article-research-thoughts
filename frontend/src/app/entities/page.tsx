import { ConvSidebar } from "@/components/ConvSidebar";
import { SidebarInset } from "@/components/ui/sidebar";
import { EntityWorkbenchClient } from "./EntityWorkbenchClient";

export default function EntityDirectoryPage() {
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <ConvSidebar />
      <SidebarInset className="flex flex-1 flex-col">
        <EntityWorkbenchClient />
      </SidebarInset>
    </div>
  );
}
