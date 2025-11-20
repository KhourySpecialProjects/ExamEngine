"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/authStore";

export default function AdminPage() {
  const router = useRouter();
  const { user } = useAuthStore();

  useEffect(() => {
    // Redirect to settings with users tab
    router.replace("/dashboard/settings?tab=users");
  }, [router]);

  return null;
}
