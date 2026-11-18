import Link from "next/link";

import { AcceptInviteForm } from "@/components/auth/accept-invite-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function AcceptInvitePage() {
  return (
    <main className="mx-auto flex min-h-full w-full max-w-md flex-1 flex-col justify-center px-4 py-12">
      <div className="mb-6 text-center">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          Atlas Enterprise AI
        </Link>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Accept invitation</CardTitle>
          <CardDescription>
            Confirm your invite and set a password to access the workspace.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AcceptInviteForm />
        </CardContent>
      </Card>
    </main>
  );
}
