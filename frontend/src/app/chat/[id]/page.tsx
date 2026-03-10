import { ConvSidebar } from "@/components/ConvSidebar";
import { ExistingChatClient } from "./ExistingChatClient";
import { SidebarInset } from "@/components/ui/sidebar";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function ExistingChatPage({ params }: Props) {
  const { id } = await params;
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <ConvSidebar currentConversationId={id} />
      <SidebarInset className="flex flex-1 flex-col">
        <ExistingChatClient conversationId={id} />
      </SidebarInset>
    </div>
  );
}
