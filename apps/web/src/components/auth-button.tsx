"use client";

import { useEffect, useState } from "react";
import { LogIn, LogOut } from "lucide-react";
import { getSession, signIn, signOut } from "next-auth/react";
import type { Session } from "next-auth";
import { Button } from "@/components/ui/button";

export function AuthButton() {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    let isActive = true;

    getSession()
      .then((nextSession) => {
        if (isActive) {
          setSession(nextSession);
          setIsLoaded(true);
        }
      })
      .catch(() => {
        if (isActive) {
          setIsLoaded(true);
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  if (!isLoaded) {
    return (
      <Button type="button" variant="outline" disabled>
        Account
      </Button>
    );
  }

  if (session?.user) {
    return (
      <Button type="button" variant="outline" onClick={() => void signOut()}>
        <LogOut data-icon="inline-start" />
        {session.user.name ?? session.user.email ?? "Sign out"}
      </Button>
    );
  }

  return (
    <Button type="button" variant="outline" onClick={() => void signIn("google")}>
      <LogIn data-icon="inline-start" />
      Sign in with Google
    </Button>
  );
}
