import { Suspense } from "react";

import { ChatPanel } from "@/components/chat/chat-panel";
import { LoadingBlock } from "@/components/shared/state-panel";

export default function ChatPage() {
  return (
    <Suspense fallback={<LoadingBlock rows={8} />}>
      <ChatPanel />
    </Suspense>
  );
}
