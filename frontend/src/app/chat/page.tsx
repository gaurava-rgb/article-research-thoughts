import { ConvSidebar } from "@/components/ConvSidebar";
import { NewChatClient } from "./NewChatClient";
import { SidebarInset } from "@/components/ui/sidebar";

export default function NewChatPage() {
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <ConvSidebar />
      <SidebarInset className="flex flex-1 flex-col">
        <NewChatClient />
      </SidebarInset>
    </div>
  );
}
